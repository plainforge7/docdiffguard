import sys
import difflib
import argparse

from reader import read_any
from aligner import normalize


def removed_fragments(older: str, newer: str, min_len: int) -> list[str]:
    """older 中有、newer 中被删除或替换掉的片段（规范化后）。"""
    a = normalize(''.join(read_any(older)))
    b = normalize(''.join(read_any(newer)))
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    fragments = []
    for tag, i1, i2, _, _ in sm.get_opcodes():
        if tag in ('delete', 'replace') and i2 - i1 >= min_len:
            fragments.append(a[i1:i2])
    return fragments


def find_resurrected(older: str, newer: str, target: str, min_len: int) -> list[str]:
    target_text = normalize(''.join(read_any(target)))
    return [f for f in removed_fragments(older, newer, min_len) if f in target_text]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="检查目标稿中是否重新出现了前后版本之间被有意删除的内容")
    parser.add_argument("--older", required=True, help="更早的版本，例如 B0")
    parser.add_argument("--newer", required=True, help="删除发生后的版本，例如 B1")
    parser.add_argument("--target", required=True, help="要检查的目标稿，例如 B2")
    parser.add_argument("--min-len", type=int, default=4, help="忽略短于此长度的片段，默认 4")
    args = parser.parse_args()
    hits = find_resurrected(args.older, args.newer, args.target, args.min_len)
    if not hits:
        print("未发现已删除内容重新出现")
        sys.exit(0)
    print(f"共 {len(hits)} 个已删除片段重新出现在目标稿中：")
    for h in hits:
        print("-", h)
    sys.exit(1)
