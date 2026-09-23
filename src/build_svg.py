#!/usr/bin/env python3
"""
Build one language edition of xkcd 1732 ("Earth Temperature Timeline") as SVG.

Original: Randall Munroe, https://xkcd.com/1732/ - CC BY-NC 2.5
Derivative work; non-commercial use only, attribution required.

Reads the translation file given on the command line, and from the data
folder (default ../data, or --data):

    curve_paths.json               the temperature curve geometry
    figures/figures.json           where the 30 inline drawings go

Layer and object names are English, so the script itself is language-neutral.
The edition is decided entirely by the translation file it is given: there is
no default language and nothing in the code names one.

Coordinate system
-----------------
Pixel space of the original 2x bitmap (1480 x 29913). The viewBox is extended to the left
(PAD_LEFT) because era suffixes in most languages are wider than "BCE".

    x(T)    = 739.5 + 132.2 * T                 T in degrees C, plot spans -5..+5
    y(year) = 1.322092 * year + 26870.8521      astronomical years, 1 BCE = 0

The time mapping is fitted on the 216 horizontal gridlines of the original
(rms 0.46 px, max 4.96 px) rather than on the hand-lettered year labels, which
wander by up to 9 px. It predicts y(-20000) = 429.0 against a measured top rule
at 428.0: the top border of the frame *is* the 20000 BCE gridline.

Usage
-----
    python3 build_svg.py ../data/translation_fr_1732.json
    python3 build_svg.py ../data/translation_fr_1732.json timeline_fr.svg
    python3 build_svg.py ../data/translation_fr_1732.json --embed-font

The output defaults to ../results/<translation name>.svg. Figures are linked
relative to the output, so the SVG must stay where it was written.
"""

import argparse
import base64
import json
import os

import adaptation
import linebreak
import text_layer
import typography as ty
from typography import esc

# ---------------------------------------------------------------- settings

# Curve geometry, from extract_curve.py. Omitted if the file is absent.
CURVE_JSON = "curve_paths.json"

# ------------------------------------------------------------- attribution
#
# The original work is cited from these constants, so a translation can't alter
# them. The translation supplies the connective wording (all four
# ATTRIBUTION_KEYS required) and optional free-text `credits`. Composed as
#
#     <from> "<title>" <by> <author> - <url>
#     <originalWorkLicensed> <licence> - <unofficialAdaptation>
#
# The URL is drawn as text and wrapped in <a>.
ORIGINAL_TITLE = "A TIMELINE OF EARTH'S AVERAGE TEMPERATURE"
ORIGINAL_AUTHOR = "RANDALL MUNROE"
ORIGINAL_URL_TEXT = "XKCD.COM/1732"
ORIGINAL_URL = "https://xkcd.com/1732/"
LICENCE_TEXT = "CC BY-NC 2.5"
LICENCE_URL = "https://creativecommons.org/licenses/by-nc/2.5/"

ATTRIBUTION_KEYS = ("from", "by", "originalWorkLicensed", "unofficialAdaptation")

# Vector text reads heavier than the original's soft lettering. Chosen by eye,
# not measured. Applied to the layer so overlapping glyphs don't darken twice;
# axis and year labels are unaffected.
TEXT_OPACITY = 0.90

# Set in the grey of the sources credit, below the frame. The original leaves
# 160px of white there, which holds three lines; a fourth grows the page.
CREDIT_FS = 26
CREDIT_LEADING = 34
CREDIT_TOP_GAP = 46          # from the foot of the bands to the first cap
CREDIT_BOTTOM_MARGIN = 28
CREDIT_INK = "#878686"

# Curve shadow implementation:
#   "rings"       nested translucent strokes, no filter. Correct in Inkscape's
#                 canvas; slight banding.
#   "blur"        feGaussianBlur + feFlood + feComposite. Correct in browsers
#                 and on export, poor on Inkscape's canvas.
#   "dropshadow"  feDropShadow. Inkscape drops the whole object.
#   "none"        no shadow.
CURVE_SHADOW_STYLE = "rings"
CURVE_SHADOW = CURVE_SHADOW_STYLE != "none"

# "rings" draws the curve several times underneath itself, offset, each copy
# wider and fainter. The copies are <use> elements pointing at the real paths,
# which therefore carry no stroke-width of their own (it would override the
# <use>'s). Solid under the dashes: the shadow peaks at 0.140 in a gap too.
# Offset measured on the original.
CURVE_SHADOW_OFFSET = (-1, 5)

# Ring widths and opacities: non-negative least squares against a 9px stroke
# blurred at sigma 4.0, scaled to the peak alpha 0.140 measured on a row
# falling between two dashes (where the stroke itself contributes nothing).
# Max error 0.013 alpha. The outermost ring stops at 22px because that same
# measurement puts the shadow at zero by about +/-10px from the centreline.
CURVE_SHADOW_LAYERS = [   # (stroke-width, opacity) -- the fitted values
    (22.0, 0.0149), (18.6, 0.0166), (15.2, 0.0234),
    (11.8, 0.0270), (8.4, 0.0284), (5.0, 0.0243),
]
CURVE_SHADOW_COLOUR = "#000000"

# Multiplies the fitted ring opacities. The fit reproduces the measured shadow;
# this is the deliberate departure from it, because the ring approximation reads
# weaker than a true blur of the same total ink.
CURVE_SHADOW_STRENGTH = 1.3

# For the "blur" and "dropshadow" styles.
CURVE_SHADOW_SIGMA = 4.0
CURVE_SHADOW_OPACITY = 0.20
# Filter region padding, absolute: 3 sigma + offset + half stroke. The bbox of
# a near-vertical open path excludes the stroke, so percentages don't work.
CURVE_SHADOW_PAD = 40

# Crops from extract_figures.py, placed unscaled, in DATA_DIR.
FIGURES_MANIFEST = "figures/figures.json"
FIGURES_DIR = "figures"

