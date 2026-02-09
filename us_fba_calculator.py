#!/usr/bin/env python3
"""US FBA 成本计算器（CLI + 中文CSV + 可视化编辑器）。"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except Exception:  # GUI 可选
    tk = None
    filedialog = messagebox = ttk = None


@dataclass
class ProductInput:
    sku: str
    category: str
    sell_price: float
    length_cm: float
    width_cm: float
    height_cm: float
    weight_kg: float
    product_cost: float = 0.0
    inbound_cost: float = 0.0
    ppc_pct: float = 0.0
    return_pct: float = 0.0
    tax_rate_pct: float = 0.0


REFERRAL_RATE = {
    "amazon-device-accessories": 0.45,
    "beauty": 0.08,
    "grocery": 0.08,
    "home": 0.15,
    "kitchen": 0.15,
    "sports": 0.15,
    "electronics": 0.08,
    "default": 0.15,
}
MIN_REFERRAL_FEE = {"default": 0.30}

# 内部标准字段（保存/GUI统一使用）
CORE_FIELDS = [
    "SKU",
    "类目",
    "售价",
    "长cm",
    "宽cm",
    "高cm",
    "重量kg",
    "采购成本",
    "头程成本",
    "广告占比",
    "退货占比",
    "税率",
]

OUTPUT_LABELS_ZH = [
    "大小件类型",
    "FBA尾程费USD",
    "佣金USD",
    "税费USD",
    "总成本USD",
    "利润USD",
    "利润率%",
    "保本售价USD",
]

FIELD_ALIASES = {
    "SKU": ["SKU", "sku"],
    "类目": ["类目", "category"],
    "售价": ["售价", "sell_price"],
    "长cm": ["长cm", "length_cm", "长"],
    "宽cm": ["宽cm", "width_cm", "宽"],
    "高cm": ["高cm", "height_cm", "高"],
    "重量kg": ["重量kg", "weight_kg", "重量"],
    "采购成本": ["采购成本", "product_cost"],
    "头程成本": ["头程成本", "inbound_cost"],
    "广告占比": ["广告占比", "ppc_pct"],
    "退货占比": ["退货占比", "return_pct"],
    "税率": ["税率", "tax_rate_pct"],
}


def to_float(v: Any, default: float = 0.0) -> float:
    if v in (None, ""):
        return default
    return float(v)


def normalize_dimensions(length_cm: float, width_cm: float, height_cm: float) -> tuple[float, float, float]:
    return tuple(sorted([length_cm, width_cm, height_cm], reverse=True))


def classify_size_tier(length_cm: float, width_cm: float, height_cm: float, weight_kg: float) -> str:
    l, w, h = normalize_dimensions(length_cm, width_cm, height_cm)
    girth_plus_length = l + 2 * (w + h)
    if l <= 45 and w <= 35 and h <= 20 and weight_kg <= 0.45:
        return "Small standard-size"
    if l <= 45 and w <= 35 and h <= 20 and weight_kg <= 9.0:
        return "Large standard-size"
    if l <= 150 and girth_plus_length <= 330 and weight_kg <= 30:
        return "Large bulky"
    return "Extra-large"


def fulfillment_fee_usd(size_tier: str, weight_kg: float) -> float:
    if size_tier == "Small standard-size":
        return 3.22 if weight_kg <= 0.45 else 3.86
    if size_tier == "Large standard-size":
        if weight_kg <= 0.45:
            return 3.86
        if weight_kg <= 0.9:
            return 4.75
        if weight_kg <= 1.35:
            return 5.40
        return 6.20 + max(0.0, weight_kg - 1.35) * 0.32
    if size_tier == "Large bulky":
        if weight_kg <= 0.45:
            return 9.61
        if weight_kg <= 4.5:
            return 10.10
        return 10.10 + (weight_kg - 4.5) * 0.38
    return 26.33 + max(0.0, weight_kg - 22.7) * 0.38


def referral_fee_usd(category: str, sell_price: float) -> float:
    key = category.strip().lower().replace(" ", "-")
    rate = REFERRAL_RATE.get(key, REFERRAL_RATE["default"])
    min_fee = MIN_REFERRAL_FEE.get(key, MIN_REFERRAL_FEE["default"])
    return max(sell_price * rate, min_fee)


def category_rate(category: str) -> float:
    key = category.strip().lower().replace(" ", "-")
    return REFERRAL_RATE.get(key, REFERRAL_RATE["default"])


def calculate(input_data: ProductInput) -> dict[str, float | str]:
    size_tier = classify_size_tier(input_data.length_cm, input_data.width_cm, input_data.height_cm, input_data.weight_kg)
    fba_fee = fulfillment_fee_usd(size_tier, input_data.weight_kg)
    referral = referral_fee_usd(input_data.category, input_data.sell_price)

    ppc_cost = input_data.sell_price * input_data.ppc_pct / 100
    return_cost = input_data.sell_price * input_data.return_pct / 100
    tax_amount = input_data.sell_price * input_data.tax_rate_pct / 100

    total_cost = input_data.product_cost + input_data.inbound_cost + fba_fee + referral + ppc_cost + return_cost + tax_amount
    profit = input_data.sell_price - total_cost
    margin_pct = (profit / input_data.sell_price * 100) if input_data.sell_price else 0.0

    variable_cost_rate = category_rate(input_data.category) + input_data.ppc_pct / 100 + input_data.return_pct / 100 + input_data.tax_rate_pct / 100
    fixed_cost = input_data.product_cost + input_data.inbound_cost + fba_fee
    break_even = float("inf") if variable_cost_rate >= 1 else max(fixed_cost, fixed_cost / (1 - variable_cost_rate))

    return {
        "大小件类型": size_tier,
        "FBA尾程费USD": round(fba_fee, 2),
        "佣金USD": round(referral, 2),
        "税费USD": round(tax_amount, 2),
        "总成本USD": round(total_cost, 2),
        "利润USD": round(profit, 2),
        "利润率%": round(margin_pct, 2),
        "保本售价USD": round(break_even, 2) if break_even != float("inf") else "inf",
    }


def _get_alias_value(row: dict[str, str], canonical: str) -> str:
    for alias in FIELD_ALIASES[canonical]:
        if alias in row:
            return row.get(alias, "")
    return ""


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    normalized = {field: _get_alias_value(row, field) for field in CORE_FIELDS}
    return normalized


def row_to_product_input(row: dict[str, str]) -> ProductInput:
    normalized = normalize_row(row)
    return ProductInput(
        sku=normalized["SKU"],
        category=normalized["类目"] or "default",
        sell_price=to_float(normalized["售价"]),
        length_cm=to_float(normalized["长cm"]),
        width_cm=to_float(normalized["宽cm"]),
        height_cm=to_float(normalized["高cm"]),
        weight_kg=to_float(normalized["重量kg"]),
        product_cost=to_float(normalized["采购成本"]),
        inbound_cost=to_float(normalized["头程成本"]),
        ppc_pct=to_float(normalized["广告占比"]),
        return_pct=to_float(normalized["退货占比"]),
        tax_rate_pct=to_float(normalized["税率"]),
    )


def enrich_row(row: dict[str, str]) -> dict[str, Any]:
    normalized = normalize_row(row)
    result = calculate(row_to_product_input(normalized))
    return {**normalized, **result}


def process_csv(input_csv: Path, output_csv: Path) -> int:
    with input_csv.open("r", newline="", encoding="utf-8-sig") as f:
        rows = [normalize_row(r) for r in csv.DictReader(f)]

    outputs = [enrich_row(r) for r in rows]
    header = CORE_FIELDS + OUTPUT_LABELS_ZH

    with output_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(outputs)

    return len(outputs)


def run_gui() -> None:
    if tk is None:
        raise SystemExit("当前 Python 未包含 tkinter，无法启动可视化窗口。")

    try:
        root = tk.Tk()
    except Exception as exc:
        raise SystemExit(f"无法启动GUI（可能是无桌面环境）: {exc}")

    root.title("US FBA 成本可视化工具")
    root.geometry("1300x760")

    current_csv = {"path": None}

    top = ttk.Frame(root, padding=8)
    top.pack(fill="x")

    ttk.Label(top, text="当前目录CSV:").pack(side="left")
    csv_choice = tk.StringVar()
    csv_combo = ttk.Combobox(top, textvariable=csv_choice, width=50, state="readonly")
    csv_combo.pack(side="left", padx=6)

    status_var = tk.StringVar(value="未加载文件")
    ttk.Label(top, textvariable=status_var).pack(side="left", padx=10)

    table_frame = ttk.Frame(root, padding=8)
    table_frame.pack(fill="both", expand=True)

    columns = CORE_FIELDS + OUTPUT_LABELS_ZH
    tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
    for col in columns:
        width = 100 if col in OUTPUT_LABELS_ZH else 90
        if col in ("SKU", "类目"):
            width = 120
        tree.heading(col, text=col)
        tree.column(col, width=width, anchor="center")

    y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
    tree.grid(row=0, column=0, sticky="nsew")
    y_scroll.grid(row=0, column=1, sticky="ns")
    x_scroll.grid(row=1, column=0, sticky="ew")
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    edit = ttk.LabelFrame(root, text="编辑区（选中行后可修改，新增行也在这里填）", padding=8)
    edit.pack(fill="x", padx=8, pady=6)

    vars_map: dict[str, tk.StringVar] = {}
    for idx, field in enumerate(CORE_FIELDS):
        r, c = divmod(idx, 6)
        ttk.Label(edit, text=field).grid(row=r * 2, column=c, sticky="w", padx=4)
        v = tk.StringVar(value="")
        vars_map[field] = v
        ttk.Entry(edit, textvariable=v, width=20).grid(row=r * 2 + 1, column=c, padx=4, pady=4, sticky="we")

    live_text = tk.Text(root, height=6)
    live_text.pack(fill="x", padx=8, pady=4)

    def calc_live(*_args: Any) -> None:
        try:
            row = {k: v.get() for k, v in vars_map.items()}
            result = calculate(row_to_product_input(row))
            live_text.delete("1.0", tk.END)
            for k in OUTPUT_LABELS_ZH:
                live_text.insert(tk.END, f"{k}: {result[k]}\n")
        except Exception as exc:
            live_text.delete("1.0", tk.END)
            live_text.insert(tk.END, f"输入有误：{exc}")

    for v in vars_map.values():
        v.trace_add("write", calc_live)

    def tree_to_rows() -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item_id in tree.get_children():
            values = tree.item(item_id, "values")
            rows.append(dict(zip(columns, values)))
        return rows

    def fill_tree(rows: list[dict[str, Any]]) -> None:
        tree.delete(*tree.get_children())
        for row in rows:
            tree.insert("", tk.END, values=[row.get(c, "") for c in columns])

    def refresh_csv_list() -> None:
        candidates = sorted([p.name for p in Path.cwd().glob("*.csv")])
        csv_combo["values"] = candidates
        if candidates and not csv_choice.get():
            csv_choice.set(candidates[0])

    def load_selected_csv() -> None:
        name = csv_choice.get().strip()
        if not name:
            messagebox.showwarning("提示", "请先选择一个CSV文件")
            return
        path = Path.cwd() / name
        if not path.exists():
            messagebox.showerror("错误", f"文件不存在：{path}")
            return

        with path.open("r", newline="", encoding="utf-8-sig") as f:
            base_rows = [normalize_row(r) for r in csv.DictReader(f)]
        rows = [enrich_row(r) for r in base_rows]
        fill_tree(rows)
        current_csv["path"] = path
        status_var.set(f"已加载：{path.name}（{len(rows)}行）")

    def on_select(_event: Any) -> None:
        selected = tree.selection()
        if not selected:
            return
        values = tree.item(selected[0], "values")
        row = dict(zip(columns, values))
        for field in CORE_FIELDS:
            vars_map[field].set(str(row.get(field, "")))

    def upsert_selected() -> None:
        row = {k: v.get() for k, v in vars_map.items()}
        enriched = enrich_row(row)
        selected = tree.selection()
        if selected:
            tree.item(selected[0], values=[enriched.get(c, "") for c in columns])
        else:
            tree.insert("", tk.END, values=[enriched.get(c, "") for c in columns])

    def add_new_row() -> None:
        for f in CORE_FIELDS:
            vars_map[f].set("")
        vars_map["SKU"].set(f"SKU-{len(tree.get_children()) + 1:03d}")

    def save_overwrite() -> None:
        path = current_csv["path"]
        if path is None:
            messagebox.showwarning("提示", "请先加载一个CSV文件")
            return
        rows = tree_to_rows()
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        status_var.set(f"已覆盖保存：{path.name}（{len(rows)}行）")
        messagebox.showinfo("完成", f"已覆盖保存到：{path}")

    def export_as() -> None:
        rows = tree_to_rows()
        if not rows:
            messagebox.showwarning("提示", "当前没有可导出的数据")
            return
        target = filedialog.asksaveasfilename(title="导出CSV", defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not target:
            return
        out = Path(target)
        with out.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        messagebox.showinfo("完成", f"已导出：{out}")

    btns = ttk.Frame(root, padding=8)
    btns.pack(fill="x")
    ttk.Button(btns, text="刷新当前目录CSV", command=refresh_csv_list).pack(side="left", padx=4)
    ttk.Button(btns, text="打开选中文件", command=load_selected_csv).pack(side="left", padx=4)
    ttk.Button(btns, text="新增空白行", command=add_new_row).pack(side="left", padx=4)
    ttk.Button(btns, text="新增/更新当前行", command=upsert_selected).pack(side="left", padx=4)
    ttk.Button(btns, text="覆盖保存到当前CSV", command=save_overwrite).pack(side="left", padx=4)
    ttk.Button(btns, text="导出为新CSV", command=export_as).pack(side="left", padx=4)

    tree.bind("<<TreeviewSelect>>", on_select)
    refresh_csv_list()
    calc_live()
    root.mainloop()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="US FBA calculator")
    p.add_argument("--input", help="输入CSV路径")
    p.add_argument("--output", help="输出CSV路径")
    p.add_argument("--gui", action="store_true", help="启动可视化窗口")

    p.add_argument("--sku", default="A001")
    p.add_argument("--category", default="home")
    p.add_argument("--sell-price", type=float, default=29.99)
    p.add_argument("--length-cm", type=float, default=22)
    p.add_argument("--width-cm", type=float, default=15)
    p.add_argument("--height-cm", type=float, default=8)
    p.add_argument("--weight-kg", type=float, default=0.62)
    p.add_argument("--product-cost", type=float, default=6.5)
    p.add_argument("--inbound-cost", type=float, default=0.9)
    p.add_argument("--ppc-pct", type=float, default=8)
    p.add_argument("--return-pct", type=float, default=2)
    p.add_argument("--tax-rate-pct", type=float, default=0)
    return p


def main() -> None:
    args = build_parser().parse_args()

    if args.gui:
        run_gui()
        return

    if args.input or args.output:
        if not (args.input and args.output):
            raise SystemExit("批量模式需要同时提供 --input 和 --output")
        count = process_csv(Path(args.input), Path(args.output))
        print(f"Processed {count} rows -> {args.output}")
        return

    product = ProductInput(
        sku=args.sku,
        category=args.category,
        sell_price=args.sell_price,
        length_cm=args.length_cm,
        width_cm=args.width_cm,
        height_cm=args.height_cm,
        weight_kg=args.weight_kg,
        product_cost=args.product_cost,
        inbound_cost=args.inbound_cost,
        ppc_pct=args.ppc_pct,
        return_pct=args.return_pct,
        tax_rate_pct=args.tax_rate_pct,
    )

    print("Input:")
    for k, v in asdict(product).items():
        print(f"  {k}: {v}")
    print("\nResult:")
    for k, v in calculate(product).items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
