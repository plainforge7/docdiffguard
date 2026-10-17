import json
import sys

from binder import bind_files

VALID_LABELS = {"same", "fuzzy", "missing"}


def main(annotation_path: str) -> int:
    with open(annotation_path, encoding="utf-8") as f:
        ann = json.load(f)
    pair = bind_files(base=ann["base"], ref=ann["ref"])
    n_base = len(pair.base_paragraphs)
    print(f"BASE 段落: {n_base}, REF 段落: {len(pair.ref_paragraphs)}")

    expected_ids = {f"P{i:03d}" for i in range(1, n_base + 1)}
    labels = ann["labels"]
    missing_ids = sorted(expected_ids - set(labels))
    extra_ids = sorted(set(labels) - expected_ids)
    bad_label = [k for k, v in labels.items() if v["label"] not in VALID_LABELS]
    prefix_mismatch = []
    for pid, v in labels.items():
        idx = int(pid[1:]) - 1
        if 0 <= idx < n_base and not pair.base_paragraphs[idx].startswith(v["prefix"]):
            prefix_mismatch.append(pid)

    problems = {
        "未标注的段落": missing_ids,
        "标注了不存在的段落": extra_ids,
        "标签值非法": bad_label,
        "前缀与段落不匹配": prefix_mismatch,
    }
    ok = True
    for name, items in problems.items():
        if items:
            ok = False
            print(f"[问题] {name}: {items}")
    print("标注检查通过" if ok else "标注检查未通过，请修正后重跑")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))