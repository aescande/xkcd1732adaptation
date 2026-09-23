"""
Apply a translation file's optional `adaptation` block: a revision of
Munroe's 2016 strip declared as a diff, rather than by editing `entries`.

    "adaptation": {
      "currentYear": 2026,
      "entriesRemoved": ["CURRENT PATH", "OPTIMISTIC SCENARIO"],
      "entriesAdded": [ {full entry objects, with text} ],
      "figuresRemoved": ["sub29"],
      "figuresShifted": {"sub30": [40, 12]},
      "figuresAdded": [ {"file": "arrow_ssp370.png", "x": .., "y": ..,
                         "width": .., "height": .., "connector": true} ]
    }

Inert when absent. Entries are named by `en`; a repeated name removes by
occurrence; the opening words suffice if they end on a word boundary and match
one entry only; an exact `en` wins; an ambiguous prefix is an error. Removals
before additions. `figuresShifted` is summed into `figureOffsets`, so
`shift_figures` moves figures and their labels in one place. Applied right
after loading, before any box is computed.
"""
import os
import re

DEFAULT_YEAR_NOW = 2016
NAME_OK = re.compile(r"^[A-Za-z0-9_-]+$")

KNOWN_KEYS = {"currentYear", "entriesRemoved", "entriesAdded",
              "figuresRemoved", "figuresShifted", "figuresAdded"}
# Fields build_figures and the eraser defs require of any added image.
FIGURE_FIELDS = ("file", "x", "y", "width", "height")


def block(doc):
    return (doc or {}).get("adaptation") or {}


def _die(msg):
    raise SystemExit(f"adaptation: {msg}")


def stem(f):
    return f["file"].rsplit(".", 1)[0]


def _summary(bits):
    return "  adaptation: " + ", ".join(bits) if bits else ""


def year_now(doc):
    """The emphasised gridline and its year label. 2016 unless overridden."""
    yr = block(doc).get("currentYear", DEFAULT_YEAR_NOW)
    if isinstance(yr, bool) or not isinstance(yr, int):
        _die(f"currentYear must be a whole year, got {yr!r}")
    return yr


def check(doc):
    """Reject an adaptation that cannot mean what it says, before any work."""
    a = block(doc)
    if not a:
        return
    unknown = set(a) - KNOWN_KEYS
    if unknown:
        _die(f"unknown key(s) {sorted(unknown)}; expected {sorted(KNOWN_KEYS)}")
    for key in ("entriesRemoved", "entriesAdded", "figuresRemoved",
                "figuresAdded"):
        if key in a and not isinstance(a[key], list):
            _die(f"{key} must be a list")
    if "figuresShifted" in a and not isinstance(a["figuresShifted"], dict):
        _die("figuresShifted must be an object of name -> [dx, dy]")


def resolve_en(name, entries):
    """A full `en`, from either the whole string or its opening words."""
    present = [e.get("en") for e in entries if e.get("en")]
    if name in present:
        return name
    hits = sorted({en for en in present if en.startswith(name + " ")})
    if len(hits) == 1:
        return hits[0]
    if not hits:
        _die(f"entriesRemoved names {name!r}, which is not an entry's `en` nor "
             f"the opening words of one")
    _die(f"entriesRemoved names {name!r}, which is ambiguous -- it opens "
         + " and ".join(repr(h) for h in hits))


def apply_entries(doc, protected_en=()):
    """Remove and add text entries. Returns a one-line summary, or ''."""
    a = block(doc)
    if not a:
        return ""
    entries = doc["entries"]

    wanted = {}
    for name in a.get("entriesRemoved", []):
        en = resolve_en(name, entries)
        wanted[en] = wanted.get(en, 0) + 1
    for en, count in wanted.items():
        if en in protected_en:
            _die(f"entriesRemoved names {en!r}, which FIGURE_LABELS binds to a "
                 f"drawing. Remove the figure too, or rebind it, but do not "
                 f"leave a caption pointing at nothing.")
        hits = [i for i, e in enumerate(entries) if e.get("en") == en]
        if len(hits) < count:
            _die(f"entriesRemoved wants {count} x {en!r} but the file has "
                 f"{len(hits)}")
        for i in reversed(hits[:count]):
            del entries[i]
    removed = sum(wanted.values())

    added = a.get("entriesAdded", [])
    for e in added:
        for field in ("en", "text", "type", "align", "at"):
            if field not in e:
                _die(f"entriesAdded item missing {field!r}: {e}")
    entries.extend(added)

    bits = []
    if removed:
        bits.append(f"removed {removed} entr{'y' if removed == 1 else 'ies'}")
    if added:
        bits.append(f"added {len(added)}")
    return _summary(bits)


def merge_offsets(doc):
    """Fold figuresShifted into figureOffsets so shift_figures applies both."""
    shifted = block(doc).get("figuresShifted") or {}
    if not shifted:
        return ""
    offsets = doc.get("figureOffsets") or {}
    doc["figureOffsets"] = offsets
    both = []
    for name, delta in shifted.items():
        if not (isinstance(delta, (list, tuple)) and len(delta) == 2):
            _die(f"figuresShifted[{name!r}] must be [dx, dy], got {delta!r}")
        if name in offsets:
            both.append(name)
            offsets[name] = [offsets[name][0] + delta[0],
                             offsets[name][1] + delta[1]]
        else:
            offsets[name] = list(delta)
    note = f"  adaptation: shifted {len(shifted)} figure(s)"
    if both:
        note += f"; {', '.join(both)} also carry a translation offset (summed)"
    return note


def apply_figures(doc, figures, figures_dir=None):
    """Remove and add images, in place. Returns a summary line, or ''."""
    a = block(doc)
    if not a or figures is None:
        return ""
    known = {stem(f) for f in figures}

    drop = set(a.get("figuresRemoved", []))
    for name in a.get("figuresRemoved", []):
        if name not in known:
            _die(f"figuresRemoved names {name!r}, which is not in the manifest")
    if drop:
        figures[:] = [f for f in figures if stem(f) not in drop]

    add = a.get("figuresAdded", [])
    for f in add:
        missing = [k for k in FIGURE_FIELDS if k not in f]
        if missing:
            _die(f"figuresAdded item missing {missing}: {f}")
        name = stem(f)
        if not NAME_OK.match(name):
            _die(f"figuresAdded file {f['file']!r}: the stem becomes an XML id, "
                 f"so it must match {NAME_OK.pattern}")
        if name in known:
            _die(f"figuresAdded {f['file']!r} collides with an existing figure")
        known.add(name)
        if figures_dir:
            path = os.path.join(figures_dir, f["file"])
            if not os.path.exists(path):
                print(f"  !! adaptation: {f['file']} is not in {figures_dir}; "
                      f"the SVG will reference a missing image")
    figures.extend(add)

    bits = []
    n_drop = len(a.get("figuresRemoved", []))
    if n_drop:
        bits.append(f"removed {n_drop} image(s)")
    if add:
        bits.append(f"added {len(add)}")
    return _summary(bits)


def is_connector(f, connector_ids):
    """Which artwork layer an image goes in. An added image may set
    `connector`; `subNN` images are classified by number."""
    if "connector" in f:
        return bool(f["connector"])
    name = stem(f)
    if name.startswith("sub") and name[3:].isdigit():
        return int(name[3:]) in connector_ids
    return False