# Connectors: arrows and leader lines. Listed by hand, since size doesn't
# separate them (sub25 is a thin arrow, sub26 a compass rose).
CONNECTOR_IDS = {1, 2, 3, 4, 5, 16, 17, 19, 20, 25, 27, 28, 29, 30}

# Labels drawn on a figure, which move with it. Chosen by eye: a bounding box
# includes unrelated text (sub15) and misses attached labels (BOSTON above
# sub06). Keyed by `en`; a repeated `en` binds by occurrence, so list in
# document order (checked).
FIGURE_LABELS = {
    # the glacial skyline: place names and ice depth, on and just above it
    "sub06": ["BOSTON", "NEW YORK", "ICE", "ICE", "MODERN SKYLINE"],
    # the insolation chart. Its 550/500/450 axis numbers are SUN_LABELS below,
    # not entries, and are shifted separately.
    "sub07": ["SUMMER SUN W/m² AT 60°N"],
    "sub08": ["ICE", "ICE", "ICE"],
    # inside the drawn brackets over the reconstruction samples
    "sub10": ["POSSIBLE", "UNLIKELY"],
    "sub14": ["THAT'S IT! I'M MOVING TO CANADA!"],
    "sub23": ["NOT A TRAP"],
}

# Filled by shift_figures. Used to move SUN_LABELS, which aren't entries.
APPLIED_SHIFT = {}

# Figures knock the gridlines out behind them. Original: fully erased to ~6px,
# half at ~20px, gone by ~45px. A dilate-then-blur edge is full at R - 2 sigma,
# half at R, zero at R + 2 sigma, so R = 24, sigma = 10.
ERASE_DILATE = 24     # feMorphology radius -- the flat, fully-erased core
ERASE_BLUR = 10       # feGaussianBlur stdDeviation -- the ramp after it
ERASE_HALO = 60       # R + ~3 sigma; how far the halo actually reaches
ERASE_MARGIN = 200    # mask/clip region padding, generous so figures can move

# Optional extra masks, for figures whose silhouette erases too little (the map
# is mostly transparent): figures/<name>_extra.png, same box. Paint black what
# to erase; it is inverted into the mask.

# Paths resolve relative to this file.
BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
DATA_DIR = os.path.join(REPO, "data")           # set by main() from --data
RESULTS_DIR = os.path.join(REPO, "results")
FIGURES_HREF = FIGURES_DIR     # figures folder relative to the output; main()

IMG_W, IMG_H = 1480, 29913
PAD_LEFT = 60                      # room to the left of x=0 for era suffixes
# Matching margin on the right, so the strip is not lopsided. The sources
# column already sits outside the frame on that side.
PAD_RIGHT = 60

# ------------------------------------------------------------- translation

def load_translation(path):
    """Load the translation file named on the command line."""
    if not os.path.exists(path):
        raise SystemExit(f"no such translation file: {path}")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# Keys the renderer reads. Anything else is refused, so a misspelt key cannot
# be silently ignored.
ENTRY_TYPES = {"header", "story", "event", "dialogue", "figure", "bracket",
               "meta", "scenario"}
STYLE_KEYS = {"fontSize", "lineHeight", "letterSpacing", "wscale", "fill"}
ENTRY_KEYS = {"type", "en", "text", "align", "at", "lines", "rotate",
              "onFigure"} | STYLE_KEYS
KNOWN_KEYS = {
    "": {"locale", "sources", "hover", "defaults", "entries", "attribution",
         "credits", "figureOffsets", "adaptation"},
    "locale": {"thousands_sep", "decimal_sep", "era_bce", "era_ce", "degree",
               "minus", "linebreak"},
    "locale.linebreak": set(linebreak.DEFAULT_PARAMS),
    "sources": {"en", "text", "box", "rotate", "align"},
    "hover": {"en", "text"},
    "attribution": set(ATTRIBUTION_KEYS),
    "defaults": ENTRY_TYPES | {"*"},
}


def check_entry(e, where):
    unknown = set(e) - ENTRY_KEYS
    if unknown:
        raise SystemExit(f"{where}: unknown key(s) {sorted(unknown)}")
    if e.get("type") not in ENTRY_TYPES:
        raise SystemExit(f"{where}: unknown type {e.get('type')!r}")


def check_keys(doc):
    """Refuse keys the renderer does not read."""
    for path, known in KNOWN_KEYS.items():
        obj = doc
        for k in filter(None, path.split(".")):
            obj = obj.get(k) or {}
        unknown = set(obj) - known
        if unknown:
            raise SystemExit(f"{path or 'top level'}: unknown key(s) "
                             f"{sorted(unknown)}")
    for row, style in doc.get("defaults", {}).items():
        unknown = set(style) - STYLE_KEYS
        if unknown:
            raise SystemExit(f"defaults.{row}: unknown key(s) {sorted(unknown)}")
    for i, e in enumerate(doc.get("entries", [])):
        check_entry(e, f"entry {i} ({e.get('en')!r})")
    for i, e in enumerate((doc.get("adaptation") or {}).get("entriesAdded", [])):
        check_entry(e, f"adaptation.entriesAdded[{i}]")


# Set by main(). No code-side fallback: a missing key fails.
TRANSLATION = None
LOC = None

# ---------------------------------------------------------------- geometry

YEAR_PX = 1.322092                 # px per year


def x_of_T(T):
    return 739.5 + 132.2 * T


def y_of_year(year):
    return YEAR_PX * year + 26870.8521

X_L, X_R = x_of_T(-5), x_of_T(5)   # 78.5, 1400.5
Y_TOP = 428.0                      # centre of the top rule == y(20000 BCE)
Y_BOT = 29753.0                    # bands stop here; the original has no bottom rule

STROKE_FRAME = 4
STROKE_ZERO = 2
TICK_LEN = 13
STROKE_TICK = 6

