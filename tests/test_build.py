"""Build every edition in data/ and compare with reference_hashes.json.

An edition is any JSON under data/ carrying `entries` and `locale`;
NON_EDITIONS lists the other JSON files the renderer reads. A JSON that is
neither is an error rather than a silent skip.

Builds into a temporary folder. Figure links are relative to the output, so
they are normalised to `figures/...` before hashing: the hash is that of an
SVG built beside the figures, whatever folder the test used.

Run with --update to record the references: after an intended change to the
output, and when an edition is added, renamed or removed.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data")
REF = os.path.join(REPO, "tests", "reference_hashes.json")
NON_EDITIONS = {"curve_paths.json", "figures/figures.json"}

ok = fail = 0


def case(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok    {name}")
    else:
        fail += 1
        print(f"  FAIL  {name}  {detail}")


def editions():
    """Paths relative to data/, sorted. Refuses an unrecognised JSON."""
    global fail
    found = []
    for root, _dirs, files in os.walk(DATA):
        for f in sorted(files):
            if not f.endswith(".json"):
                continue
            rel = os.path.relpath(os.path.join(root, f), DATA).replace(os.sep, "/")
            doc = json.load(open(os.path.join(DATA, rel), encoding="utf-8"))
            if isinstance(doc, dict) and "entries" in doc and "locale" in doc:
                found.append(rel)
            elif rel not in NON_EDITIONS:
                fail += 1
                print(f"  FAIL  {rel} is neither an edition nor a known data "
                      f"file; add it to NON_EDITIONS if it is not an edition")
    return sorted(found)


update = "--update" in sys.argv[1:]
refs = {} if update else json.load(open(REF, encoding="utf-8"))
found = editions()
TMP = tempfile.mkdtemp(prefix="build_test_")
prefix = os.path.relpath(os.path.join(DATA, "figures"), TMP).replace(os.sep, "/")
hashes = {}

for rel in found:
    svg = os.path.join(TMP, rel.replace("/", "_") + ".svg")
    r = subprocess.run([sys.executable, os.path.join(REPO, "src", "build_svg.py"),
                        os.path.join(DATA, rel), svg],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(svg):
        fail += 1
        print(f"  FAIL  {rel} does not build  {(r.stdout + r.stderr)[-300:]}")
        continue
    text = open(svg, encoding="utf-8").read().replace(
        f'xlink:href="{prefix}/', 'xlink:href="figures/')
    hashes[rel] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if update:
        print(f"  {rel}  {hashes[rel]}")
    elif rel not in refs:
        case(f"{rel} has a reference", False, "new edition: run --update")
    else:
        case(f"{rel} matches its reference", hashes[rel] == refs[rel],
             f"{hashes[rel]} != {refs[rel]}")

shutil.rmtree(TMP, ignore_errors=True)

if not update:
    for rel in refs:
        case(f"{rel} still exists", rel in found,
             "stale reference: run --update")

if update:
    if fail:
        sys.exit(1)
    with open(REF, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(hashes, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(f"\nreferences written to {os.path.relpath(REF, REPO)}")
    sys.exit(0)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
