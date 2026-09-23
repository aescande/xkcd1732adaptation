# `translation_<lang>_1732.json`

Every string of one edition, and its layout. The renderer also reads
`curve_paths.json` and `figures/` from the same data folder.

```
locale        formatting of generated labels, line-breaking rules
sources       the sources credit, up the right margin
hover         the title text
defaults      style per entry type
entries       the 156 text blocks
attribution   required: wording around the citation of the original
credits       optional: extra credit lines
figureOffsets optional: figure moves for this translation
adaptation    optional: revisions to the 2016 strip; no effect when absent
```

All coordinates are **2x pixels**: the space of the 1480 × 29913 artwork, not
the 740-wide original.

Keys not listed here are refused by the build, as are unknown entry types.

A JSON file under `data/` carrying `entries` and `locale` is an edition, and
`tests/test_build.py` builds it and compares it with a recorded hash.

---

## `entries[]`

| Field | Type | Required | Meaning |
|---|---|---|---|
| `type` | string | yes | one of the eight types below |
| `en` | string | yes | the original English, flattened. Never drawn |
| `text` | string \| array | yes | what to draw |
| `align` | `left`\|`right`\|`center` | yes | which edge stays fixed |
| `at` | `[x, y]` | yes | the anchor point, see below |
| `lines` | int | no | lines to break `text` into. Default 1 |
| `fontSize` | number | no | px |
| `lineHeight` | number | no | baseline to baseline, px |
| `letterSpacing` | string \| number | no | `"-0.04em"`, `"-2px"` or px |
| `wscale` | number | no | horizontal condense factor about the anchor |
| `rotate` | number | no | degrees clockwise about `at`. Default 0 |
| `fill` | colour | no | overrides the ink colour |
| `onFigure` | string \| null | no | binds the entry to a figure, or (null) unbinds it |

Style fields resolve entry → the type's row in `defaults` → the `*` row. For
`fontSize`, `lineHeight`, `wscale` and `rotate`, a signed string is relative to
the inherited value: `"-5"` is five less.

**`en` must not be edited.** It identifies an entry across translations: it
keys the ink colours of lettering drawn inside figures, `FIGURE_LABELS` (the
labels that move with their figure) and `adaptation.entriesRemoved`.

### `at` is a mid-edge, not a corner

```
align = "left"     at = middle of the LEFT edge     grows rightward
align = "right"    at = middle of the RIGHT edge    grows leftward
align = "center"   at = the CENTRE of the block     grows both ways
```

The y component is the block's mid-height, so a block gaining a line grows
equally up and down. Blocks left of the curve are right-aligned so they grow
away from it, and the reverse on the right.

### `text`: string or array

- **string**: broken into `lines` lines by `src/linebreak.py`, with the
  parameters in `locale.linebreak`.
- **array**: one element per line, verbatim; `lines` is ignored.

The English edition uses the array form for 17 of its 63 multi-line blocks.

### `rotate`, `wscale`

Rotation is about `at`, after the block is laid out. `wscale` is applied inside
the rotation, in the block's own frame. Four entries are rotated (three
`figure`, one `dialogue`).

### `type`

`header` `story` `event` `dialogue` `figure` `bracket` `meta` `scenario`

Selects the row in `defaults`. `header` is drawn in black, the others in the
body ink.

### `onFigure`

Entries drawn on a figure (`FIGURE_LABELS` in `build_svg.py`) move with it.
`"onFigure": "sub08"` adds an entry to that figure; `"onFigure": null` removes
it.

---

## `defaults`

```json
"defaults": {
  "*":     { "letterSpacing": "-0.03em" },
  "story": { "fontSize": 42, "lineHeight": 42 },
  ...
}
```

One row per type, plus `*` for all types. Measured from the original.
`bracket` reads high (parenthesis glyphs overshoot the cap line), and
`figure`'s line height rests on a single two-line sample.

`meta.fontSize` also sets the size of `sources`, and `*.letterSpacing` its
tracking and that of the credit lines.

---

## `locale`

| Key | fr | en |
|---|---|---|
| `thousands_sep` | `""` | `""` |
| `decimal_sep` | `","` | `"."` |
| `era_bce` | `av. J.-C.` | `BCE` |
| `era_ce` | `apr. J.-C.` | `CE` |
| `degree` | `" °C"` | `"°C"` |
| `minus` | `−` (U+2212) | `-` |

These generate the 52 year labels, the 9 temperature labels and the 4.3 °C
span annotation, none of which are entries. Positions come from the axis
mapping:

```
x(T)    = 739.5 + 132.2 × T              T in °C
y(year) = 1.322092 × year + 26870.8521   astronomical years, 1 BCE = 0
```

