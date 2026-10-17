import argparse
import argparse
import json

import anthropic
from pydantic import ValidationError

from aligner import build_results, content_changed
from binder import bind_files
from models import JudgeVerdict


def rule_judge(base_text: str, ref_text: str) -> JudgeVerdict:
    if content_changed(base_text, ref_text):
        return JudgeVerdict(verdict="modified", reason="规则：存在实质性增删", evidence=base_text)
    return JudgeVerdict(verdict="same", reason="规则：只有标点或空白差异", evidence=base_text)


PROMPT = """你是文档比对助手。给你两段文字：BASE（润色版，基准）和 REF（转录版）。
只判断 BASE 中的内容相对 REF 是否有实质性差异。
规则：
1. 只输出一个 JSON 对象，不要输出任何其他文字。
2. JSON 字段：verdict（只能是 same、modified、unsure 之一）、reason（一句中文理由）、evidence（从 BASE 原文中逐字复制的一句话，必须能在 BASE 中找到）。
3. 不确定时输出 unsure，不要猜测。

BASE：{base}
REF：{ref}"""


def llm_judge(base_text: str, ref_text: str) -> JudgeVerdict:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-haiku-5-5",
        max_tokens=4096,
        messages=[{"role": "user", "content": PROMPT.format(base=base_text, ref=ref_text)}],
    )
    text = next((block.text for block in response.content if block.type == "text"), "")
    if "{" not in text:
        raise ValueError(f"模型没有返回 JSON（停止原因：{response.stop_reason}），原文开头：{text[:80]}")
    start, end = text.index("{"), text.rindex("}") + 1
    data = json.loads(text[start:end])
    return JudgeVerdict.model_validate(data)


def judge_with_fallback(base_text: str, ref_text: str) -> JudgeVerdict:
    try:
        return llm_judge(base_text, ref_text)
    except (anthropic.APIError, ValueError, ValidationError) as e:
        verdict = rule_judge(base_text, ref_text)
        verdict.reason = f"LLM 失败，已降级为规则（{type(e).__name__}：{e}）：{verdict.reason}"
        return verdict


def judge_fuzzy(results, pair) -> list[tuple[str, JudgeVerdict, bool]]:
    rows = []
    for r in results:
        if r.diff_type != "fuzzy":
            continue
        verdict = judge_with_fallback(r.base_text, r.ref_text)
        evidence_ok = verdict.evidence in pair.base_paragraphs
        rows.append((r.base_id, verdict, evidence_ok))
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--ref", required=True)
    args = parser.parse_args()
    pair = bind_files(base=args.base, ref=args.ref)
    results = build_results(pair)
    for base_id, verdict, evidence_ok in judge_fuzzy(results, pair):
        print(base_id, verdict.verdict, "证据有效" if evidence_ok else "证据无效", verdict.reason)


