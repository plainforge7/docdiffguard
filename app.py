import json
import tempfile
from pathlib import Path

import streamlit as st

from aligner import build_results, validate_results
from binder import bind_files
from report import make_report

st.title("DocDiffGuard")
st.write("阶段 8：上传 BASE（润色版）和 REF（转录版）。")

base_file = st.file_uploader("BASE（润色版）", type=["txt", "docx"], key="base")
ref_file = st.file_uploader("REF（转录版）", type=["txt", "docx"], key="ref")


def save_temp(uploaded) -> str:
    suffix = Path(uploaded.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getvalue())
        return tmp.name


if base_file and ref_file:
    try:
        pair = bind_files(base=save_temp(base_file), ref=save_temp(ref_file))
    except (ValueError, FileNotFoundError) as e:
        st.error(str(e))
    else:
        st.success(f"BASE：{base_file.name}，共 {len(pair.base_paragraphs)} 段")
        st.success(f"REF：{ref_file.name}，共 {len(pair.ref_paragraphs)} 段")

        results = build_results(pair)
        kept, dropped = validate_results(results, pair)
        for r in dropped:
            st.warning(f"丢弃 {r.base_id}：引用无法在原文中找到")

        rows = [
            {
                "base_id": r.base_id,
                "ref_id": r.ref_id,
                "diff_type": r.diff_type,
                "action": r.action,
                "confidence": round(r.confidence, 3),
                "base_text": r.base_text,
                "ref_text": r.ref_text,
            }
            for r in kept
        ]
        st.subheader("对齐结果")
        st.dataframe(rows)

        json_rows = [{**r.model_dump(), "source": base_file.name} for r in kept]
        json_text = json.dumps(json_rows, ensure_ascii=False, indent=2)
        report_text = make_report(kept)

        col1, col2 = st.columns(2)
        with col1:
            st.download_button("下载 JSON", data=json_text, file_name="result.json", mime="application/json")
        with col2:
            st.download_button("下载报告", data=report_text, file_name="report.md", mime="text/markdown")

        st.subheader("修改清单")
        st.markdown(report_text)