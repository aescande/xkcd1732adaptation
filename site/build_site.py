#!/usr/bin/env python3
"""Assemble the site into _site/.

One language folder per site/<lang>/index.html that has a render in
results/<lang>/timeline.png. A language with no render is left out rather than
published with a missing image.

Each page declares its own name, in its own language:

    <meta name="edition" content="Français">

and carries <!--switch--> where the language links go, so the list of editions
is always the list of what is actually published.
"""
import os
import re
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(REPO, "site")
RESULTS = os.path.join(REPO, "results")
OUT = os.path.join(REPO, "_site")

SWITCH = "<!--switch-->"
EDITIONS = "<!--editions-->"
_META = re.compile(r'<meta name="edition" content="([^"]*)">')


def editions():
    """[(lang, name)] for every page with a render, sorted by folder name."""
    found = []
    for lang in sorted(os.listdir(SITE)):
        page = os.path.join(SITE, lang, "index.html")
        if not os.path.isfile(page):
            continue
        if not os.path.isfile(os.path.join(RESULTS, lang, "timeline.png")):
            print(f"  skipped (no render): {lang}")
            continue
        m = _META.search(open(page, encoding="utf-8").read())
        if not m:
            raise SystemExit(f"{lang}/index.html has no <meta name=\"edition\">")
        found.append((lang, m.group(1)))
    return found


def switch_html(langs, current):
    """The language links for one page: the current edition is not a link."""
    if len(langs) < 2:
        return ""
    parts = [name if lang == current else f'<a href="../{lang}/">{name}</a>'
             for lang, name in langs]
    return '<nav class="switch">' + " · ".join(parts) + "</nav>"


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def main():
    langs = editions()
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(SITE, OUT, ignore=shutil.ignore_patterns("*.py"))

    for lang in sorted(os.listdir(OUT)):
        d = os.path.join(OUT, lang)
        if not os.path.isdir(d):
            continue
        if lang not in [l for l, _ in langs]:
            shutil.rmtree(d)
            continue
        shutil.copyfile(os.path.join(RESULTS, lang, "timeline.png"),
                        os.path.join(d, "timeline.png"))
        page = os.path.join(d, "index.html")
        html = open(page, encoding="utf-8").read()
        write(page, html.replace(SWITCH, switch_html(langs, lang)))
        print(f"  published: {lang}")

    index = os.path.join(OUT, "index.html")
    html = open(index, encoding="utf-8").read()
    items = "\n".join(f'      <li><a href="{lang}/">{name}</a></li>'
                      for lang, name in langs)
    write(index, html.replace(EDITIONS, items))
    if not langs:
        print("  nothing to publish: no language has a render")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
