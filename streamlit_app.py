#!/usr/bin/env python3
"""Streamlit 可视化版：US FBA 费用计算与 CSV 编辑器。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from us_fba_calculator import CORE_FIELDS, OUTPUT_LABELS_ZH, enrich_row

st.set_page_config(page_title="US FBA 成本工具", layout="wide")
st.title("US FBA 成本工具（Streamlit 可视化版）")
st.caption("支持：选择当前目录CSV、查看/编辑、新增行、实时计算、覆盖保存、导出新文件")

BASE_DIR = Path.cwd()
ALL_COLUMNS = CORE_FIELDS + OUTPUT_LABELS_ZH


def normalize_input_df(df: pd.DataFrame) -> pd.DataFrame:
    for col in CORE_FIELDS:
        if col not in df.columns:
            df[col] = ""
    return df[CORE_FIELDS].fillna("").copy()


def recalc_from_inputs(input_df: pd.DataFrame) -> pd.DataFrame:
    rows = [enrich_row(r) for r in input_df.to_dict(orient="records")]
    return pd.DataFrame(rows, columns=ALL_COLUMNS)


def load_csv_as_input(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=CORE_FIELDS)
    raw = pd.read_csv(path, encoding="utf-8-sig")
    return normalize_input_df(raw)


def current_result_df() -> pd.DataFrame:
    return recalc_from_inputs(st.session_state.input_df)


def save_current_to(path: Path) -> None:
    current_result_df().to_csv(path, index=False, encoding="utf-8-sig")


if "loaded_file" not in st.session_state:
    st.session_state.loaded_file = ""
if "input_df" not in st.session_state:
    st.session_state.input_df = pd.DataFrame(columns=CORE_FIELDS)

csv_files = sorted([p.name for p in BASE_DIR.glob("*.csv")])
if not csv_files:
    st.warning("当前目录没有 CSV 文件。请先放一个 CSV（例如 us_fba_template.csv）。")

selected = st.selectbox("选择当前目录CSV文件", options=csv_files, index=0 if csv_files else None)

c1, c2 = st.columns([1, 1])
with c1:
    if st.button("打开选中文件", use_container_width=True, disabled=not bool(selected)):
        st.session_state.input_df = load_csv_as_input(BASE_DIR / selected)
        st.session_state.loaded_file = selected
with c2:
    if st.button("重置为空表", use_container_width=True):
        st.session_state.input_df = pd.DataFrame(columns=CORE_FIELDS)
        st.session_state.loaded_file = ""

if st.session_state.loaded_file:
    st.success(f"已加载：{st.session_state.loaded_file}，共 {len(st.session_state.input_df)} 行")

st.subheader("输入表（可编辑）")
st.write("在这里改 SKU/尺寸/重量/成本等输入字段；结果会在下方自动更新。")

edited_inputs = st.data_editor(
    st.session_state.input_df,
    use_container_width=True,
    num_rows="dynamic",
    hide_index=True,
    key="input_editor",
)

# 关键修复：仅维护输入表状态，不把结果列回写到编辑器，避免“首输消失/滞后一拍”
st.session_state.input_df = normalize_input_df(edited_inputs)
result_df = current_result_df()

b1, b2, b3 = st.columns([1, 1, 1])
with b1:
    if st.button("新增空白行", use_container_width=True):
        new_row = {col: "" for col in CORE_FIELDS}
        new_row["SKU"] = f"SKU-{len(st.session_state.input_df) + 1:03d}"
        st.session_state.input_df = pd.concat([st.session_state.input_df, pd.DataFrame([new_row])], ignore_index=True)
        st.rerun()
with b2:
    save_disabled = not bool(st.session_state.loaded_file)
    if st.button("覆盖保存到当前CSV", use_container_width=True, disabled=save_disabled):
        target = BASE_DIR / st.session_state.loaded_file
        save_current_to(target)
        st.success(f"已覆盖保存：{target}")
with b3:
    filename = st.text_input("导出文件名", value="us_fba_export.csv")

csv_bytes = result_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
st.download_button(
    "导出为新CSV",
    data=csv_bytes,
    file_name=filename or "us_fba_export.csv",
    mime="text/csv",
    use_container_width=True,
)

st.subheader("结果表（自动计算）")
st.dataframe(result_df, use_container_width=True, hide_index=True)

st.subheader("单行实时预览")
if len(result_df) > 0:
    preview_index = st.number_input("预览第几行（从1开始）", min_value=1, max_value=len(result_df), value=1)
    st.json(result_df.iloc[preview_index - 1].to_dict())
else:
    st.info("当前没有数据行。")
