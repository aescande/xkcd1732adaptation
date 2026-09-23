"""
Font, text measurement (HarfBuzz), and the glyphs the font lacks.
Shared by build_svg.py and text_layer.py.
"""
import functools
import os

try:
    import uharfbuzz as hb
except ImportError:
    raise SystemExit(
        "uharfbuzz is required: python -m pip install uharfbuzz (see README)")

BASE = os.path.dirname(os.path.abspath(__file__))
FONT_FILE = os.path.join(BASE, "..", "3rdparty", "xkcd-font", "xkcd-script.ttf")

FONT_FAMILY = "xkcd Script"        # the font's internal family name
FONT_STACK = ("'xkcd Script','xkcd-script','Humor Sans','Comic Neue',"
              "sans-serif")

# Munroe draws the rules and the title in black, but body text in a very dark
# navy: modal core pixel #0B0E1D across the story and event blocks.
RULE_INK = "#000000"
BODY_INK = "#0B0E1D"

_hb_face = hb.Face(hb.Blob.from_file_path(FONT_FILE))
_hb_font = hb.Font(_hb_face)
_UPM = _hb_face.upem


@functools.lru_cache(maxsize=None)
def advance(s, size):
    """Shaped advance width of s at this size, kerning included."""
    if not s:
        return 0.0
    buf = hb.Buffer()
    buf.add_str(s)
    buf.guess_segment_properties()
    hb.shape(_hb_font, buf)
    return sum(p.x_advance for p in buf.glyph_positions) * size / _UPM


def _cap_ratio():
    """Cap height as a fraction of em: the highest ink top in shaped
    "HAMBURGEFONS" (R, 0.707). Shaped rather than per letter: the font
    ligates, and the unligated N alone would give 0.725."""
    buf = hb.Buffer()
    buf.add_str("HAMBURGEFONS")
    buf.guess_segment_properties()
    hb.shape(_hb_font, buf)
    top = 0
    for info in buf.glyph_infos:
        ext = _hb_font.get_glyph_extents(info.codepoint)
        if ext is not None:
            top = max(top, ext.y_bearing)
    return top / _UPM


CAP = _cap_ratio()


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def spacing_px(spec, size):
    """'-0.04em', '-2px' or a bare number -> px at this font size."""
    if spec is None:
        return 0.0
    if isinstance(spec, (int, float)):
        return float(spec)
    s = str(spec).strip()
    if s.endswith("em"):
        return float(s[:-2]) * size
    if s.endswith("px"):
        s = s[:-2]
    return float(s)


# --------------------------------------------------------------- tracking

# "..." keeps its natural spacing: negative letter-spacing would merge the
# dots into a dash.
def untracked_chars(s):
    """How many characters of s are exempt from letter-spacing."""
    return 3 * s.count("...")


def markup(line):
    """Escape a line, exempting each "..." from letter-spacing."""
    return '<tspan letter-spacing="0">...</tspan>'.join(
        esc(p) for p in line.split("..."))


def measurer(size, ls_px):
    """Drawn width of a string: shaped advance, letter-spacing (except in
    "..."), and substituted glyphs at their real advance."""
    return lambda s: runs_width(split_runs(s), size, ls_px)


# ----------------------------------------------------------- inline glyphs
#
# The font's Unicode cmap has no U+00B0 (degree), U+00B2 (superscript two) or
# U+2082 (subscript two); for French it also lacks U+00AB/U+00BB (guillemets)
# and U+1D49 (superscript e). The degree appears only in the legacy Macintosh
# subtable, where 0xB0 maps to 'infinity' by Mac Roman convention, so anything
# reading that table draws the wrong glyph without erroring.
#
# The degree is therefore drawn as a disc, and the others are the ordinary
# glyph at a reduced size with a baseline shift. Everything is in em so it
# tracks the font size.
#
# The disc is filled, not a ring (measured: 9x10 px, area 60).
DISC_R_EM = 0.114        # radius
DISC_CY_EM = 0.647       # centre height above the baseline
DISC_ADV_EM = 0.25       # advance the disc occupies
DISC_CX_FRAC = 0.72      # position within that advance: it sits late, close
                         # to the following letter

