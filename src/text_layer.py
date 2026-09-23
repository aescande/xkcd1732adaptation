"""
Render the text entries of translation_<lang>_1732.json into SVG.

Line breaking runs at build time against the real font, so the SVG carries one
<text> per line with an explicit baseline and nothing is left for the renderer
to reflow.

Anchoring, per FORMAT.md:

    align=left    at = middle of the LEFT edge
    align=right   at = middle of the RIGHT edge
    align=center  at = the CENTRE

`at.y` is the block's mid-height, so a block gaining a line grows equally up
and down. Converting that to a first baseline needs the cap height, since the
ink of an all-caps line runs from cap-top to baseline:

    first_baseline = at.y + capHeight/2 - (n-1) * lineHeight / 2

Style resolution is entry -> its type's row in `defaults` -> the `*` row.
"""
import re
from collections import namedtuple

from linebreak import LineBreaker, Unsplittable
from typography import (BODY_INK, CAP, DISC_ADV_EM, FONT_STACK, GUILL_ADV_EM,
                        RULE_INK, advance, esc, guillemet_svg, markup, measurer,
                        runs_width, spacing_px, split_runs, text_width,
                        disc_svg)

_ANCHOR = {"left": "start", "right": "end", "center": "middle"}

# The sources credit runs up the right margin in grey rather than body ink.
SOURCES_INK = "#878686"
# Gap to the frame is 3px, as in the original. After rotate(90) the comma's
# descender is the leftmost ink.
SOURCES_DX = 6

# Colours keyed on `en` (never drawn, same across translations). A `fill` in
# the data overrides. Lettering inside a drawing takes the drawing's ink,
# measured on the crop's opaque pixels.
COLOUR_BY_EN = {
    "SUMMER SUN W/m² AT 60°N": "#8D8079",            # insolation chart
    "NOT A TRAP": "#1C110B",                          # on sub23 (horse)
    "THAT'S IT! I'M MOVING TO CANADA!": "#2B1F1A",   # in sub14's balloon
}

# A numeric field may carry a signed string instead of a number: "-5" means five
# less than whatever would otherwise apply, so an entry can nudge a default
# without restating it.
#
# letterSpacing is excluded: its values usually start with a minus, so a sign
# can't mark a relative value.
RELATIVE_KEYS = {"fontSize", "lineHeight", "wscale", "rotate"}
_RELATIVE_RE = re.compile(r"^[+-]\d*\.?\d+$")


def resolve(entry, doc, key, fallback=None):
    """entry override -> its type's row -> the '*' row -> fallback."""
    defaults = doc["defaults"]
    row = defaults.get(entry["type"], {})

    def inherited():
        if key in row:
            return row[key]
        return defaults.get("*", {}).get(key, fallback)

    if key in entry:
        value = entry[key]
        if (key in RELATIVE_KEYS and isinstance(value, str)
                and _RELATIVE_RE.match(value.strip())):
            base = inherited()
            return (base if isinstance(base, (int, float)) else 0) + float(value)
        return value
    return inherited()


def entry_fill(entry, doc):
    """JSON override -> code table -> per-type default."""
    fill = resolve(entry, doc, "fill")
    if fill:
        return fill
    if entry.get("en") in COLOUR_BY_EN:
        return COLOUR_BY_EN[entry["en"]]
    return RULE_INK if entry["type"] == "header" else BODY_INK


Block = namedtuple("Block", "lines size tracking ls_px leading x y first")


def layout(i, entry, doc, breaker_params):
    """Broken lines and geometry of entry i."""
    size = resolve(entry, doc, "fontSize", 42)
    tracking = resolve(entry, doc, "letterSpacing")
    ls_px = spacing_px(tracking, size)
    breaker = LineBreaker(measurer(size, ls_px), breaker_params)
    text = entry["text"]
    if isinstance(text, list):
        lines = [breaker.render(s) for s in text]
    else:
        try:
            lines = breaker.split(text, entry.get("lines", 1))
        except Unsplittable as exc:
            raise SystemExit(f"entry {i} ({entry.get('en')!r}): {exc}")
    leading = resolve(entry, doc, "lineHeight", size)
    x, y = entry["at"]
    first = y + CAP * size / 2.0 - (len(lines) - 1) * leading / 2.0
    return Block(lines, size, tracking, ls_px, leading, x, y, first)


def _left(x, width, anchor):
    """Left edge of a run of this width anchored at x."""
    if anchor == "start":
        return x
    return x - width if anchor == "end" else x - width / 2


