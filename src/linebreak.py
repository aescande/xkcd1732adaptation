"""
Split a string into exactly N lines at word boundaries, minimising raggedness
(dynamic programming). Language-specific rules come from a parameter dict.
`measure` is any callable str -> width.

    breaker = LineBreaker(measure, params)
    lines   = breaker.split(text, nlines=3)
"""

import re


DEFAULT_PARAMS = {
    # ---- protection (language-neutral mechanism) --------------------------
    "nbsp": " ",   # U+00A0: a space that is never a break
    "protected": [],         # regexes; blanket rules, applied on top of nbsp

    # ---- punctuation binding (language-specific) -------------------------
    "glue_before": "",       # chars that attach to the PRECEDING token
    "glue_after":  "",       # chars that attach to the FOLLOWING token

    # ---- aesthetic penalties (tuning, not language) ----------------------
    "short_word_max": 2,     # a token this short shouldn't end a line
    "short_word_penalty": 0.25,   # ... at this cost (relative to target²)
    "comma_bonus": 0.10,     # reward breaking after a comma
    "break_chars": ",",      # what counts as a comma for the bonus above
}


class Unsplittable(Exception):
    """Raised when the requested line count cannot be produced."""


class LineBreaker:
    def __init__(self, measure, params=None):
        self.measure = measure
        p = dict(DEFAULT_PARAMS)
        p.update(params or {})
        self.p = p

    # -- tokenisation ------------------------------------------------------

    def tokenize(self, text):
        """Split into atoms. Whitespace separates; everything else binds."""
        p = self.p
        nbsp = p["nbsp"]

        # blanket regex protection -> convert their inner spaces to nbsp
        for pat in p["protected"]:
            text = re.sub(pat, lambda m: m.group(0).replace(" ", nbsp), text)

        toks = [t for t in re.split(r"[ \t\n]+", text) if t]

        # bind punctuation that leans on a neighbour
        out = []
        pending_prefix = None
        for t in toks:
            if pending_prefix is not None:
                t = pending_prefix + " " + t
                pending_prefix = None
            if p["glue_after"] and t[-1] in p["glue_after"]:
                # token is (or ends with) an opening mark: it leans right
                pending_prefix = t
                continue
            if p["glue_before"] and t[0] in p["glue_before"] and out:
                # token starting with a leaning mark, e.g. "!", "»,"
                out[-1] += " " + t
                continue
            out.append(t)
        if pending_prefix is not None:
            out.append(pending_prefix)
        return out

    def render(self, s):
        """Turn markup back into what actually gets drawn."""
        return s.replace(self.p["nbsp"], " ")

    def width(self, s):
        return self.measure(self.render(s))

    # -- the dynamic program ----------------------------------------------

    def split(self, text, nlines=1):
        if nlines <= 1:
            return [self.render(text)]

        t = self.tokenize(text)
        m = len(t)
        if nlines > m:
            raise Unsplittable(
                f"{nlines} lines requested but only {m} breakable tokens")

        def line(i, j):                      # tokens i..j-1 as one string
            return " ".join(t[i:j])

        target = self.width(line(0, m)) / nlines
        t2 = target * target
        p = self.p

        def cost(i, j):
            w = self.width(line(i, j))
            c = (w - target) ** 2
            last = t[j - 1]
            bare = re.sub(r"[^\w]", "", last)
            if len(bare) <= p["short_word_max"]:
                c += t2 * p["short_word_penalty"]
            if last[-1] in p["break_chars"]:
                c -= t2 * p["comma_bonus"]
            return c

        INF = float("inf")
        dp = [[INF] * (m + 1) for _ in range(nlines + 1)]
        bk = [[0] * (m + 1) for _ in range(nlines + 1)]
        dp[0][0] = 0.0
        for k in range(1, nlines + 1):
            for j in range(k, m + 1):
                best, arg = INF, k - 1
                for i in range(k - 1, j):
                    c = dp[k - 1][i] + cost(i, j)
                    if c < best:
                        best, arg = c, i
                dp[k][j], bk[k][j] = best, arg

        lines, j = [], m
        for k in range(nlines, 0, -1):
            i = bk[k][j]
            lines.append(line(i, j))
            j = i
        lines.reverse()
        return [self.render(l) for l in lines]
