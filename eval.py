import json
from types import SimpleNamespace

from aligner import build_results, validate_results
from models import AlignmentResult
from pydantic import ValidationError

def load_cases(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run_case(case: dict) -> dict:
    pair = SimpleNamespace(
        base_path=case["id"],
        base_paragraphs=case["base"],
        ref_paragraphs=case["ref"],
    )
    results = build_results(pair)
    actual = {r.base_id: r.diff_type for r in results}
    actual_refs = {r.base_id: r.ref_id for r in results}
    expected = case["expected"]
    failures = [pid for pid in expected if actual.get(pid) != expected[pid]]
    return {"id": case["id"], "passed": not failures, "actual": actual, "actual_refs": actual_refs}


def count_metrics(cases: list[dict]) -> dict:
    tp = fp = fn = tn = 0
    for case in cases:
        result = run_case(case)
        for pid, expected_label in case["expected"].items():
            actual_label = result["actual"].get(pid)
            expected_pos = expected_label != "same"
            actual_pos = actual_label != "same"
            if expected_pos and actual_pos:
                tp += 1
            elif not expected_pos and actual_pos:
                fp += 1
            elif expected_pos and not actual_pos:
                fn += 1
            else:
                tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"TP": tp, "FP": fp, "FN": fn, "TN": tn,
            "precision": precision, "recall": recall, "f1": f1}


def count_order(cases: list[dict]) -> dict:
    total = correct = 0
    for case in cases:
        result = run_case(case)
        for pid, expected_ref in case.get("refs", {}).items():
            total += 1
            if result["actual_refs"].get(pid) == expected_ref:
                correct += 1
    accuracy = correct / total if total else 0.0
    return {"checked": total, "correct": correct, "order_accuracy": accuracy}


def count_guards(cases: list[dict]) -> dict:
    total = valid = format_ok = role_confused = 0
    for case in cases:
        pair = SimpleNamespace(
            base_path=case["id"],
            base_paragraphs=case["base"],
            ref_paragraphs=case["ref"],
        )
        results = build_results(pair)
        kept, _ = validate_results(results, pair)
        total += len(results)
        valid += len(kept)
        for r in results:
            if r.base_text not in pair.base_paragraphs and r.base_text in pair.ref_paragraphs:
                role_confused += 1
            try:
                AlignmentResult.model_validate(r.model_dump())
                format_ok += 1
            except ValidationError:
                pass
    if total == 0:
        return {"total": 0}
    return {
        "total": total,
        "citation_accuracy": valid / total,
        "hallucination_rate": (total - valid) / total,
        "format_rate": format_ok / total,
        "role_confusion_rate": role_confused / total,
    }


if __name__ == "__main__":
    cases = load_cases("eval_cases.json")
    for case in cases:
        result = run_case(case)
        status = "PASS" if result["passed"] else "FAIL"
        print(status, result["id"], result["actual"])
    metrics = count_metrics(cases)
    print("---")
    for name, value in metrics.items():
        print(f"{name}: {value:.3f}" if isinstance(value, float) else f"{name}: {value}")
    order = count_order(cases)
    for name, value in order.items():
        print(f"{name}: {value:.3f}" if isinstance(value, float) else f"{name}: {value}")
        guards = count_guards(cases)
    for name, value in guards.items():
        print(f"{name}: {value:.3f}" if isinstance(value, float) else f"{name}: {value}")