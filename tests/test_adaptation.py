#!/usr/bin/env python3
"""Exercise the adaptation block: every feature, and every way it should fail."""
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO, "src")
DATA_DIR = os.path.join(REPO, "data")
sys.path.insert(0, SRC_DIR)
SRC = os.path.join(DATA_DIR, "translation_en_1732.json")
# Scratch directory for the test builds.
TMP = tempfile.mkdtemp(prefix="adaptation_test_")
ok = fail = 0


def run(doc, tag):
    p = os.path.join(TMP, f"{tag}.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False)
    return subprocess.run([sys.executable, "build_svg.py", p,
                           os.path.join(TMP, f"{tag}.svg")],
                          capture_output=True, text=True, cwd=SRC_DIR)


def case(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok    {name}")
    else:
        fail += 1
        print(f"  FAIL  {name}  {detail}")


def out(r):
    return r.stdout + r.stderr


def read_svg(tag):
    """The built SVG, or "" if the build produced none."""
    p = os.path.join(TMP, f"{tag}.svg")
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


base = json.load(open(SRC, encoding="utf-8"))

# ------------------------------------------------- naming entries by prefix
import adaptation
ents = base["entries"]
# Derive a prefix that is unique in this file.
long_en = next(e["en"] for e in ents
               if e["en"].startswith("TEMPERATURES START TO LEVEL"))
words = long_en.split()
prefix = next(" ".join(words[:n]) for n in range(1, len(words) + 1)
              if sum(e["en"].startswith(" ".join(words[:n]) + " ")
                     for e in ents) == 1)
print(f"  (unique prefix: {prefix!r})")
case("opening words resolve to the full en",
     adaptation.resolve_en(prefix, ents) == long_en)
case("exact en still wins", adaptation.resolve_en("ICE", ents) == "ICE")
d = copy.deepcopy(base)
d["adaptation"] = {"entriesRemoved": [prefix]}
r = run(d, "prefix")
svg = read_svg("prefix")
case("prefix removal builds and drops the entry",
     r.returncode == 0 and "LEVEL OUT" not in svg, r.stderr[-200:])
# two entries sharing opening words
d = copy.deepcopy(base)
d["entries"] = d["entries"] + [
    {"en": "SHARED OPENING ALPHA", "text": "A", "type": "scenario",
     "align": "left", "at": [900, 29700]},
    {"en": "SHARED OPENING BETA", "text": "B", "type": "scenario",
     "align": "left", "at": [900, 29720]}]
d["adaptation"] = {"entriesRemoved": ["SHARED OPENING"]}
r = run(d, "ambig")
case("ambiguous prefix rejected, naming both candidates",
     r.returncode != 0 and "ambiguous" in out(r)
     and "ALPHA" in out(r) and "BETA" in out(r),
     out(r)[-250:])

# ---------------------------------------------------------------- happy path
doc = copy.deepcopy(base)
n_entries = len(doc["entries"])
doc["adaptation"] = {
    "currentYear": 2026,
    "entriesRemoved": ["CURRENT PATH", "OPTIMISTIC SCENARIO"],
    "entriesAdded": [
        {"en": "STAYS BELOW 2 C", "text": "STAYS BELOW 2 °C",
         "type": "scenario", "align": "left", "at": [940, 29650]},
        {"en": "IF COOPERATION BREAKS DOWN",
         "text": "IF COOPERATION BREAKS DOWN",
         "type": "scenario", "align": "left", "at": [1175, 29655], "lines": 2},
    ],
    "figuresRemoved": ["sub29"],
    "figuresShifted": {"sub30": [40, 12], "sub02": [10, 0]},
    "figuresAdded": [
        {"file": "arrow_new.png", "x": 900, "y": 29600, "width": 50, "height": 40,
         "connector": True},
    ],
}
r = run(doc, "happy")
case("builds with a full adaptation", r.returncode == 0, r.stderr[-300:])
svg = read_svg("happy")
case("removed entries gone", svg and "CURRENT PATH" not in svg)
case("added entry drawn", "STAYS BELOW 2" in svg)
case("removed image gone", svg and 'figures/sub29.png' not in svg)
case("added image placed", 'figures/arrow_new.png' in svg)
case("added image in connectors layer",
     svg.find('inkscape:label="connectors"') != -1
     and svg.find('arrow_new.png') > svg.find('inkscape:label="connectors"'))
case("warns about the missing PNG", "not in" in r.stdout and "arrow_new" in r.stdout)

# present-day marker moved
case("2026 gridline present", 'id="gridline_present_day' in svg)
y2026 = 1.322092 * 2026 + 26870.8521
case("2026 year label at the exact position (no nudge needed)",
     f'y="{y2026:.1f}"' in svg, f"expected y={y2026:.1f}")
case("2016 label gone", svg and '>2016<' not in svg)

# additive shift: FR carries figureOffsets for sub02 already
fr = json.load(open(os.path.join(DATA_DIR, "translation_fr_1732.json"),
                    encoding="utf-8"))
pre = (fr.get("figureOffsets") or {}).get("sub02")
case("FR carries an offset for sub02", pre is not None)
pre = pre or [0, 0]
fr["adaptation"] = {"figuresShifted": {"sub02": [10, 5]}}
r = run(fr, "additive")
case("additive shift builds", r.returncode == 0, r.stderr[-300:])
case("reports the summed offset", "summed" in r.stdout, r.stdout[-300:])
m = re.search(r"shifted sub02 by \(([-+\d.]+), ([-+\d.]+)\)", r.stdout)
case("sub02 offset is the sum",
     m and (float(m.group(1)), float(m.group(2)))
     == (pre[0] + 10, pre[1] + 5),
     f"pre={pre} got={m.groups() if m else None}")

# ------------------------------------------------------------- failure modes
for tag, block, needle in [
    ("badkey", {"currentYr": 2026}, "unknown key"),
    ("protected", {"entriesRemoved": ["NOT A TRAP"]}, "FIGURE_LABELS"),
    ("protected_by_prefix", {"entriesRemoved": ["NOT A"]}, "FIGURE_LABELS"),
    ("midword", {"entriesRemoved": ["CURRENT PAT"]}, "not an entry's `en`"),
    ("nosuchprefix", {"entriesRemoved": ["NOTHING LIKE THIS"]},
     "not an entry's `en`"),
    ("toomany", {"entriesRemoved": ["CURRENT PATH", "CURRENT PATH"]},
     "but the file has"),
    ("nosuchfig", {"figuresRemoved": ["sub99"]}, "not in the manifest"),
    ("badname", {"figuresAdded": [{"file": "my arrow!.png", "x": 1, "y": 1,
                                   "width": 1, "height": 1}]}, "XML id"),
    ("collide", {"figuresAdded": [{"file": "sub01.png", "x": 1, "y": 1,
                                   "width": 1, "height": 1}]}, "collides"),
    ("notext", {"entriesAdded": [{"en": "X", "type": "scenario",
                                  "align": "left", "at": [0, 0]}]},
     "missing 'text'"),
    ("badshift", {"figuresShifted": {"sub01": [1, 2, 3]}}, "[dx, dy]"),
    ("badyear", {"currentYear": "2026"}, "whole year"),
]:
    d = copy.deepcopy(base)
    d["adaptation"] = block
    r = run(d, tag)
    o = out(r)
    case(f"rejects {tag}", r.returncode != 0 and needle in o,
         f"rc={r.returncode} {o[-200:]!r}")

print(f"\n{ok} passed, {fail} failed")
# Cleanup after the summary, so an error in it cannot hide the result.
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if fail else 0)
sys.exit(1 if fail else 0)
