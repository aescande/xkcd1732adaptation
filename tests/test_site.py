"""The site pages carry what build_site.py needs."""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(REPO, "site")
sys.path.insert(0, SITE)

import build_site  # noqa: E402

ok = fail = 0


def case(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok    {name}")
    else:
        fail += 1
        print(f"  FAIL  {name}  {detail}")


langs = sorted(d for d in os.listdir(SITE)
               if os.path.isfile(os.path.join(SITE, d, "index.html")))
case("there is at least one edition page", bool(langs))

for lang in langs:
    html = open(os.path.join(SITE, lang, "index.html"), encoding="utf-8").read()
    m = build_site._META.search(html)
    case(f"{lang} declares its edition name", bool(m), "no <meta name=edition>")
    case(f"{lang} has the switch placeholder", build_site.SWITCH in html)
    case(f"{lang} shows timeline.png", 'src="timeline.png"' in html)

index = open(os.path.join(SITE, "index.html"), encoding="utf-8").read()
case("the index has the editions placeholder", build_site.EDITIONS in index)

pairs = [(l, l.upper()) for l in langs]
if len(pairs) > 1:
    nav = build_site.switch_html(pairs, pairs[0][0])
    case("the current edition is not a link in the switch",
         f'>{pairs[0][1]}<' not in nav and f'"../{pairs[1][0]}/"' in nav, nav)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
