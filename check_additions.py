import re
import sys
import argparse

from reader import read_any
from aligner import normalize

SENTENCE_END = r"(?<=[。！？；\n])"
MIN_LEN = 4


def split_sentences(paragraphs: list[str]) -> list[str]:
    sentences = []
    for para in paragraphs:
        for s in re.split(SENTENCE_END, para):
            if len(normalize(s)) >= MIN_LEN:
                sentences.append(s.strip())
    return sentences


def find_unsourced(target: str, sources: list[str]) -> list[str]:
    source_text = normalize("".join("".join(read_any(p)) for p in sources))
    flagged = []
    for s in split_sentences(read_any(target)):
        if normalize(s) not in source_text:
            flagged.append(s)
    return flagged


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="列出目标文档中在所有来源里都找不到原文的句子")
    parser.add_argument("--target", required=True, help="要检查的文档，例如 B2")
    parser.add_argument("--source", action="append", required=True, help="允许作为原文的来源，可重复")
    args = parser.parse_args()
    flagged = find_unsourced(args.target, args.source)
    if not flagged:
        print("未发现来源之外的句子")
        sys.exit(0)
    print(f"共 {len(flagged)} 句在所有来源中找不到原文，请人工确认：")
    for s in flagged:
        print("-", s)
    sys.exit(1)
