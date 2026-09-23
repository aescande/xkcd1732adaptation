# Renderer

Builds one edition of xkcd 1732 as SVG from a translation file.

| file | role |
|---|---|
| `build_svg.py` | the SVG generator |
| `typography.py` | font, text measurement, the glyphs the font lacks |
| `text_layer.py` | renders the translation entries |
| `linebreak.py` | fixed-line-count line breaker |
| `adaptation.py` | applies a translation's optional `adaptation` block |
| `requirements.txt` | Python dependencies |

Data is read from `../data` (schema in `../data/FORMAT.md`), the font from
`../3rdparty/xkcd-font/`. Tests are in `../tests/`.

## Running it

```
python build_svg.py ../data/translation_fr_1732.json                -> ../results/translation_fr_1732.svg
python build_svg.py ../data/translation_fr_1732.json timeline_fr.svg
python build_svg.py ../data/translation_fr_1732.json --embed-font
python build_svg.py my_translation.json --data my_data/
```

The edition is decided entirely by the translation file. `--data` points at
another folder holding `curve_paths.json` and `figures/`. `--embed-font`
inlines the font as `@font-face` (browsers honour it, Inkscape does not).

Figures are linked relative to the output file, so the SVG must stay where it
was written. The curve is omitted if `curve_paths.json` is absent.

Requires **uharfbuzz** (`python -m pip install -r requirements.txt`). Text is
measured through HarfBuzz, which is what browsers and Inkscape shape with.
Pillow applies kerning only when compiled with libraqm, which the Windows
wheels are not; unkerned, `"CO"` measures 64.00 px instead of 53.41 at size
60, and lines split around a substituted glyph are misplaced by 8–10 px.

`CAP`, which sets every baseline, is read from the glyph outlines.

For Inkscape, install `xkcd-script.ttf` on the system: Inkscape resolves fonts
only through the system.

## Coordinate system

Everything is in the pixel space of the original 2x bitmap (1480 × 29913). The
`viewBox` starts at **x = −60**: era suffixes longer than "BCE" don't fit the
original 77 px margin. The plot itself is untouched.

```
x(T)    = 739.5 + 132.2 × T              T in °C, frame spans −5 … +5
y(year) = 1.322092 × year + 26870.8521   astronomical years, 1 BCE = 0
```

Both are fitted on the original artwork; the year mapping on its 216
horizontal gridlines rather than on the hand-lettered year labels.

## Layers (bottom to top)

```
background              white paper, locked
temperature bands       10 <rect>
gridlines               3 horizontal groups + 1 vertical group
zero axis               1 <line>, opaque black
gridline erasers        one per figure
text erasers            one per text block
curve shadow            nested translucent strokes
curve                   5 paths
illustrations           the figures, minus the connectors
connectors              arrows and leader lines
frame                   open frame + 8 ticks
header rules            2 horizontal rules
span annotation         the 4.3 °C label
chart labels            the insolation chart's 550/500/450
temperature labels      9 <text>
year labels             52 <text>
text                    the translation entries
credits                 attribution + credit lines
```

Each eraser paints a patch of band colour, masked to a dilated, blurred copy of
its figure or text block, which knocks the gridlines out behind it with a soft
margin, as in the original.

## The curve

Five paths, because a dash pattern cannot vary within one SVG path; they share
their junction nodes. The geometry and the measured stroke properties are in
`../data/curve_paths.json`; `build_svg.py` renders whatever is in that file,
and draws no curve at all if it is absent.

**Dashes.** The JSON stores the visible ink. A round linecap adds half a stroke
width at each end, so `build_svg.py` emits the geometric dash shortened and the
gap lengthened by one width: `"5 17"` for a measured 14 / 8. When retuning in
Inkscape, edit the geometric value.

The three projections carry a `stroke-dashoffset` that puts dash centres on the
measured positions. The main curve has none.

### The shadow

`CURVE_SHADOW_STYLE` selects the implementation:

| style | what it is | Inkscape canvas | browser / export |
|---|---|---|---|
| `rings` (default) | nested translucent strokes, no filter | correct | correct |
| `blur` | `feGaussianBlur` + `feFlood` + `feComposite` | poor | correct |
| `dropshadow` | `feDropShadow` | object dropped | correct |
| `none` | — | — | — |

`rings` draws the curve six times underneath itself, offset, each copy wider
and fainter, with the widths and opacities of `CURVE_SHADOW_LAYERS` scaled by
`CURVE_SHADOW_STRENGTH`. The copies are `<use>` elements, so the visible paths
carry no `stroke-width` of their own.

Filter regions use absolute padding: the bounding box of a near-vertical open
path excludes its stroke.

## Open items

**Anchoring is on the advance, not the ink.** This font's ink overhangs its
advance by about 16 px on a 27-character run, so right-aligned and centred
blocks sit slightly off.

**Do not check text with CairoSVG.** It does not apply GPOS kerning, and this
font kerns hard (`T`→`O` is −14.8 px at size 60).

**Year labels.** The "now" label is pushed down to keep the gap the original
leaves under 2000 (2016: +7 px). The 1 BCE / 1 CE pair is placed 16 px above and
20 px below year 0. The original's 2016 rule sits 3 px below the exact mapping; the SVG
uses the exact position.

**The zero axis is continuous.** The original breaks it into 46 segments where
artwork or text crosses.

**Curve dash phase drifts** along the reconstruction; it is not phase-locked to
the original.

## Glyphs the font lacks

The Unicode cmap has no `°`, `²`, `₂`, `ᵉ`, `«`, `»` or `…`. `typography.py`
draws the degree as a filled disc and the guillemets as stroked chevrons;
`²`, `₂` and `ᵉ` are ordinary glyphs at reduced size with a baseline shift, all
in em. `…` is not substituted. What that means when writing a translation is in
[`../data/FORMAT.md`](../data/FORMAT.md).

The degree exists only in the legacy Macintosh cmap subtable, where `0xB0` is
'infinity' by Mac Roman convention. Audit against the Unicode cmap only.