# Gridline weights. Measured as "ink" = stroke_width * opacity from the source
# bitmap, then expressed at stroke-width 2 (= 1px at the comic's 1x size).
# All three are neutral black: per-channel ratios matched to within 0.005.
STROKE_GRID = 2
OPACITY_GRID_V = 0.165             # one per whole degree C   (ink 0.33)
OPACITY_GRID_100 = 0.069           # every 100 years          (ink 0.138)
OPACITY_GRID_500 = 0.338           # every 500 years          (ink 0.676)
OPACITY_GRID_NOW = 0.470           # the 2016 rule            (ink 0.94)

GRID_YEAR_FIRST = -19900           # -20000 coincides with the top rule
GRID_YEAR_LAST = 2100
GRID_YEAR_STEP = 100
GRID_YEAR_STRONG = 500
# The emphasised rule and its year label; set by main() from the adaptation.
GRID_YEAR_NOW = adaptation.DEFAULT_YEAR_NOW

# The "now" label is pushed down to keep the gap the original leaves under
# 2000 (16 years + 7px), so a later year needs no nudge.
YEAR_LABEL_MIN_GAP = YEAR_PX * 16 + 7      # 28.15 px

BAND_FILLS = [
    "#C2C8E7", "#D9DDF2", "#E3E6F5", "#ECEEF8", "#FDFDFE",
    "#FEFDFD", "#F8F0EC", "#F5E9E3", "#F2E1D9", "#EBD2C6",
]

FS_TEMP = 31            # sized to match the original label WIDTH (53px for "+3°C")
TEMP_LETTER_SPACING = "-0.05em"
FS_YEAR = 32
FS_ERA = 20
YEAR_X = 72.0
ERA_DY = 22

# ---------------------------------------------------------------- labels

def group_digits(n):
    return f"{n:,}".replace(",", LOC["thousands_sep"])


def year_labels():
    """(baseline_y, number, era_or_None, inline)"""
    out = []
    for yr in range(-20000, 0, 500):
        out.append((y_of_year(yr), group_digits(-yr), LOC["era_bce"], False))

    out.append((y_of_year(0) - 16, "1", LOC["era_bce"], True))
    out.append((y_of_year(0) + 20, "1", LOC["era_ce"], True))

    for yr in (500, 1000, 1500):
        out.append((y_of_year(yr), group_digits(yr), LOC["era_ce"], False))

    centennial = (1600, 1700, 1800, 1900, 2000)
    for yr in centennial:
        out.append((y_of_year(yr), group_digits(yr), None, False))

    now = GRID_YEAR_NOW
    gap = YEAR_PX * (now - centennial[-1])
    out.append((y_of_year(now) + max(0.0, YEAR_LABEL_MIN_GAP - gap),
                group_digits(now), None, False))

    # Skipped if "now" has caught up with it, which would stack two labels.
    if GRID_YEAR_LAST - now >= 16:
        out.append((y_of_year(GRID_YEAR_LAST), group_digits(GRID_YEAR_LAST),
                    None, False))
    return out

# ---------------------------------------------------------------- svg

def layer(label, body, lid, locked=False, style="display:inline"):
    ins = ' sodipodi:insensitive="true"' if locked else ""
    return (f'  <g inkscape:groupmode="layer" inkscape:label="{label}" '
            f'id="{lid}" style="{style}"{ins}>\n{body}  </g>\n')


def build_bands():
    # Wrapped in an inner group so the erasers can <use> it: each eraser paints
    # the bands back over the gridlines, which keeps the colours linked rather
    # than duplicated.
    out = ['    <g id="bands_group">\n']
    for i, fill in enumerate(BAND_FILLS):
        T = -5 + i
        x0, x1 = x_of_T(T), x_of_T(T + 1)
        out.append(f'      <rect x="{x0:.2f}" y="{Y_TOP:.2f}" width="{x1 - x0:.2f}" '
                   f'height="{Y_BOT - Y_TOP:.2f}" fill="{fill}" '
                   f'id="band_{T:+d}_{T + 1:+d}"/>\n')
    out.append('    </g>\n')
    return "".join(out)


def build_gridlines():
    """Vertical rule per degree, horizontal rule per century, both translucent."""
    out = ['    <g id="gridlines_vertical" stroke="' + ty.RULE_INK +
           f'" stroke-width="{STROKE_GRID}" opacity="{OPACITY_GRID_V}">\n']
    for T in range(-4, 5):
        if T == 0:
            continue                       # the opaque zero axis covers this one
        x = x_of_T(T)
        out.append(f'      <line x1="{x:.2f}" y1="{Y_TOP:.2f}" x2="{x:.2f}" '
                   f'y2="{Y_BOT:.2f}" id="gridline_v_{T:+d}"/>\n')
    out.append('    </g>\n')

    groups = {
        "gridlines_century": (OPACITY_GRID_100, []),
        "gridlines_half_millennium": (OPACITY_GRID_500, []),
        "gridline_present_day": (OPACITY_GRID_NOW, [GRID_YEAR_NOW]),
    }
    for yr in range(GRID_YEAR_FIRST, GRID_YEAR_LAST + 1, GRID_YEAR_STEP):
        key = ("gridlines_half_millennium" if yr % GRID_YEAR_STRONG == 0
               else "gridlines_century")
        groups[key][1].append(yr)

    for gid, (op, years) in groups.items():
        out.append(f'    <g id="{gid}" stroke="{ty.RULE_INK}" '
                   f'stroke-width="{STROKE_GRID}" opacity="{op}">\n')
        for yr in years:
            y = y_of_year(yr)
            out.append(f'      <line x1="{X_L:.2f}" y1="{y:.2f}" x2="{X_R:.2f}" '
                       f'y2="{y:.2f}" id="gridline_h_{yr}"/>\n')
        out.append('    </g>\n')
    return "".join(out)


