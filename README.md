# xkcd 1732 — adaptation tools

Rebuilds [*A Timeline of Earth's Average Temperature*](https://xkcd.com/1732/)
by Randall Munroe as SVG, from geometry measured off the original artwork, and
draws it in any language from a translation file.

Two editions are included so far: English, which reproduces Munroe's own text and
serves as the reference, and French. The editions can be seen from here:
[aescande.github.io/xkcd1732adaptation/](https://aescande.github.io/xkcd1732adaptation/).

This is an unofficial adaptation. It is not affiliated with, nor endorsed by,
Randall Munroe or xkcd. The original work is licensed
[CC BY-NC 2.5](https://creativecommons.org/licenses/by-nc/2.5/).

## Layout

```
src/        the renderer                              src/README.md
data/       translations, curve geometry, figures     data/FORMAT.md
tests/      tests of the renderer
3rdparty/   the xkcd Script font (ipython/xkcd-font)
results/    rendered editions
site/       the published page — HTML only, no binaries
```

## Building

Requires Python 3 and the packages in `src/requirements.txt`.

```
python -m pip install -r src/requirements.txt
python src/build_svg.py data/translation_fr_1732.json
```

Any file in `data/` can be given; the French one is the example here. The SVG
is written to `results/`, named after the translation file.

Tests:

```
python tests/test_linebreak.py
python tests/test_adaptation.py
python tests/test_keys.py
python tests/test_build.py
python tests/test_site.py
```

`test_build.py` builds every edition in `data/` in a temporary folder and
compares it with `tests/reference_hashes.json`. Record the references with
`python tests/test_build.py --update` after an intended change to the output,
and when an edition is added, renamed or removed. The same tests run on every
push (`.github/workflows/tests.yml`).

## Adding a translation or an adaptation

A language is one JSON file. Nothing in the code names a language, and there
is no default: the file decides what is drawn.

**A new language.** Copy `data/translation_en_1732.json`, which holds Munroe's
original wording, and translate the `text` of each of the 156 entries. Leave
`en` untouched — it is how the renderer recognises an entry across languages,
so it keys the ink colours and the labels that travel with a drawing. Then set
the `locale` block (era suffixes, decimal separator, minus sign, degree
spacing, line-breaking rules) and the `attribution` wording, and add yourself
to `credits`.

Translated text is rarely the same width as the original, so expect to adjust.
`data/FORMAT.md` describes the three levers, from least to most intrusive: the
entry's `fontSize`, `wscale` or `lines`; a `figureOffsets` entry when a wider
label runs into the arrow pointing at it; and moving the block with `at`.

**A revision of the strip.** A newer "now", different scenario branches, data
that has moved: these go in an `adaptation` block inside the translation file,
which declares the changes as a diff — entries and figures added, removed or
shifted — rather than editing `entries` in place. The block is inert when
absent, and it is repeated in each language file.

Both are documented key by key in [`data/FORMAT.md`](data/FORMAT.md).

Build the file, then run `python tests/test_build.py --update` so the new
edition is checked from then on.

**Publishing a page for it** needs two more things: a PNG export of the SVG at
`results/<lang>/timeline.png`, and a page at `site/<lang>/index.html` — copy
`site/fr/index.html` and translate its title and alt text. The workflow picks
up any language that has both. `site/index.html` still forwards to `fr/`.

## Site

`site/build_site.py` assembles the site into `_site/`: one folder per
`site/<lang>/index.html` that has a render in `results/<lang>/timeline.png`,
with the language links and the index list filled in from the pages that were
kept. A language with no render is left out.

`.github/workflows/pages.yml` runs it on every push and deploys `_site/`. To
see the site locally, run it yourself and open the result (`_site/` is
git-ignored):

```
python site/build_site.py
```

## Licensing

There is no single licence for this repository: it combines original code,
material derived from Munroe's artwork, and a third-party font, which carry
different terms. See [`LICENSE`](LICENSE) for the summary and
[`REUSE.toml`](REUSE.toml) for the same information in machine-readable form.

## Status

`data/` holds the English and French editions; `results/fr/timeline.png` is the
published French render and `results/en/timeline.png` is the English one. 