def emit_runs(runs, x, baseline, size, ls_px, spacing_attr, fill):
    """Absolutely-positioned pieces, for a line containing an inline glyph.

    A plain line stays a single anchored <text>, which is far easier to edit.
    """
    out = []
    for kind, s, size_em, dy_em in runs:
        # No padding between runs: each substituted glyph carries its own
        # advance. The original sets W/m² and 60°N tight.
        if kind == "disc":
            out.append(disc_svg(x, baseline, size, fill))
            x += DISC_ADV_EM * size
        elif kind == "guill":
            out.append(guillemet_svg(x, baseline, size, fill, s))
            x += GUILL_ADV_EM * size
        elif kind == "text":
            # xml:space="preserve": a run after an inline glyph can begin with
            # a space ("W/m²| AT 60"), which SVG would otherwise collapse.
            out.append(f'        <text x="{x:.2f}" y="{baseline:.1f}" '
                       f'xml:space="preserve" text-anchor="start" '
                       f'font-family="{FONT_STACK}" font-size="{size}"'
                       f'{spacing_attr} fill="{fill}">{markup(s)}</text>\n')
            x += text_width(s, size, ls_px)
        elif kind == "shift":
            glyph_size = size_em * size
            out.append(f'        <text x="{x:.2f}" '
                       f'y="{baseline + dy_em * size:.1f}" text-anchor="start" '
                       f'font-family="{FONT_STACK}" '
                       f'font-size="{glyph_size:.1f}" fill="{fill}">'
                       f'{esc(s)}</text>\n')
            x += advance(s, glyph_size)
    return "".join(out)


def block_boxes(doc):
    """Ink bounding box of each entry, for its erase mask."""
    breaker_params = doc["locale"].get("linebreak", {})
    boxes = []
    for i, entry in enumerate(doc["entries"]):
        b = layout(i, entry, doc, breaker_params)
        width = max(runs_width(split_runs(l), b.size, b.ls_px) for l in b.lines)
        width *= resolve(entry, doc, "wscale", 1.0) or 1.0
        left = _left(b.x, width, _ANCHOR[entry["align"]])
        boxes.append({"i": i, "x": left, "y": b.first - CAP * b.size,
                      "w": width,
                      "h": (len(b.lines) - 1) * b.leading + CAP * b.size})
    return boxes


def build_text(doc):
    breaker_params = doc["locale"].get("linebreak", {})
    out = []
    for i, entry in enumerate(doc["entries"]):
        b = layout(i, entry, doc, breaker_params)
        x, y = b.x, b.y
        anchor = _ANCHOR[entry["align"]]
        fill = entry_fill(entry, doc)
        spacing_attr = f' letter-spacing="{b.tracking}"' if b.tracking else ""

        # Horizontal condense about the anchor, so the block still grows from
        # the edge `align` nominates. Inside any rotation, so the squeeze
        # happens in the block's own frame rather than the page's.
        condense = resolve(entry, doc, "wscale", 1.0)
        rotate = entry.get("rotate")
        transforms = []
        if rotate:
            transforms.append(f"rotate({rotate},{x},{y})")
        if condense and condense != 1.0:
            transforms.append(
                f"translate({x},0) scale({condense},1) translate({-x},0)")
        transform = f' transform="{" ".join(transforms)}"' if transforms else ""

        out.append(f'    <g id="text_{i:03d}" class="{entry["type"]}"'
                   f'{transform}>\n')
        for k, line in enumerate(b.lines):
            baseline = b.first + k * b.leading
            runs = split_runs(line)
            if len(runs) == 1 and runs[0][0] == "text":
                out.append(f'      <text x="{x}" y="{baseline:.1f}" '
                           f'text-anchor="{anchor}" font-family="{FONT_STACK}" '
                           f'font-size="{b.size}"{spacing_attr} fill="{fill}">'
                           f'{markup(line)}</text>\n')
                continue
            left = _left(x, runs_width(runs, b.size, b.ls_px), anchor)
            out.append('      <g class="inline">\n'
                       + emit_runs(runs, left, baseline, b.size, b.ls_px,
                                   spacing_attr, fill)
                       + '      </g>\n')
        out.append("    </g>\n")

    out.append(build_sources(doc))
    return "".join(out)


def build_sources(doc):
    """The credit line, running vertically up the right margin.

    Special-cased in the data too: it carries a full box rather than an anchor.
    """
    sources = doc.get("sources")
    if not sources:
        return ""
    x, y = sources["box"][0] + SOURCES_DX, sources["box"][1]
    size = doc["defaults"].get("meta", {}).get("fontSize", 35)
    tracking = doc["defaults"].get("*", {}).get("letterSpacing")
    spacing_attr = f' letter-spacing="{tracking}"' if tracking else ""
    return (f'    <g id="text_sources">\n'
            f'      <text x="{x}" y="{y}" text-anchor="start" '
            f'font-family="{FONT_STACK}" font-size="{size}"{spacing_attr} '
            f'fill="{SOURCES_INK}" '
            f'transform="rotate({sources.get("rotate", 90)},{x},{y})">'
            f'{esc(sources["text"])}</text>\n'
            f'    </g>\n')