def build_zero_axis():
    x = x_of_T(0)
    return (f'    <line x1="{x:.2f}" y1="{Y_TOP:.2f}" x2="{x:.2f}" y2="{Y_BOT:.2f}" '
            f'stroke="{ty.RULE_INK}" stroke-width="{STROKE_ZERO}" id="zero_axis"/>\n')


# Two rules in the header, measured: x 426-1059, y 157 and 268, 3px.
HEADER_RULES = [(426, 1059, 157), (426, 1059, 268)]
STROKE_HEADER_RULE = 3


def build_header_rules():
    out = []
    for i, (x0, x1, y) in enumerate(HEADER_RULES):
        out.append(f'    <line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" '
                   f'stroke="{ty.RULE_INK}" stroke-width="{STROKE_HEADER_RULE}" '
                   f'stroke-linecap="butt" id="header_rule_{i + 1}"/>\n')
    return "".join(out)


def build_frame():
    d = (f"M {X_L:.2f} {Y_BOT:.2f} L {X_L:.2f} {Y_TOP:.2f} "
         f"L {X_R:.2f} {Y_TOP:.2f} L {X_R:.2f} {Y_BOT:.2f}")
    out = [f'    <path d="{d}" fill="none" stroke="{ty.RULE_INK}" '
           f'stroke-width="{STROKE_FRAME}" stroke-linecap="butt" id="frame"/>\n']
    for T in range(-4, 5):
        if T == 0:
            continue
        x = x_of_T(T)
        out.append(f'    <line x1="{x:.2f}" y1="{Y_TOP:.2f}" x2="{x:.2f}" '
                   f'y2="{Y_TOP + TICK_LEN:.2f}" stroke="{ty.RULE_INK}" '
                   f'stroke-width="{STROKE_TICK}" stroke-linecap="butt" '
                   f'id="tick_{T:+d}"/>\n')
    return "".join(out)


Y_TEMP_BASE = 419          # baseline of the temperature labels, measured

def degree_label(head, suf, fs, ls, cx, baseline, eid):
    """A '<digits> ° <suffix>' label, laid out piecewise around a drawn disc.

    Centred on cx.
    """
    lp = ty.spacing_px(ls, fs)
    w = lambda s: ty.text_width(s, fs, lp)
    total = w(head) + ty.DISC_ADV_EM * fs + w(suf)
    x0 = cx - total / 2.0
    xd = x0 + w(head)
    sp = f' letter-spacing="{ls}"' if ls else ""
    txt = (lambda x, s: f'      <text x="{x:.2f}" y="{baseline}" '
                        f'text-anchor="start" font-family="{ty.FONT_STACK}" '
                        f'font-size="{fs}"{sp} fill="{ty.RULE_INK}">{esc(s)}</text>\n')
    svg = (f'    <g id="{eid}">\n'
           + txt(x0, head)
           + ty.disc_svg(xd, baseline, fs, ty.RULE_INK, indent=6)
           + txt(xd + ty.DISC_ADV_EM * fs, suf)
           + '    </g>\n')
    return svg


def build_temperature_labels():
    """Sized to match the original's *width* (53px for '+3°C') rather than its
    cap height, so the digits come out shorter than Munroe's 28px."""
    pre, _, suf = LOC["degree"].partition("°")
    out = []
    for T in range(-4, 5):
        sign = LOC["minus"] if T < 0 else ("+" if T > 0 else "")
        out.append(degree_label(f"{sign}{abs(T)}{pre}", suf, FS_TEMP,
                                TEMP_LETTER_SPACING, x_of_T(T), Y_TEMP_BASE,
                                f"temp_label_{T:+d}"))
    return "".join(out)


# Span annotation. Measured: ink 79px wide, baseline 492, between arrow halves
# ending at x=411 and resuming at 503. fs=41 untracked (tracking crushes the
# decimal point).
SPAN_VALUE = "4.3"
SPAN_CX, SPAN_BASELINE, SPAN_FS = 459, 492, 41


# Axis numbers of the insolation chart (sub07); not entries, since they don't
# vary by language. Right-aligned at x=948, in the chart's sepia. fs=18 matches
# the width (the cap height would need 26). Moved with sub07.
SUN_LABEL_X = 948
SUN_LABEL_FS = 18
SUN_LABEL_COLOUR = "#8D8079"
SUN_LABELS = [("550", 2288), ("500", 2334), ("450", 2380)]


def build_sun_labels():
    dx, dy = APPLIED_SHIFT.get("sub07", (0, 0))
    out = []
    for txt, base in SUN_LABELS:
        base += dy
        out.append(f'    <text x="{SUN_LABEL_X + dx}" y="{base}" text-anchor="end" '
                   f'font-family="{ty.FONT_STACK}" font-size="{SUN_LABEL_FS}" '
                   f'fill="{SUN_LABEL_COLOUR}" id="sun_label_{txt}">{txt}</text>\n')
    return "".join(out)


def build_span_annotation():
    pre, _, suf = LOC["degree"].partition("°")
    val = SPAN_VALUE.replace(".", LOC["decimal_sep"])
    return degree_label(val + pre, suf, SPAN_FS, None,
                        SPAN_CX, SPAN_BASELINE, "span_annotation")


def build_year_labels():
    out = []
    for i, (ybase, num, era, inline) in enumerate(year_labels()):
        if inline:
            # One <text>, no <tspan>: with text-anchor=end, some renderers
            # anchor a sized tspan separately.
            out.append(f'    <text x="{YEAR_X:.2f}" y="{ybase:.1f}" '
                       f'text-anchor="end" font-family="{ty.FONT_STACK}" '
                       f'font-size="{FS_ERA + 4}" fill="{ty.RULE_INK}" '
                       f'id="year_label_{i}">{esc(num)} {esc(era)}</text>\n')
            continue
        out.append(f'    <text x="{YEAR_X:.2f}" y="{ybase:.1f}" text-anchor="end" '
                   f'font-family="{ty.FONT_STACK}" font-size="{FS_YEAR}" fill="{ty.RULE_INK}" '
                   f'id="year_label_{i}">{esc(num)}</text>\n')
        if era:
            out.append(f'    <text x="{YEAR_X:.2f}" y="{ybase + ERA_DY:.1f}" '
                       f'text-anchor="end" font-family="{ty.FONT_STACK}" '
                       f'font-size="{FS_ERA}" fill="{ty.RULE_INK}" '
                       f'id="year_label_{i}_era">{esc(era)}</text>\n')
    return "".join(out)


