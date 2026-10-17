import re
import json
import argparse
from difflib import SequenceMatcher

from binder import bind_files

from models import AlignmentResult

ACTIONS = {"same": "keep", "fuzzy": "review", "missing": "add"}

def normalize(text: str) -> str:
    return re.sub(r"[\W_]", "", text)

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()

def build_results(pair) -> list[AlignmentResult]:
    results = []
    for i, base_para in enumerate(pair.base_paragraphs, start=1):
        scores = [similarity(base_para, ref_para) for ref_para in pair.ref_paragraphs]
        best_score = max(scores)
        best_j = scores.index(best_score)
        label = classify(best_score, base_para, pair.ref_paragraphs[best_j])
        matched = label != "missing"
        results.append(AlignmentResult(
            base_id=f"P{i:03d}",
            base_text=base_para,
            ref_id=f"R{best_j + 1:03d}" if matched else None,
            ref_text=pair.ref_paragraphs[best_j] if matched else None,
            diff_type=label,
            action=ACTIONS[label],
            reason=f"相似度 {best_score:.3f}",
            confidence=best_score,
            source=pair.base_path,
        ))
    return results

def content_changed(a: str, b: str) -> bool:
    matcher = SequenceMatcher(None, a, b)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        changed = a[i1:i2] + b[j1:j2]
        if re.sub(r"[\W_]", "", changed):
            return True
    return False

def classify(score: float, base: str, ref: str) -> str:
    if score > 0.92 and not content_changed(base, ref):
        return "same"
    if score >= 0.75:
        return "fuzzy"
    return "missing"

def validate_results(results, pair):
    kept = []
    dropped = []
    for r in results:
        base_ok = r.base_text in pair.base_paragraphs
        ref_ok = r.ref_text is None or r.ref_text in pair.ref_paragraphs
        if base_ok and ref_ok:
            kept.append(r)
        else:
            dropped.append(r)
    return kept, dropped

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--ref", required=True)
    args = parser.parse_args()
    pair = bind_files(base=args.base, ref=args.ref)
    results = build_results(pair)
    kept, dropped = validate_results(results, pair)
    for r in dropped:
        print(f"丢弃 {r.base_id}：引用无法在原文中找到", file=sys.stderr)
    print(json.dumps([r.model_dump() for r in kept], ensure_ascii=False, indent=2))