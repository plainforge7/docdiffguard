from types import SimpleNamespace

from aligner import build_results
from eval import load_cases
from judge import judge_with_fallback

TARGET = {"fuzzy": "modified", "same": "same"}

if __name__ == "__main__":
    cases = load_cases("eval_cases.json")
    stats = {label: {"total": 0, "agree": 0, "fallback": 0} for label in TARGET}
    for case in cases:
        pair = SimpleNamespace(
            base_path=case["id"],
            base_paragraphs=case["base"],
            ref_paragraphs=case["ref"],
        )
        results = {r.base_id: r for r in build_results(pair)}
        for pid, expected in case["expected"].items():
            if expected not in TARGET:
                continue
            r = results[pid]
            verdict = judge_with_fallback(r.base_text, r.ref_text)
            is_fallback = "降级" in verdict.reason
            matched = verdict.verdict == TARGET[expected]
            s = stats[expected]
            s["total"] += 1
            s["fallback"] += is_fallback
            s["agree"] += matched and not is_fallback
            status = "与期望一致" if matched else "与期望不一致"
            detail = verdict.reason if is_fallback else verdict.reason[:40]
            print(case["id"], pid, expected, verdict.verdict, status, "（降级）" if is_fallback else "", detail)
    for label, s in stats.items():
        print(f"{label}：总数 {s['total']}，与期望一致 {s['agree']}，降级 {s['fallback']}")