def load_curve():
    path = os.path.join(DATA_DIR, CURVE_JSON)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _erase_filter(prefix, n, box_w, box_h, halo, dilate, blur):
    """Dilate-then-blur halo of the target's alpha, as a white fill. The
    region is a percentage of the box, giving the same reach at any size."""
    px = 100.0 * halo / box_w
    py = 100.0 * halo / box_h
    return (f'    <filter id="{prefix}_spread_{n}" x="{-px:.1f}%" y="{-py:.1f}%" '
            f'width="{100 + 2 * px:.1f}%" height="{100 + 2 * py:.1f}%">\n'
            f'      <feMorphology in="SourceAlpha" operator="dilate" '
            f'radius="{dilate}" result="d"/>\n'
            f'      <feGaussianBlur in="d" stdDeviation="{blur}" result="b"/>\n'
            f'      <feFlood flood-color="#ffffff" result="f"/>\n'
            f'      <feComposite in="f" in2="b" operator="in"/>\n'
            '    </filter>\n')


def _erase_mask(prefix, n, target, region, extra=""):
    """Mask (the filtered target, plus an optional extra image) and clip rect.
    `region` is (x, y, w, h), already formatted."""
    x, y, w, h = region
    return (f'    <mask id="{prefix}_mask_{n}" maskUnits="userSpaceOnUse" '
            f'x="{x}" y="{y}" width="{w}" height="{h}">\n'
            f'{extra}'
            f'      <use xlink:href="#{target}" '
            f'filter="url(#{prefix}_spread_{n})"/>\n'
            '    </mask>\n'
            f'    <clipPath id="{prefix}_clip_{n}" clipPathUnits="userSpaceOnUse">\n'
            f'      <rect x="{x}" y="{y}" width="{w}" height="{h}"/>\n'
            '    </clipPath>\n')


def _eraser(prefix, n):
    """The bands painted back through a mask, over the gridlines."""
    return (f'    <g id="{prefix}_{n}" clip-path="url(#{prefix}_clip_{n})" '
            f'mask="url(#{prefix}_mask_{n})">\n'
            '      <use xlink:href="#bands_group"/>\n'
            '    </g>\n')


def build_defs(curve, figures, boxes):
    body = [build_curve_shadow_defs(curve), build_text_erase_defs(boxes)]
    # Inverts an extra mask so black marks what to erase. sRGB interpolation,
    # or the default linearRGB skews the black/white mapping.
    body.append(
        '    <filter id="mask_invert" x="0%" y="0%" width="100%" height="100%" '
        'color-interpolation-filters="sRGB">\n'
        '      <feColorMatrix type="matrix" values="'
        '-1 0 0 0 1  0 -1 0 0 1  0 0 -1 0 1  0 0 0 1 0"/>\n'
        '    </filter>\n')
    if figures:
        # Keyed on SourceAlpha: the map's ice fills are pale, so luminance
        # would erase nothing.
        for f in figures:
            body.append(_erase_filter("erase", adaptation.stem(f), f["width"],
                                      f["height"], ERASE_HALO, ERASE_DILATE,
                                      ERASE_BLUR))
        for f in figures:
            n = adaptation.stem(f)
            mx, my = f["x"] - ERASE_MARGIN, f["y"] - ERASE_MARGIN
            mw, mh = f["width"] + 2 * ERASE_MARGIN, f["height"] + 2 * ERASE_MARGIN
            extra = ""
            name = f"{n}_extra.png"
            if os.path.exists(os.path.join(DATA_DIR, FIGURES_DIR, name)):
                rel = f"{FIGURES_HREF}/{name}"
                extra = (f'      <image xlink:href="{rel}" '
                         f'x="{f["x"]}" y="{f["y"]}" '
                         f'width="{f["width"]}" height="{f["height"]}" '
                         f'filter="url(#mask_invert)"/>\n')
                print(f"  extra erase mask: {rel}")
            # The extra mask goes first: it is opaque, so the halo is painted
            # over it and the two union.
            body.append(_erase_mask("erase", n, f"figure_{n}",
                                    tuple(str(v) for v in (mx, my, mw, mh)),
                                    extra))
    return "  <defs>\n" + "".join(body) + "  </defs>\n"


# Text knocks the gridlines out as the figures do, with a tighter halo.
TEXT_ERASE_DILATE = 20
TEXT_ERASE_BLUR = 8
TEXT_ERASE_HALO = 60
TEXT_ERASE_MARGIN = 120

# Per block, like the figures: a single full-canvas filter region is too large
# for Inkscape.


def build_text_erase_defs(boxes):
    body = []
    for b in boxes:
        n = f'{b["i"]:03d}'
        mx, my = b["x"] - TEXT_ERASE_MARGIN, b["y"] - TEXT_ERASE_MARGIN
        mw = b["w"] + 2 * TEXT_ERASE_MARGIN
        mh = b["h"] + 2 * TEXT_ERASE_MARGIN
        body.append(_erase_filter("terase", n, max(b["w"], 1), max(b["h"], 1),
                                  TEXT_ERASE_HALO, TEXT_ERASE_DILATE,
                                  TEXT_ERASE_BLUR))
        body.append(_erase_mask("terase", n, f"text_{n}",
                                tuple(f"{v:.0f}" for v in (mx, my, mw, mh))))
    return "".join(body)


def build_text_erasers(boxes):
    return "".join(_eraser("terase", f'{b["i"]:03d}') for b in boxes)


