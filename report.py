import json
import sys

from models import AlignmentResult


def load_results(path: str) -> list[AlignmentResult]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [AlignmentResult.model_validate(item) for item in data]


def make_report(results: list[AlignmentResult]) -> str:
    missing = [r for r in results if r.diff_type == "missing"]
    modified = [r for r in results if r.diff_type == "fuzzy"]
    lines = ["# 转录版需要修改的点", ""]
    lines.append(f"## 一、缺失内容（missing）：{len(missing)} 条")
    for r in missing:
        lines.append(f"- {r.base_id}：{r.base_text}")
    lines.append("")
    lines.append(f"## 二、需要修改（modified）：{len(modified)} 条")
    for r in modified:
        lines.append(f"- {r.base_id} 对应 {r.ref_id}")
        lines.append(f"  - BASE：{r.base_text}")
        lines.append(f"  - REF：{r.ref_text}")
    return "\n".join(lines)


if __name__ == "__main__":
    results = load_results(sys.argv[1])
    print(make_report(results))