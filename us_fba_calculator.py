#!/usr/bin/env python3
"""US FBA 成本计算器（支持中文表头 + CLI + 可视化窗口）。"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except Exception:  # GUI 是可选能力，不影响 CLI
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


# MVP 简化费率（US）
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

# 兼容中英文字段名
FIELD_ALIASES = {
    "sku": ["sku", "SKU"],
    "category": ["category", "类目"],
    "sell_price": ["sell_price", "售价"],
    "length_cm": ["length_cm", "长cm", "长"],
    "width_cm": ["width_cm", "宽cm", "宽"],
    "height_cm": ["height_cm", "高cm", "高"],
    "weight_kg": ["weight_kg", "重量kg", "重量"],
    "product_cost": ["product_cost", "采购成本"],
    "inbound_cost": ["inbound_cost", "头程成本"],
    "ppc_pct": ["ppc_pct", "广告占比"],
    "return_pct": ["return_pct", "退货占比"],
    "tax_rate_pct": ["tax_rate_pct", "税率"],
}

OUTPUT_LABELS_ZH = {
    "sku": "SKU",
    "category": "类目",
    "size_tier": "大小件类型",
    "fba_fee_usd": "FBA尾程费USD",
    "referral_fee_usd": "佣金USD",
    "tax_amount_usd": "税费USD",
    "total_cost_usd": "总成本USD",
    "profit_usd": "利润USD",
    "margin_pct": "利润率%",
    "break_even_price_usd": "保本售价USD",
}


def to_float(v: Any, default: float = 0.0) -> float:
    if v in (None, ""):
        return default
    return float(v)


def normalize_dimensions(length_cm: float, width_cm: float, height_cm: float) -> tuple[float, float, float]:
    l, w, h = sorted([length_cm, width_cm, height_cm], reverse=True)
    return l, w, h


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
        "sku": input_data.sku,
        "category": input_data.category,
        "size_tier": size_tier,
        "fba_fee_usd": round(fba_fee, 2),
        "referral_fee_usd": round(referral, 2),
        "tax_amount_usd": round(tax_amount, 2),
        "total_cost_usd": round(total_cost, 2),
        "profit_usd": round(profit, 2),
        "margin_pct": round(margin_pct, 2),
        "break_even_price_usd": round(break_even, 2) if break_even != float("inf") else "inf",
    }


def get_field(row: dict[str, str], canonical: str, default: str = "") -> str:
    for key in FIELD_ALIASES[canonical]:
        if key in row:
            return row.get(key, default)
    return default


def row_to_product_input(row: dict[str, str]) -> ProductInput:
    return ProductInput(
        sku=get_field(row, "sku", ""),
        category=get_field(row, "category", "default"),
        sell_price=to_float(get_field(row, "sell_price", "0")),
        length_cm=to_float(get_field(row, "length_cm", "0")),
        width_cm=to_float(get_field(row, "width_cm", "0")),
        height_cm=to_float(get_field(row, "height_cm", "0")),
        weight_kg=to_float(get_field(row, "weight_kg", "0")),
        product_cost=to_float(get_field(row, "product_cost", "0")),
        inbound_cost=to_float(get_field(row, "inbound_cost", "0")),
        ppc_pct=to_float(get_field(row, "ppc_pct", "0")),
        return_pct=to_float(get_field(row, "return_pct", "0")),
        tax_rate_pct=to_float(get_field(row, "tax_rate_pct", "0")),
    )


def localize_result(result: dict[str, Any], zh_output: bool) -> dict[str, Any]:
    if not zh_output:
        return result
    return {OUTPUT_LABELS_ZH.get(k, k): v for k, v in result.items()}


def process_csv(input_csv: Path, output_csv: Path, zh_output: bool = True) -> int:
    with input_csv.open("r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        output_csv.write_text("", encoding="utf-8")
        return 0

    outputs: list[dict[str, Any]] = []
    for row in rows:
        item = row_to_product_input(row)
        result = localize_result(calculate(item), zh_output)
        outputs.append({**row, **result})

    with output_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(outputs[0].keys()))
        writer.writeheader()
        writer.writerows(outputs)

    return len(outputs)


def run_gui() -> None:
    if tk is None:
        raise SystemExit("当前 Python 未包含 tkinter，无法启动可视化窗口。")

    try:
        root = tk.Tk()
    except Exception as e:
        raise SystemExit(f"无法启动GUI（可能是无桌面环境）: {e}")
    root.title("US FBA 成本计算器")
    root.geometry("880x640")

    fields = [
        ("SKU", "sku", "A001"),
        ("类目", "category", "home"),
        ("售价", "sell_price", "29.99"),
        ("长cm", "length_cm", "22"),
        ("宽cm", "width_cm", "15"),
        ("高cm", "height_cm", "8"),
        ("重量kg", "weight_kg", "0.62"),
        ("采购成本", "product_cost", "6.5"),
        ("头程成本", "inbound_cost", "0.9"),
        ("广告占比", "ppc_pct", "8"),
        ("退货占比", "return_pct", "2"),
        ("税率", "tax_rate_pct", "0"),
    ]

    values: dict[str, tk.StringVar] = {}
    form = ttk.Frame(root, padding=10)
    form.pack(fill="x")

    for i, (label, key, default) in enumerate(fields):
        ttk.Label(form, text=label, width=12).grid(row=i // 2, column=(i % 2) * 2, sticky="w", padx=6, pady=4)
        var = tk.StringVar(value=default)
        values[key] = var
        ttk.Entry(form, textvariable=var, width=26).grid(row=i // 2, column=(i % 2) * 2 + 1, sticky="w", padx=6, pady=4)

    result_text = tk.Text(root, height=14)
    result_text.pack(fill="both", expand=True, padx=10, pady=10)

    def calc_single(*_: Any) -> None:
        try:
            p = ProductInput(
                sku=values["sku"].get(),
                category=values["category"].get(),
                sell_price=to_float(values["sell_price"].get()),
                length_cm=to_float(values["length_cm"].get()),
                width_cm=to_float(values["width_cm"].get()),
                height_cm=to_float(values["height_cm"].get()),
                weight_kg=to_float(values["weight_kg"].get()),
                product_cost=to_float(values["product_cost"].get()),
                inbound_cost=to_float(values["inbound_cost"].get()),
                ppc_pct=to_float(values["ppc_pct"].get()),
                return_pct=to_float(values["return_pct"].get()),
                tax_rate_pct=to_float(values["tax_rate_pct"].get()),
            )
            result = localize_result(calculate(p), zh_output=True)
            result_text.delete("1.0", tk.END)
            for k, v in result.items():
                result_text.insert(tk.END, f"{k}: {v}\n")
        except Exception as e:
            result_text.delete("1.0", tk.END)
            result_text.insert(tk.END, f"输入有误：{e}")

    for var in values.values():
        var.trace_add("write", calc_single)

    btn_frame = ttk.Frame(root, padding=10)
    btn_frame.pack(fill="x")

    def batch_convert() -> None:
        in_file = filedialog.askopenfilename(title="选择输入CSV", filetypes=[("CSV", "*.csv")])
        if not in_file:
            return
        out_file = filedialog.asksaveasfilename(title="保存输出CSV", defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not out_file:
            return
        try:
            cnt = process_csv(Path(in_file), Path(out_file), zh_output=True)
            messagebox.showinfo("完成", f"已处理 {cnt} 行\n输出文件：{out_file}")
        except Exception as e:
            messagebox.showerror("失败", str(e))

    ttk.Button(btn_frame, text="立即计算", command=calc_single).pack(side="left", padx=6)
    ttk.Button(btn_frame, text="批量CSV转换", command=batch_convert).pack(side="left", padx=6)

    calc_single()
    root.mainloop()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="US FBA calculator")
    p.add_argument("--input", help="输入CSV路径")
    p.add_argument("--output", help="输出CSV路径")
    p.add_argument("--output-lang", choices=["zh", "en"], default="zh", help="输出列名语言，默认中文")
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
        zh_output = args.output_lang == "zh"
        count = process_csv(Path(args.input), Path(args.output), zh_output=zh_output)
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
    result = localize_result(calculate(product), zh_output=args.output_lang == "zh")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