# The shift is per character rather than per kind: at 0.54 em the '*' ink sits
# at -15..-1 from its own baseline while '2' sits at -17..-1, so one offset
# cannot place both.
#
# The guillemets are drawn: two chevrons of two straight strokes each. The
# stroke matches the font's stem width (0.090 em, from the "I"); the chevrons
# are about half the cap height, centred on the capitals.
GUILL_H_EM = 0.34         # full height of a chevron
GUILL_W_EM = 0.115        # horizontal depth, apex to arm ends
GUILL_GAP_EM = 0.135      # spacing between the two chevrons
GUILL_STROKE_EM = 0.085   # stroke width; the font's stems measure 0.090
GUILL_CY_EM = 0.30        # centre above the baseline, ~half the cap height

# Ink width, round caps included: the apex of the first chevron to the arm ends
# of the second, plus half a stroke of cap at each end.
GUILL_INK_EM = GUILL_W_EM + GUILL_GAP_EM + GUILL_STROKE_EM

# Side bearings: outer faces the sentence, inner faces the quoted words
# (negative, since the quoted text already has a space). Mirrored between
# « and »; same advance either way.
GUILL_BEARING_EM = 0.06           # outer: towards the rest of the sentence
GUILL_INNER_BEARING_EM = -0.038   # inner: towards the quoted words
GUILL_ADV_EM = GUILL_INK_EM + GUILL_BEARING_EM + GUILL_INNER_BEARING_EM

#          kind        glyph  size_em  dy_em
SPECIALS = {
    "°": ("disc",  None,   None,    None),
    "²": ("shift", "2",    0.54,   -0.31),   # W/m²
    "₂": ("shift", "2",    0.54,    0.19),   # CO₂
    "ᵉ": ("shift", "e",    0.54,   -0.40),   # French ordinal, XXᵉ
    "*": ("shift", "*",    0.54,   -0.50),   # footnote marker
    "«": ("guill", "left",  None,   None),   # French quotes
    "»": ("guill", "right", None,   None),
}

def split_runs(line):
    """Break a line into ('text', s, None, None) and inline-glyph runs."""
    runs, buf = [], []
    for ch in line:
        if ch in SPECIALS:
            if buf:
                runs.append(("text", "".join(buf), None, None))
                buf = []
            runs.append(SPECIALS[ch])
        else:
            buf.append(ch)
    if buf:
        runs.append(("text", "".join(buf), None, None))
    return runs


def text_width(s, size, ls_px):
    """Drawn width of a plain text run, letter-spacing included."""
    return advance(s, size) + ls_px * (len(s) - untracked_chars(s))


def runs_width(runs, size, ls_px):
    total = 0.0
    for kind, s, size_em, _dy in runs:
        if kind == "disc":
            total += DISC_ADV_EM * size
        elif kind == "guill":
            total += GUILL_ADV_EM * size
        elif kind == "text":
            total += text_width(s, size, ls_px)
        elif kind == "shift":
            total += advance(s, size_em * size)
    return total


def disc_svg(x, baseline, size, fill, indent=8):
    """The degree disc, centred within an advance starting at x."""
    pad = " " * indent
    return (f'{pad}<circle cx="{x + DISC_ADV_EM * size * DISC_CX_FRAC:.2f}" '
            f'cy="{baseline - DISC_CY_EM * size:.2f}" '
            f'r="{DISC_R_EM * size:.2f}" fill="{fill}"/>\n')


def guillemet_svg(x, baseline, size, fill, direction, indent=8):
    """A guillemet, as two chevrons within an advance starting at x.

    Stroked rather than filled, with round joins, so the corner and the tips
    carry the same softness the lettering has. One path holds both chevrons.
    """
    pad = " " * indent
    cy = baseline - GUILL_CY_EM * size
    h = GUILL_H_EM * size / 2.0
    w = GUILL_W_EM * size
    gap = GUILL_GAP_EM * size
    left = direction == "left"
    # Leading bearing: outer for «, inner for ». Then half a stroke for the
    # round cap.
    lead = GUILL_BEARING_EM if left else GUILL_INNER_BEARING_EM
    x0 = x + (lead + GUILL_STROKE_EM / 2.0) * size
    d = []
    for i in range(2):
        # Apex points the way the quote does; the arms open behind it.
        if left:
            apex = x0 + i * gap
            arm = apex + w
        else:
            apex = x0 + w + i * gap
            arm = apex - w
        d.append(f"M {arm:.2f} {cy - h:.2f} L {apex:.2f} {cy:.2f} "
                 f"L {arm:.2f} {cy + h:.2f}")
    return (f'{pad}<path d="{" ".join(d)}" fill="none" stroke="{fill}" '
            f'stroke-width="{GUILL_STROKE_EM * size:.2f}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>\n')
