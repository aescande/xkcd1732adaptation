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

The time mapping is fitted on the **216 horizontal gridlines** (rms residual
0.46 px, max 4.96 px), not on the hand-lettered year labels, which wander by up
to 9 px. It predicts y(−20000) = 429.0 against a top rule measured at 428.0:
the frame's top border is the 20000 BCE gridline.

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

## What was measured

**Frame**: open. Top rule at y = 428, two verticals at x = 78.5 and 1400.5
down to y = 29753. No bottom rule. Width 4 px.

**Bands**: 10 one-degree flats:

| band | fill | band | fill |
|---|---|---|---|
| −5…−4 | `#C2C8E7` | 0…+1 | `#FEFDFD` |
| −4…−3 | `#D9DDF2` | +1…+2 | `#F8F0EC` |
| −3…−2 | `#E3E6F5` | +2…+3 | `#F5E9E3` |
| −2…−1 | `#ECEEF8` | +3…+4 | `#F2E1D9` |
| −1…0 | `#FDFDFE` | +4…+5 | `#EBD2C6` |

**Gridlines**: neutral black with opacity (per-channel ratios match within
0.005). Measured as ink = stroke-width × opacity, expressed at stroke-width 2
(= 1 px at the comic's 1x size):

| line | measured ink | stroke | opacity |
|---|---|---|---|
| vertical, per °C | 0.33 px | 2 | 0.165 |
| horizontal, per 100 yr | 0.138 px | 2 | 0.069 |
| horizontal, per 500 yr | 0.676 px | 2 | 0.338 |
| horizontal, "now" | 0.94 px | 2 | 0.470 |

Horizontals span the full width from 19900 BCE to 2100 CE; verticals the full
height. The 0 °C vertical is a separate opaque black 2 px rule. 12 px ticks hang
below the top rule at each whole degree.

## Verification

The SVG rasterised and compared with the original:

| feature | original | svg | delta |
|---|---|---|---|
| left rule | 78.5 | 78.5 | 0.0 |
| 0 °C axis | 739.5 | 739.0 | −0.5 |
| right rule | 1400.5 | 1399.5 | −1.0 |
| top rule | 428.0 | 427.5 | −0.5 |

Gridlines: 217 detected in the original, all matched in the SVG, mean delta
−0.51 px, max 4.47 px. Ink per class: 100 yr 0.132 vs 0.134; 500 yr 0.680 vs
0.676. The SVG has 222 lines: five are fully covered by artwork in the original.

## The curve

Extracted from the original by `extract_curve.py` (in `derivation/`). Five
paths, because a dash pattern cannot vary within one SVG path; they share
their junction nodes.

| path | style | nodes | span |
|---|---|---|---|
| `reconstruction` | dashed | 640 | 20000 BCE → 1858, −4.32 → −0.30 °C |
| `instrumental` | solid | 11 | 1858 → 2020, −0.30 → +0.74 °C |
| `scenario_current_path` | dashed | 17 | → +4.10 °C at 2098 |
| `scenario_optimistic` | dashed | 7 | → +2.00 °C at 2091 |
| `scenario_best_case` | dashed | 5 | → +1.19 °C at 2091 |

The dashed/solid boundary is at y = 29322 (year 1858); the instrumental record
starts in 1850 (y = 29317). The measured value is used.

| | historical | projections |
|---|---|---|
| colour | `#020101` | `#140B07` |
| width | 9 px | 9 px |
| dash / gap | 14 / 8 (period 22) | 20 / 11 (period 31) |

**Dashes.** The JSON stores the visible ink. A round linecap adds half a stroke
width at each end, so `build_svg.py` emits the geometric dash shortened and the
gap lengthened by one width: `"5 17"` for a measured 14 / 8. When retuning in
Inkscape, edit the geometric value.

The three projections carry a `stroke-dashoffset` that puts dash centres on the
measured positions. The main curve has none.

Verified against the original: centreline deviation rms 0.65 px (0.0049 °C),
p99 1.50 px, max 3.50 px; dash pattern 14 / 8 / 22; ink ratio svg/source
0.928.

### The shadow

`CURVE_SHADOW_STYLE` selects the implementation:

| style | what it is | Inkscape canvas | browser / export |
|---|---|---|---|
| `rings` (default) | nested translucent strokes, no filter | correct | correct |
| `blur` | `feGaussianBlur` + `feFlood` + `feComposite` | poor | correct |
| `dropshadow` | `feDropShadow` | object dropped | correct |
| `none` | — | — | — |

`rings` draws the curve six times underneath itself, offset (−1, 5), each copy
wider and fainter. Widths and opacities are a non-negative least-squares fit
to a 9 px stroke blurred at σ 4.0, peak alpha 0.140 (max error 0.013), then
scaled by `CURVE_SHADOW_STRENGTH`. The copies are `<use>` elements, so the
visible paths carry no `stroke-width` of their own.

Filter regions use absolute padding: the bounding box of a near-vertical open
path excludes its stroke.

## Other languages

Everything translatable is in the translation JSON (`../data/FORMAT.md`),
including the `locale` block, all entries, the hover text, the sources credit
and the attribution. There is no code-side fallback: a missing key fails. Layer
and object names stay English. Year labels follow the original: every BCE label
carries the era, the first three CE labels carry it, 1600 onwards are bare.

An `adaptation` block is duplicated per translation file; nothing checks that
editions agree.

### When translated text does not fit

In increasing order of intrusiveness:

- **`fontSize` / `wscale` / `lines`** on the entry. `wscale` condenses about
  the anchor.
- **`figureOffsets`**, e.g. `{"sub03": [72, 0]}`, when a wider label runs into
  its arrow. A figure carries the labels drawn on it (`FIGURE_LABELS`).
- **`at`** on the entry, to move the block.

The line breaker takes a fixed line count and has no width limit: a longer
string gives wider lines, not more of them.

### Attribution

The original work is cited from constants in `build_svg.py` (title, author,
URL, licence). The translation supplies the connective wording in a mandatory
`attribution` block and optional free-text `credits`. Credit lines are drawn
without glyph substitution; the build warns about characters the font lacks.

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
in em. `…` is not substituted: write `...`.

The degree exists only in the legacy Macintosh cmap subtable, where `0xB0` is
'infinity' by Mac Roman convention. Audit against the Unicode cmap only.

Every accented French capital (`À Â Ä Ç É È Ê Ë Î Ï Ô Ö Ù Û Ü Œ Ÿ`) is present.
