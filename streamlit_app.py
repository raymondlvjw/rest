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


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """确保列完整、顺序统一，并补算结果列。"""
    for col in CORE_FIELDS:
        if col not in df.columns:
            df[col] = ""

    base = df[CORE_FIELDS].fillna("")
    records = []
    for _, row in base.iterrows():
        records.append(enrich_row(row.to_dict()))
    return pd.DataFrame(records, columns=ALL_COLUMNS)


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=ALL_COLUMNS)
    raw = pd.read_csv(path, encoding="utf-8-sig")
    return normalize_df(raw)


def recalc_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in CORE_FIELDS:
        if col not in df.columns:
            df[col] = ""
    base = df[CORE_FIELDS].fillna("")
    rows = [enrich_row(r) for r in base.to_dict(orient="records")]
    return pd.DataFrame(rows, columns=ALL_COLUMNS)


csv_files = sorted([p.name for p in BASE_DIR.glob("*.csv")])
if not csv_files:
    st.warning("当前目录没有 CSV 文件。请先放一个 CSV（例如 us_fba_template.csv）。")

selected = st.selectbox("选择当前目录CSV文件", options=csv_files, index=0 if csv_files else None)

if "loaded_file" not in st.session_state:
    st.session_state.loaded_file = ""
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=ALL_COLUMNS)

col_load, col_reload = st.columns([1, 1])
with col_load:
    if st.button("打开选中文件", use_container_width=True, disabled=not bool(selected)):
        st.session_state.df = load_csv(BASE_DIR / selected)
        st.session_state.loaded_file = selected
with col_reload:
    if st.button("重新计算当前表", use_container_width=True):
        st.session_state.df = recalc_df(st.session_state.df)

if st.session_state.loaded_file:
    st.success(f"已加载：{st.session_state.loaded_file}，共 {len(st.session_state.df)} 行")

st.subheader("表格编辑区")
st.write("你可以直接在表格里改值；新增行请点击下方“新增空白行”。")

edited_df = st.data_editor(
    st.session_state.df,
    use_container_width=True,
    num_rows="dynamic",
    hide_index=True,
    key="editor",
)

st.session_state.df = recalc_df(edited_df)

c1, c2, c3 = st.columns([1, 1, 1])
with c1:
    if st.button("新增空白行", use_container_width=True):
        new_row = {col: "" for col in ALL_COLUMNS}
        new_row["SKU"] = f"SKU-{len(st.session_state.df) + 1:03d}"
        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
        st.rerun()
with c2:
    save_disabled = not bool(st.session_state.loaded_file)
    if st.button("覆盖保存到当前CSV", use_container_width=True, disabled=save_disabled):
        target = BASE_DIR / st.session_state.loaded_file
        st.session_state.df.to_csv(target, index=False, encoding="utf-8-sig")
        st.success(f"已覆盖保存：{target}")
with c3:
    filename = st.text_input("导出文件名", value="us_fba_export.csv")

csv_bytes = st.session_state.df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
st.download_button(
    "导出为新CSV",
    data=csv_bytes,
    file_name=filename or "us_fba_export.csv",
    mime="text/csv",
    use_container_width=True,
)

st.subheader("单行实时预览")
if len(st.session_state.df) > 0:
    preview_index = st.number_input("预览第几行（从1开始）", min_value=1, max_value=len(st.session_state.df), value=1)
    st.json(st.session_state.df.iloc[preview_index - 1].to_dict())
else:
    st.info("当前没有数据行。")