def build_erasers(figures):
    """The bands painted back over the gridlines behind each figure. The mask
    follows the live figure; the clip rect doesn't, so a figure can move up to
    ERASE_MARGIN."""
    return "".join(_eraser("erase", adaptation.stem(f)) for f in figures)


def path_extent(pts, pad):
    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    return (min(xs) - pad, min(ys) - pad,
            max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad)


def build_curve_shadow(doc):
    """Shadow copies of the curve, drawn beneath it. See CURVE_SHADOW_STYLE."""
    if not (doc and CURVE_SHADOW):
        return ""
    dx, dy = CURVE_SHADOW_OFFSET

    if CURVE_SHADOW_STYLE == "rings":
        out = [f'    <g id="curve_shadow" transform="translate({dx},{dy})" '
               f'fill="none" stroke="{CURVE_SHADOW_COLOUR}" '
               f'stroke-linecap="round" stroke-linejoin="round">\n']
        for w, op in CURVE_SHADOW_LAYERS:
            out.append(f'      <g stroke-width="{w:g}" '
                       f'opacity="{op * CURVE_SHADOW_STRENGTH:.4f}">\n')
            for p in doc["paths"]:
                out.append(f'        <use xlink:href="#curve_{p["id"]}"/>\n')
            out.append('      </g>\n')
        out.append('    </g>\n')
        return "".join(out)

    # blur / dropshadow: one filtered group per path. Filtering a group rather
    # than the <use> directly is the documented workaround for stroked open
    # paths vanishing under a filter.
    out = [f'    <g id="curve_shadow" transform="translate({dx},{dy})">\n']
    for p in doc["paths"]:
        out.append(f'      <g filter="url(#curve_shadow_{p["id"]})">\n'
                   f'        <use xlink:href="#curve_{p["id"]}"/>\n'
                   '      </g>\n')
    out.append('    </g>\n')
    return "".join(out)


def build_curve_shadow_defs(doc):
    if not (doc and CURVE_SHADOW) or CURVE_SHADOW_STYLE == "rings":
        return ""
    body = []
    for p in doc["paths"]:
        x, y, w, h = path_extent(p["points"], CURVE_SHADOW_PAD)
        region = (f'filterUnits="userSpaceOnUse" x="{x:.1f}" y="{y:.1f}" '
                  f'width="{w:.1f}" height="{h:.1f}"')
        if CURVE_SHADOW_STYLE == "dropshadow":
            prim = (f'      <feDropShadow dx="0" dy="0" '
                    f'stdDeviation="{CURVE_SHADOW_SIGMA}" '
                    f'flood-color="{CURVE_SHADOW_COLOUR}" '
                    f'flood-opacity="{CURVE_SHADOW_OPACITY}"/>\n')
        else:
            # No feMerge of SourceGraphic: this group is a shadow-only copy
            # sitting under the real curve, so re-merging the source would
            # paint a second full-opacity stroke.
            prim = (f'      <feGaussianBlur in="SourceAlpha" '
                    f'stdDeviation="{CURVE_SHADOW_SIGMA}" result="b"/>\n'
                    f'      <feFlood flood-color="{CURVE_SHADOW_COLOUR}" '
                    f'flood-opacity="{CURVE_SHADOW_OPACITY}" result="c"/>\n'
                    f'      <feComposite in="c" in2="b" operator="in"/>\n')
        body.append(f'    <filter id="curve_shadow_{p["id"]}" {region}>\n'
                    f'{prim}    </filter>\n')
    return "".join(body)


def build_curve(doc):
    """One <path> per section. A dash pattern cannot vary within a single path,
    so the dashed reconstruction and the solid instrumental run must be separate
    elements; they share the junction node so the join is seamless.

    stroke-width is set on the wrapping group, not on the paths: the shadow
    <use> elements need to override it, and an attribute on the referenced
    element would win over the one on the <use>."""
    if not doc:
        return ""
    widths = {p["stroke"]["width"] for p in doc["paths"]}
    assert len(widths) == 1, "paths differ in stroke-width; group cannot carry it"
    out = [f'    <g id="curve_strokes" fill="none" '
           f'stroke-width="{widths.pop()}" '
           f'stroke-linecap="round" stroke-linejoin="round">\n']
    for p in doc["paths"]:
        pts = p["points"]
        st = p["stroke"]
        d = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in pts)
        dash = ""
        if p["style"] == "dashed":
            # The JSON dash is the visible ink. Round caps add half a width at
            # each end, so the dash is shortened and the gap lengthened by one
            # width.
            on, off = st["dasharray"]
            w = st["width"]
            on, off = max(0.01, on - w), off + w
            dash = f' stroke-dasharray="{on:g} {off:g}"'
            if st.get("dashoffset"):
                dash += f' stroke-dashoffset="{st["dashoffset"]:g}"'
        out.append(f'      <path id="curve_{p["id"]}" d="{d}" '
                   f'stroke="{st["colour"]}"{dash}/>\n')
    out.append('    </g>\n')
    return "".join(out)


def load_figures():
    path = os.path.join(DATA_DIR, FIGURES_MANIFEST)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def label_owners(doc):
    """Entry index -> the figure it is drawn on. An entry's `onFigure` adds or
    (null) removes a link. Named `onFigure` because `figure` is a `type` value.
    """
    entries = doc["entries"]
    # Where each `en` occurs, in document order.
    occurrences = {}
    for i, entry in enumerate(entries):
        occurrences.setdefault(entry.get("en"), []).append(i)

    owner = {}
    taken = {}
    resolved = []
    for name, labels in FIGURE_LABELS.items():
        for en in labels:
            nth = taken.get(en, 0)
            taken[en] = nth + 1
            hits = occurrences.get(en, ())
            if nth >= len(hits):
                raise SystemExit(
                    f"FIGURE_LABELS {name}: no entry with en={en!r}"
                    + (f" beyond the {len(hits)} the file has"
                       if hits else " anywhere in the file"))
            owner[hits[nth]] = name
            resolved.append(hits[nth])

    # Repeated labels bind correctly only if the table is in document order.
    if resolved != sorted(resolved):
        raise SystemExit("FIGURE_LABELS is not in document order")

    for i, entry in enumerate(entries):
        if "onFigure" in entry:
            if entry["onFigure"]:
                owner[i] = entry["onFigure"]
            else:
                owner.pop(i, None)
    return owner


