import sys
from pathlib import Path

from docx import Document


def read_paragraphs(path: str) -> list[str]:
    text = Path(path).read_text(encoding="utf-8")
    raw_parts = text.split("\n\n")
    paragraphs = []
    for part in raw_parts:
        cleaned = part.strip()
        if cleaned:
            paragraphs.append(cleaned)
    return paragraphs


def read_docx_paragraphs(path: str) -> list[str]:
    doc = Document(path)
    paragraphs = []
    for p in doc.paragraphs:
        cleaned = p.text.strip()
        if cleaned:
            paragraphs.append(cleaned)
    return paragraphs


def read_any(path: str) -> list[str]:
    suffix = Path(path).suffix.lower()
    if suffix == ".txt":
        return read_paragraphs(path)
    if suffix == ".docx":
        return read_docx_paragraphs(path)
    raise ValueError(f"不支持的文件类型: {suffix}")


def make_ids(paragraphs: list[str]) -> list[tuple[str, str]]:
    result = []
    for i, para in enumerate(paragraphs, start=1):
        result.append((f"P{i:03d}", para))
    return result


if __name__ == "__main__":
    path = sys.argv[1]
    paragraphs = read_any(path)
    for pid, text in make_ids(paragraphs):
        print(pid, text)
