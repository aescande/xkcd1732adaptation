"""Unknown keys and entry types in a translation file are refused."""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(REPO, "src", "build_svg.py")
base = json.load(open(os.path.join(REPO, "data", "translation_fr_1732.json"),
                      encoding="utf-8"))
TMP = tempfile.mkdtemp(prefix="keys_test_")
ok = fail = 0


def case(name, mutate, needle):
    global ok, fail
    doc = copy.deepcopy(base)
    mutate(doc)
    p = os.path.join(TMP, f"{name}.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False)
    r = subprocess.run([sys.executable, BUILD, p, os.path.join(TMP, "out.svg")],
                       capture_output=True, text=True)
    out = r.stdout + r.stderr
    if r.returncode != 0 and needle in out:
        ok += 1
        print(f"  ok    rejects {name}")
    else:
        fail += 1
        print(f"  FAIL  rejects {name}  rc={r.returncode} {out[-200:]!r}")


case("entry key", lambda d: d["entries"][3].update(fontsize=30),
     "entry 3 ('TEMPERATURE'): unknown key(s) ['fontsize']")
case("entry type", lambda d: d["entries"][3].update(type="stroy"),
     "unknown type 'stroy'")
case("top-level key", lambda d: d.update(figureOffset={}),
     "top level: unknown key(s) ['figureOffset']")
case("locale key", lambda d: d["locale"].update(decimal=","),
     "locale: unknown key(s) ['decimal']")
case("linebreak key", lambda d: d["locale"]["linebreak"].update(glue=""),
     "locale.linebreak: unknown key(s) ['glue']")
case("defaults row", lambda d: d["defaults"].update(evnt={}),
     "defaults: unknown key(s) ['evnt']")
case("defaults key", lambda d: d["defaults"]["event"].update(wspace=0.92),
     "defaults.event: unknown key(s) ['wspace']")
case("added entry key",
     lambda d: d.update(adaptation={"entriesAdded": [
         {"en": "X", "text": "X", "type": "event", "align": "left",
          "at": [0, 0], "colour": "#000"}]}),
     "adaptation.entriesAdded[0]: unknown key(s) ['colour']")

print(f"\n{ok} passed, {fail} failed")
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if fail else 0)