def shift_figures(figures, doc):
    """Apply `figureOffsets` in place, moving each figure's labels with it.
    Manual, not derived: long arrows are pinned at both ends."""
    offsets = doc.get("figureOffsets") or {}
    if not offsets:
        return
    known = {adaptation.stem(f) for f in figures}
    for name in offsets:
        if name not in known:
            raise SystemExit(f"figureOffsets: no figure named {name}")
    owner = label_owners(doc)
    for f in figures:
        name = adaptation.stem(f)
        if name not in offsets:
            continue
        dx, dy = offsets[name]
        f["x"] += dx
        f["y"] += dy
        APPLIED_SHIFT[name] = (dx, dy)
        moved = [i for i, o in owner.items() if o == name]
        for i in moved:
            at = doc["entries"][i]["at"]
            at[0] += dx
            at[1] += dy
        with_labels = f" with {len(moved)} label(s)" if moved else ""
        print(f"  shifted {name} by ({dx:+g}, {dy:+g}){with_labels}")


def build_figures(figures, connectors):
    """Place each crop at its recorded bounding box. No scaling: width and
    height come straight from the manifest and match the PNG's pixel size."""
    out = []
    for f in figures:
        if adaptation.is_connector(f, CONNECTOR_IDS) != connectors:
            continue
        out.append(
            f'    <image id="figure_{adaptation.stem(f)}" '
            f'xlink:href="{FIGURES_HREF}/{f["file"]}" '
            f'x="{f["x"]}" y="{f["y"]}" '
            f'width="{f["width"]}" height="{f["height"]}"/>\n'
        )
    return "".join(out)


