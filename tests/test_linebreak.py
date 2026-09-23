"""Line breaker: invariants on sample strings, with the real font and the
French parameters from data/translation_fr_1732.json."""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

from linebreak import LineBreaker, Unsplittable  # noqa: E402
from typography import measurer, spacing_px      # noqa: E402

ok = fail = 0


def case(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok    {name}")
    else:
        fail += 1
        print(f"  FAIL  {name}  {detail}")


fr = json.load(open(os.path.join(REPO, "data", "translation_fr_1732.json"),
                    encoding="utf-8"))
params = fr["locale"]["linebreak"]
size = 42
ls = fr["defaults"].get("*", {}).get("letterSpacing")
breaker = LineBreaker(measurer(size, spacing_px(ls, size)), params)

SAMPLES = [
    ("ÇA SUFFIT ! JE DÉMÉNAGE AU CANADA !", 3),
    ("QUAND ON VOUS DIT « LE CLIMAT A DÉJÀ CHANGÉ », "
     "VOICI LE GENRE DE CHANGEMENTS DONT IL S'AGIT.", 2),
    ("BOSTON EST ENSEVELIE SOUS PRÈS DE 1,6 KM DE GLACE, "
     "ET LES GLACIERS DESCENDENT JUSQU'À NEW YORK.", 2),
    ("LE PLUS ANCIEN HUMAIN DONT NOUS CONNAISSIONS LE NOM", 2),
    ("ESSOR DES CITÉS-ÉTATS GRECQUES", 2),
]

for text, n in SAMPLES:
    lines = breaker.split(text, n)
    print("\n" + "\n".join(f"        {l}" for l in lines))
    tag = text[:24]
    case(f"{tag}: {n} lines", len(lines) == n, lines)
    case(f"{tag}: words kept in order", " ".join(lines).split() == text.split())
    case(f"{tag}: no line starts with {params['glue_before']!r}",
         not any(l[0] in params["glue_before"] for l in lines[1:]))
    case(f"{tag}: no line ends with {params['glue_after']!r}",
         not any(l[-1] in params["glue_after"] for l in lines[:-1]))

# A non-breaking space is never a break, and is drawn as a space.
lines = LineBreaker(len, params).split("AAAA B CCCCC", 2)
case("nbsp is not a break", lines == ["AAAA B", "CCCCC"], lines)

# More lines than tokens.
try:
    breaker.split("TROP COURT", 5)
    case("too many lines raises Unsplittable", False)
except Unsplittable:
    case("too many lines raises Unsplittable", True)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
