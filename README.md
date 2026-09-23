# xkcd 1732 — Adaptation tools and result

Tools for the translation and adaptation of [*A Timeline of Earth's Average Temperature*](https://xkcd.com/1732/)
by Randall Munroe, rebuilt as SVG from geometry measured off the original artwork.

**As an example, [view the timeline →](https://aescande.github.io/xkcd1732adaptation/fr/)**

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
derivation/ how the geometry was measured             (not yet published)
```

## Building

Requires Python 3 and the packages in `src/requirements.txt`.

```
python -m pip install -r src/requirements.txt
python src/build_svg.py data/translation_fr_1732.json
```

The SVG is written to `results/translation_fr_1732.svg`. Tests:

```
python tests/test_linebreak.py
python tests/test_adaptation.py
python tests/test_keys.py
python tests/test_build.py
```

`test_build.py` builds every edition in `data/` in a temporary folder and
compares it with `tests/reference_hashes.json`. Record the references with
`python tests/test_build.py --update`: after an intended change to the output,
and when an edition is added, renamed or removed. The same tests run on every
push (`.github/workflows/tests.yml`).

## Site

The site is assembled and deployed by `.github/workflows/pages.yml`: it copies
`site/` and uses files from `results/`.

To preview the page locally, copy the image in by hand first (the copy is
git-ignored):

```
python -c "import shutil; shutil.copy('results/fr/timeline.png', 'site/fr/timeline.png')"
```

then open `site/fr/index.html`.

## Licensing

There is no single licence for this repository: it combines original code,
material derived from Munroe's artwork, and a third-party font, which carry
different terms. See [`LICENSE`](LICENSE) for the summary and
[`REUSE.toml`](REUSE.toml) for the same information in machine-readable form.

## Status

Published: the renderer, its data and tests, the French render and the page
that shows it. Not yet published: the derivation scripts.
