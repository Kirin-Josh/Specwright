"""Stage 1 — turn an uploaded .docx/.pdf into markdown sections. (M1)"""

from pathlib import Path

from app.schemas import SpecDocument, SpecSection


def ingest(path: Path) -> SpecDocument:
    from docling.document_converter import DocumentConverter

    markdown = DocumentConverter().convert(str(path)).document.export_to_markdown()
    return SpecDocument(title=path.stem, sections=split_sections(markdown))


def split_sections(markdown: str) -> list[SpecSection]:
    sections: list[SpecSection] = []
    heading, lines = "Preamble", []
    for line in markdown.splitlines():
        if line.startswith("#"):
            if lines:
                sections.append(SpecSection(heading=heading, markdown="\n".join(lines).strip()))
            heading, lines = line.lstrip("# ").strip(), []
        else:
            lines.append(line)
    if lines:
        sections.append(SpecSection(heading=heading, markdown="\n".join(lines).strip()))
    return [s for s in sections if s.markdown]


def chunk_sections(doc: SpecDocument, max_chars: int) -> list[SpecDocument]:
    """Group whole sections into documents of at most ~max_chars; 0 keeps one document."""
    if max_chars <= 0:
        return [doc]
    chunks: list[SpecDocument] = []
    current: list[SpecSection] = []
    size = 0
    for s in doc.sections:
        n = len(s.heading) + len(s.markdown)
        if current and size + n > max_chars:
            chunks.append(doc.model_copy(update={"sections": current}))
            current, size = [], 0
        current.append(s)
        size += n
    if current:
        chunks.append(doc.model_copy(update={"sections": current}))
    return chunks


def to_prompt_text(doc: SpecDocument) -> str:
    body = "\n\n".join(f"## {s.heading}\n{s.markdown}" for s in doc.sections)
    return f"<spec title=\"{doc.title}\">\n{body}\n</spec>"
