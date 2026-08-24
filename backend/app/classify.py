"""Route a question before retrieval runs.

A question mis-routed as "single fact" when it's actually comparative can
silently return a partial answer with high apparent confidence -- picking
one document's chunk and ignoring that the real answer differs across
products. Comparative questions get diverse, multi-document retrieval
instead of a single top-k pass.
"""

import re

_COMPARATIVE_MARKERS = [
    r"\bdiff[ée]rence\b",
    r"\bcompar",
    r"\bpar rapport\b",
    r"\bversus\b",
    r"\bvs\b",
    r"\bplut[oô]t que\b",
    r"\bentre .+ et .+\b",
    r"\bou\b.*\?",  # "X ou Y ?" style either/or questions
]

_COMPARATIVE_RE = re.compile("|".join(_COMPARATIVE_MARKERS), re.IGNORECASE)


def is_comparative(question: str) -> bool:
    return bool(_COMPARATIVE_RE.search(question))
