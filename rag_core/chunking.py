"""Chunking strategies.

``structured`` (default) follows the clause numbering of policies and charters
("5.2.1 ...", "3. ...", "(a) ...", "第十条"), keeps a clause intact, may cross
a page boundary, records the nearest heading as ``section`` and drops running
headers / footers.  ``page`` is the original page-local splitter, kept so older
indexes and the chunk-ID gold labels of ``cnooc_eval_v1`` stay reproducible.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from rag_core.textnorm import clean_display, normalize

CHUNKERS = ("structured", "page")

_SENTENCE_END = "。；;！!？?：:.」』）)"
_CLAUSE_START = re.compile(
    r"^("
    r"第[一二三四五六七八九十百零〇\d]+[章节節条條款]"
    r"|\d{1,3}(?:\.\d{1,3}){0,3}[\.、．]?(?=\s|[一-鿿（(“\"])"
    r"|[（(][a-zA-Z0-9一二三四五六七八九十ivx]{1,4}[）)]"
    r"|[一二三四五六七八九十]{1,3}、"
    r")"
)
_NUMBERED_HEADING = re.compile(r"^(第[一二三四五六七八九十百零〇\d]+[章节節]|\d{1,3}(?:\.\d{1,3}){0,2})\s*\S")
_LEADER_DOTS = re.compile(r"(\.{6,}|…{3,}|·{6,})")
_PAGE_NUMBER = re.compile(r"^[-–—\s]*(\d{1,4}|[ivxlc]{1,6})[-–—\s]*$", re.IGNORECASE)


@dataclass
class _Line:
    text: str
    page: int


@dataclass
class _Unit:
    lines: list[_Line] = field(default_factory=list)
    section: str = ""

    @property
    def text(self) -> str:
        return _join([line.text for line in self.lines])

    @property
    def size(self) -> int:
        return sum(len(line.text) for line in self.lines)


def _join(lines: list[str]) -> str:
    """Re-join PDF soft wraps: CJK continuations are glued, real breaks keep a newline."""
    out = ""
    for line in lines:
        if not out:
            out = line
        elif _CLAUSE_START.match(line) or out[-1] in _SENTENCE_END or _is_heading(out.rsplit("\n", 1)[-1], None):
            out += "\n" + line
        elif re.match(r"[A-Za-z0-9]", out[-1]) and re.match(r"[A-Za-z0-9]", line[0]):
            out += " " + line
        else:
            out += line
    return out


def _running_lines(pages: list[dict]) -> set[str]:
    """Short lines repeated on many pages are headers/footers, not content."""
    counts: Counter[str] = Counter()
    for page in pages:
        seen = {normalize(line) for line in clean_display(page.get("text", "")).splitlines() if line.strip()}
        counts.update(item for item in seen if len(item) <= 30)
    threshold = max(3, int(len(pages) * 0.4))
    return {line for line, count in counts.items() if count >= threshold} if len(pages) >= 4 else set()


def _is_heading(line: str, previous: str | None) -> bool:
    if len(line) > 24 or line[-1] in _SENTENCE_END or "，" in line or "," in line:
        return False
    if _NUMBERED_HEADING.match(line) and not re.search(r"[。；]", line):
        # "5.2 合规培训" is a heading, "5.2.1 公司应……" is a clause.
        body = _NUMBERED_HEADING.sub("", line, count=1)
        return len(line) <= 20 and not body.startswith(("公司", "员工", "員工", "本"))
    if _CLAUSE_START.match(line):
        return False
    return previous is None or previous[-1] in _SENTENCE_END or len(previous) <= 24


def _lines(pages: list[dict]) -> list[_Line]:
    running = _running_lines(pages)
    result: list[_Line] = []
    for page in pages:
        number = int(page["page_number"])
        for raw in clean_display(page.get("text", "")).splitlines():
            line = raw.strip()
            if not line or _PAGE_NUMBER.match(line) or _LEADER_DOTS.search(line) or normalize(line) in running:
                continue
            result.append(_Line(line, number))
    return result


def _units(lines: list[_Line]) -> list[_Unit]:
    units: list[_Unit] = []
    section = ""
    current: _Unit | None = None
    previous: str | None = None
    # A heading with no body before the next heading (or the end) is content,
    # e.g. a one-line note or a title page; keep it rather than dropping it.
    pending_heading: _Line | None = None
    for line in lines:
        if _is_heading(line.text, previous):
            if current is not None:
                units.append(current)
            elif pending_heading is not None:
                units.append(_Unit([pending_heading], section))
            section, pending_heading, current = line.text, line, None
        elif current is None or _CLAUSE_START.match(line.text):
            if current is not None:
                units.append(current)
            head = [pending_heading] if pending_heading is not None else []
            current, pending_heading = _Unit([*head, line], section), None
        else:
            current.lines.append(line)
        previous = line.text
    if current is not None:
        units.append(current)
    elif pending_heading is not None:
        units.append(_Unit([pending_heading], section))
    return units


def _split_long(unit: _Unit, max_chars: int) -> list[_Unit]:
    if unit.size <= max_chars:
        return [unit]
    pieces: list[_Unit] = []
    current = _Unit(section=unit.section)
    for line in unit.lines:
        for part in re.split(r"(?<=[。；;])", line.text):
            if not part:
                continue
            if current.size + len(part) > max_chars and current.lines:
                pieces.append(current)
                current = _Unit(section=unit.section)
            current.lines.append(_Line(part, line.page))
    if current.lines:
        pieces.append(current)
    return pieces


def structured_chunks(
    pages: list[dict],
    *,
    relative_path: str,
    target_chars: int = 400,
    max_chars: int = 900,
    min_chars: int = 60,
) -> list[dict]:
    units = [piece for unit in _units(_lines(pages)) for piece in _split_long(unit, max_chars)]
    groups: list[list[_Unit]] = []
    for unit in units:
        if groups:
            last = groups[-1]
            size = sum(item.size for item in last)
            new_section = unit.section != last[-1].section
            if size + unit.size <= target_chars and not (new_section and size >= min_chars):
                last.append(unit)
                continue
        groups.append([unit])
    chunks = []
    for number, group in enumerate(groups, start=1):
        lines = [line for unit in group for line in unit.lines]
        sections = list(dict.fromkeys(unit.section for unit in group if unit.section))
        page_start, page_end = lines[0].page, max(line.page for line in lines)
        chunks.append({
            "chunk_id": f"{relative_path}::p{page_start:04d}::s{number:04d}",
            "text": "\n".join(unit.text for unit in group),
            "page_start": page_start,
            "page_end": page_end,
            "section": " / ".join(sections)[:200],
        })
    return chunks


def page_chunks(pages: list[dict], *, relative_path: str, max_chars: int = 700, overlap: int = 80) -> list[dict]:
    """The original P0 splitter: page-local, line-packed, ≤700 characters."""
    chunks = []
    for page in pages:
        pieces, current, size = [], [], 0
        for line in page["text"].splitlines(keepends=True):
            if current and size + len(line) > max_chars:
                pieces.append("".join(current).strip())
                current, size = [], 0
            if len(line) > max_chars:
                if current:
                    pieces.append("".join(current).strip())
                    current, size = [], 0
                start = 0
                while start < len(line):
                    pieces.append(line[start:start + max_chars].strip())
                    if start + max_chars >= len(line):
                        break
                    start += max_chars - overlap
            else:
                current.append(line)
                size += len(line)
        if current:
            pieces.append("".join(current).strip())
        for number, text in enumerate((piece for piece in pieces if piece), start=1):
            chunks.append({
                "chunk_id": f"{relative_path}::p{page['page_number']:04d}::c{number:04d}",
                "text": text,
                "page_start": page["page_number"],
                "page_end": page["page_number"],
                "section": "",
            })
    return chunks


def chunk_pages(pages: list[dict], *, relative_path: str, strategy: str = "structured") -> list[dict]:
    if strategy not in CHUNKERS:
        raise ValueError(f"未知切分策略：{strategy}，可选 {CHUNKERS}")
    if strategy == "page":
        return page_chunks(pages, relative_path=relative_path)
    return structured_chunks(pages, relative_path=relative_path)


def search_text(record: dict) -> str:
    """Representation used for embedding, BM25 and reranking (title + section + body)."""
    title = record.get("title") or record.get("source") or ""
    section = record.get("section") or ""
    prefix = " · ".join(part for part in (title, section) if part)
    body = record.get("text", "")
    return normalize(f"{prefix}\n{body}" if prefix else body)