def build_font_face():
    """The lettering face as @font-face. Split lines are positioned from its
    metrics, so another face misplaces them. Ignored by Inkscape."""
    with open(ty.FONT_FILE, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()
    return ('  <defs><style type="text/css">\n'
            f'    @font-face {{ font-family: "{ty.FONT_FAMILY}"; font-style: normal;\n'
            '      font-weight: normal;\n'
            f'      src: url("data:font/ttf;base64,{b64}") format("truetype"); '
            '}\n'
            '  </style></defs>\n')


def credit_segments(doc):
    """The credit lines, each a list of (text, url or None) pieces."""
    att = doc.get("attribution")
    if not att:
        raise SystemExit(
            "the translation file has no `attribution` block; it must carry "
            + ", ".join(ATTRIBUTION_KEYS))
    missing = [k for k in ATTRIBUTION_KEYS if not str(att.get(k, "")).strip()]
    if missing:
        raise SystemExit("attribution is missing: " + ", ".join(missing))

    lines = [
        [(f'{att["from"]} "{ORIGINAL_TITLE}" {att["by"]} {ORIGINAL_AUTHOR} — ',
          None),
         (ORIGINAL_URL_TEXT, ORIGINAL_URL)],
        [(f'{att["originalWorkLicensed"]} ', None),
         (LICENCE_TEXT, LICENCE_URL),
         (f' — {att["unofficialAdaptation"]}', None)],
    ]
    # Optional (none in the English edition).
    for line in doc.get("credits") or []:
        lines.append([(line, None)])

    # Drawn as plain runs, without glyph substitution.
    unknown = {c for segs in lines for t, _ in segs for c in t
               if c in ty.SPECIALS}
    if unknown:
        print(f"  !! credits use {''.join(sorted(unknown))}, which the font "
              f"cannot draw here -- rephrase, or they will render as boxes")
    return lines


def credit_geometry(n):
    """First baseline, and the page height needed to hold n credit lines."""
    first = Y_BOT + CREDIT_TOP_GAP + ty.CAP * CREDIT_FS
    last = first + (n - 1) * CREDIT_LEADING
    return first, max(IMG_H, int(last + CREDIT_BOTTOM_MARGIN + 0.5))


def build_credits(doc, lines):
    first, _ = credit_geometry(len(lines))
    tracking = doc["defaults"].get("*", {}).get("letterSpacing")
    spacing = f' letter-spacing="{tracking}"' if tracking else ""
    out = []
    for k, segs in enumerate(lines):
        parts = []
        for text, url in segs:
            if url:
                parts.append(f'<a href="{esc(url)}" target="_blank" '
                             f'rel="noopener"><tspan>{esc(text)}</tspan></a>')
            else:
                parts.append(esc(text))
        out.append(f'    <text x="{X_L:.1f}" y="{first + k * CREDIT_LEADING:.1f}" '
                   f'xml:space="preserve" text-anchor="start" '
                   f'font-family="{ty.FONT_STACK}" font-size="{CREDIT_FS}"'
                   f'{spacing} fill="{CREDIT_INK}" id="credit_{k}">'
                   f'{"".join(parts)}</text>\n')
    return "".join(out)


HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.0.dtd"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:cc="http://creativecommons.org/ns#"
     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
     width="{w}" height="{h}" viewBox="{vx} 0 {w} {h}"
     version="1.1" id="svg_root">
  <title>{title}</title>
  <desc>Adapted from xkcd 1732 by Randall Munroe ({url}), {licence}. Non-commercial use only.</desc>
  <metadata>
    <rdf:RDF><cc:Work rdf:about="">
      <dc:title>A Timeline of Earth's Average Temperature</dc:title>
      <dc:source>{url}</dc:source>
      <dc:creator><cc:Agent><dc:title>Randall Munroe (original work)</dc:title></cc:Agent></dc:creator>
      <cc:license rdf:resource="http://creativecommons.org/licenses/by-nc/2.5/"/>
{credits}    </cc:Work></rdf:RDF>
  </metadata>
"""


def build_metadata(lines):
    """The credit lines, mirrored into the RDF."""
    return "".join("      <dc:description>%s</dc:description>\n"
                   % esc("".join(t for t, _ in segs)) for segs in lines)


def build(embed_font=False):
    curve = load_curve()
    figures = load_figures()
    # Figures are added or removed, then shifted, before any box is computed.
    if figures:
        note = adaptation.apply_figures(TRANSLATION, figures,
                                        os.path.join(DATA_DIR, FIGURES_DIR))
        if note:
            print(note)
        shift_figures(figures, TRANSLATION)
    # The page grows if the credits exceed the 160px below the bands; IMG_H
    # stays the artwork's height.
    boxes = text_layer.block_boxes(TRANSLATION)
    credit_lines = credit_segments(TRANSLATION)
    _, page_h = credit_geometry(len(credit_lines))
    p = [HEADER.format(w=IMG_W + PAD_LEFT + PAD_RIGHT, h=page_h, vx=-PAD_LEFT,
                       title=esc(TRANSLATION["hover"]["text"]),
                       url=ORIGINAL_URL, licence=LICENCE_TEXT,
                       credits=build_metadata(credit_lines))]
    if embed_font:
        p.append(build_font_face())
    p.append(build_defs(curve, figures, boxes))
    p.append(layer("background",
                   f'    <rect x="{-PAD_LEFT}" y="0" width="{IMG_W + PAD_LEFT + PAD_RIGHT}" '
                   f'height="{page_h}" fill="#FFFFFF" id="paper"/>\n',
                   "layer_background", locked=True))
    p.append(layer("temperature bands", build_bands(), "layer_bands"))
    p.append(layer("gridlines", build_gridlines(), "layer_gridlines"))
    p.append(layer("zero axis", build_zero_axis(), "layer_zero_axis"))
    if figures:
        p.append(layer("gridline erasers", build_erasers(figures),
                       "layer_erasers"))
    p.append(layer("text erasers", build_text_erasers(boxes),
                   "layer_text_erasers"))
    if curve:
        # Shadow first, underneath; its <use> refer forward to the paths.
        if CURVE_SHADOW:
            p.append(layer("curve shadow", build_curve_shadow(curve),
                           "layer_curve_shadow"))
        p.append(layer("curve", build_curve(curve), "layer_curve"))
    if figures:
        p.append(layer("illustrations", build_figures(figures, False),
                       "layer_illustrations"))
        p.append(layer("connectors", build_figures(figures, True),
                       "layer_connectors"))
    p.append(layer("frame", build_frame(), "layer_frame"))
    p.append(layer("header rules", build_header_rules(), "layer_header_rules"))
    p.append(layer("span annotation", build_span_annotation(), "layer_span"))
    p.append(layer("chart labels", build_sun_labels(), "layer_chart_labels"))
    p.append(layer("temperature labels", build_temperature_labels(),
                   "layer_temperature_labels"))
    p.append(layer("year labels", build_year_labels(), "layer_year_labels"))
    p.append(layer("text", text_layer.build_text(TRANSLATION), "layer_text",
                   style=f"display:inline;opacity:{TEXT_OPACITY:g}"))
    p.append(layer("credits", build_credits(TRANSLATION, credit_lines),
                   "layer_credits"))
    p.append("</svg>\n")
    return "".join(p)


def main(argv=None):
    global TRANSLATION, LOC, GRID_YEAR_NOW, DATA_DIR, FIGURES_HREF
    ap = argparse.ArgumentParser(
        description="Build one language edition of xkcd 1732 as SVG.")
    ap.add_argument("translation",
                    help="translation JSON; decides which edition is built")
    ap.add_argument("output", nargs="?",
                    help="output SVG (default: ../results/<translation>.svg)")
    ap.add_argument("--data", default=DATA_DIR,
                    help="folder holding curve_paths.json and figures/ "
                         "(default: ../data)")
    ap.add_argument("--embed-font", action="store_true",
                    help="inline the lettering face so the file renders "
                         "correctly without it installed (adds ~275 kB; "
                         "browsers honour it, Inkscape does not)")
    args = ap.parse_args(argv)

    DATA_DIR = os.path.abspath(args.data)
    TRANSLATION = load_translation(args.translation)
    check_keys(TRANSLATION)
    LOC = TRANSLATION["locale"]

    # Adaptation: after loading, before any coordinate is read.
    adaptation.check(TRANSLATION)
    GRID_YEAR_NOW = adaptation.year_now(TRANSLATION)
    if GRID_YEAR_NOW != adaptation.DEFAULT_YEAR_NOW:
        print(f"  adaptation: present day is {GRID_YEAR_NOW}")
    protected = {en for labels in FIGURE_LABELS.values() for en in labels}
    for note in (adaptation.apply_entries(TRANSLATION, protected),
                 adaptation.merge_offsets(TRANSLATION)):
        if note:
            print(note)

    stem = os.path.splitext(os.path.basename(args.translation))[0]
    out = args.output or os.path.join(RESULTS_DIR, stem + ".svg")
    if os.path.abspath(out) == os.path.abspath(args.translation):
        raise SystemExit("refusing to overwrite the translation file")
    out_dir = os.path.dirname(os.path.abspath(out))
    os.makedirs(out_dir, exist_ok=True)
    FIGURES_HREF = os.path.relpath(os.path.join(DATA_DIR, FIGURES_DIR),
                                   out_dir).replace(os.sep, "/")

    print(f"  translation: {os.path.basename(args.translation)}")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(build(args.embed_font))
    print(f"  {os.path.basename(out):28s} {os.path.getsize(out) / 1024:9.1f} kB")


if __name__ == "__main__":
    main()
