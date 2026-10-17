import argparse
from dataclasses import dataclass
from pathlib import Path

from reader import read_any


@dataclass
class DocPair:
    base_path: str
    ref_path: str
    base_paragraphs: list[str]
    ref_paragraphs: list[str]


def bind_files(base: str, ref: str) -> DocPair:
    if not Path(base).exists():
        raise FileNotFoundError(f"BASE 文件不存在: {base}")
    if not Path(ref).exists():
        raise FileNotFoundError(f"REF 文件不存在: {ref}")
    if Path(base).resolve() == Path(ref).resolve():
        raise ValueError("BASE 和 REF 不能是同一个文件")
    base_paragraphs = read_any(base)
    ref_paragraphs = read_any(ref)
    if not base_paragraphs:
        raise ValueError(f"BASE 文件没有可读内容: {base}")
    if not ref_paragraphs:
        raise ValueError(f"REF 文件没有可读内容: {ref}")
    return DocPair(
        base_path=base,
        ref_path=ref,
        base_paragraphs=base_paragraphs,
        ref_paragraphs=ref_paragraphs,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--ref", required=True)
    args = parser.parse_args()
    pair = bind_files(base=args.base, ref=args.ref)
    print(f"BASE: {pair.base_path}，共 {len(pair.base_paragraphs)} 段")
    print(f"REF: {pair.ref_path}，共 {len(pair.ref_paragraphs)} 段")
