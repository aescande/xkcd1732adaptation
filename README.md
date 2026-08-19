# xkcd 1732 — Adaptation tools and result

Tools for the translation and adaptation of [*A Timeline of Earth's Average Temperature*](https://xkcd.com/1732/)
by Randall Munroe, rebuilt as SVG from geometry measured off the original artwork.

**As an example, [view the timeline →](https://aescande.github.io/xkcd1732adaptation/fr/)**

This is an unofficial adaptation. It is not affiliated with, nor endorsed by,
Randall Munroe or xkcd. The original work is licensed
[CC BY-NC 2.5](https://creativecommons.org/licenses/by-nc/2.5/).

## Layout

```
site/       the published page — HTML only, no binaries
results/    rendered editions
src/        the renderer                      (not yet published)
data/       translations, curve, figures      (not yet published)
derivation/ how the geometry was measured     (not yet published)
```

The site is assembled and deployed by `.github/workflows/pages.yml`: it copies
`site/` and uses files from `results/`.

To preview the page locally, copy the image in by hand first — the copy is
git-ignored, so it cannot be committed by accident:

```
python -c "import shutil; shutil.copy('results/fr/timeline.png', 'site/fr/timeline.png')"
```

then open `site/fr/index.html`.

## Licensing

There is no single licence for this repository: it combines your own work with
material derived from Munroe's artwork, and the two cannot carry the same terms.
See [`LICENSE`](LICENSE) for the summary and [`REUSE.toml`](REUSE.toml) for the
same information in machine-readable form.

## Status

Published so far: the French render and the page that shows it.