The year labels are every 500 years to 1500 CE, then every 100 years, on one
linear scale.

### `locale.linebreak`

Parameters of the line breaker.

| Key | Purpose |
|---|---|
| `nbsp` | a space that is never a break |
| `protected` | regexes whose internal spaces become `nbsp` |
| `glue_before` | chars attaching to the preceding word (fr: `!?:;»`) |
| `glue_after` | chars attaching to the following word (fr: `«`) |
| `short_word_max` | a word this short should not end a line (fr 3, en 2) |
| `short_word_penalty` | cost of ending a line on such a word |
| `comma_bonus` | reward for breaking after a comma |
| `break_chars` | what counts as a comma above |

**`nbsp`.** The font has no U+00A0 glyph, so it is used as markup only: put it
wherever a break is forbidden (`FILM 300`, `ZHENG HE`). It is replaced by an ordinary
space before measuring and drawing.

---

## `sources`

```json
{ "en": "...", "text": "...", "box": [1405, 428, 1429, 1388],
  "rotate": 90, "align": "left" }
```

The credit running up the right margin, outside the frame. The renderer reads
`text`, `box[0]`, `box[1]` (the start point) and `rotate` (default 90).
`box[2]`, `box[3]` and `align` are not read.

---

## `hover`

```json
{ "en": "...", "text": "..." }
```

The title text. Not part of the artwork; written to the SVG `<title>`.

---

## `attribution` and `credits`

```json
"attribution": { "from": "D'APRÈS", "by": "DE",
                 "originalWorkLicensed": "ŒUVRE ORIGINALE SOUS LICENCE",
                 "unofficialAdaptation": "ADAPTATION NON OFFICIELLE" },
"credits": [ "ADAPTATION DU FICHIER ET TRADUCTION : ADRIEN ESCANDE" ]
```

All four `attribution` keys are required. The title, author, URL and licence
of the original come from `build_svg.py`. The result, below the frame:

```
<from> "<title>" <by> <author> — <url>
<originalWorkLicensed> <licence> — <unofficialAdaptation>
<each credits line>
```

---

## `figureOffsets`

```json
"figureOffsets": { "sub02": [-69, 0], "sub03": [72, 0] }
```

Moves figures by `[dx, dy]`, with the labels drawn on them. Used when
translated text changes a block's width. An unknown figure name is an error.

---

## `adaptation`

Revises the strip as a diff rather than by editing `entries`, so one file
builds either the 2016 original or an updated version.

```json
"adaptation": {
  "currentYear": 2026,
  "entriesRemoved": ["CURRENT PATH", "TEMPERATURES START TO LEVEL"],
  "entriesAdded": [ { a full entry object, text included } ],
  "figuresRemoved": ["sub29"],
  "figuresShifted": {"sub30": [40, 12]},
  "figuresAdded": [ {"file": "arrow_ssp370.png", "x": 1180, "y": 29610,
                     "width": 60, "height": 44, "connector": true} ]
}
```

Every key is optional.

| Key | Meaning |
|---|---|
| `currentYear` | The emphasised rule and its year label. Default 2016. The label keeps the gap the original leaves under 2000 (2016: +7 px, 2026: none). The 2100 label is dropped if "now" is less than 16 years before it |
| `entriesRemoved` | Named by `en`, see below |
| `entriesAdded` | Full entry objects, appended |
| `figuresRemoved` | Manifest names, no extension |
| `figuresShifted` | Added to `figureOffsets`. Labels drawn on a moved figure follow |
| `figuresAdded` | `connector` picks the layer, default false. The file stem becomes an XML id: `[A-Za-z0-9_-]+` |

### Naming entries

- An exact `en` wins: `"ICE"` never means a longer entry starting with it.
- Otherwise the opening words, ending on a word boundary. `"CURRENT PAT"` is
  refused; an ambiguous prefix is an error listing the candidates.
- A repeated `en` removes by occurrence: `ICE` twice removes the first two.

Two entries open `TEMPERATURES START`, so that one needs `TO LEVEL` or
`TO DECLINE`. Removals run before additions.

### Refusals

Unknown key; a name matching nothing or ambiguous; more occurrences than exist;
removing an entry bound to a figure; an unknown, colliding or badly named
image; an added entry missing a required field; a malformed shift; a
non-integer year. All fail before drawing; a missing PNG only warns.
`tests/test_adaptation.py` covers each.

The block is repeated in every translation file; nothing checks that they
agree.

---

## Not in this file

Drawn from constants in `build_svg.py`, not from entries: the 4.3 °C span
annotation (uses `decimal_sep` and `degree`), the insolation chart's axis
numbers 550 / 500 / 450, and the two header rules.
