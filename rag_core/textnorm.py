"""Text normalisation used for embedding, BM25 and reranking.

The CNOOC governance charters are published in Traditional Chinese while users
(and the evaluation set) ask in Simplified Chinese. pypdf also inserts stray
spaces between CJK characters. Both break lexical matching, so every search
representation goes through :func:`normalize`. The original text is kept for
display and citation.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from rag_core._t2s_table import SIMPLIFIED, TRADITIONAL

_CJK = r"㐀-鿿豈-﫿"
_CJK_PUNCT = r"　-〿＀-￯"
_SPACE_BETWEEN_CJK = re.compile(rf"(?<=[{_CJK}{_CJK_PUNCT}])[ \t ]+(?=[{_CJK}{_CJK_PUNCT}])")
_SPACES = re.compile(r"[ \t ]+")
_FALLBACK = str.maketrans(TRADITIONAL, SIMPLIFIED)


@lru_cache(maxsize=1)
def _opencc():
    try:  # pragma: no cover - depends on optional dependency
        import opencc

        return opencc.OpenCC("t2s")
    except Exception:
        return None


def to_simplified(text: str) -> str:
    converter = _opencc()
    if converter is not None:  # pragma: no cover - optional dependency
        return converter.convert(text)
    return text.translate(_FALLBACK)


def t2s_backend() -> str:
    return "opencc" if _opencc() is not None else "builtin-table"


def clean_display(text: str) -> str:
    """Repair extraction artefacts but keep the original script for display."""
    lines = []
    for line in text.splitlines():
        line = _SPACE_BETWEEN_CJK.sub("", line)
        line = _SPACES.sub(" ", line).strip()
        lines.append(line)
    return "\n".join(lines).strip()


def normalize(text: str) -> str:
    """Search representation: NFKC, CJK spacing repaired, Simplified Chinese, lower-case."""
    return to_simplified(unicodedata.normalize("NFKC", clean_display(text))).lower()


def compact(text: str) -> str:
    """Whitespace-free form used for evidence-quote matching in evaluation."""
    return re.sub(r"\s+", "", normalize(text))
