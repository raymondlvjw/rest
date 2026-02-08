#!/usr/bin/env python3
"""US FBA calculator (MVP+).

Supports:
- single-item calculation (from CLI args)
- batch CSV processing: --input xxx.csv --output yyy.csv
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


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


def to_float(v: Any, default: float = 0.0) -> float:
    if v in (None, ""):
        return default
    return float(v)


def normalize_dimensions(length_cm: float, width_cm: float, height_cm: float) -> tuple[float, float, float]:
    l, w, h = sorted([length_cm, width_cm, height_cm], reverse=True)
    return l, w, h


def classify_size_tier(length_cm: float, width_cm: float, height_cm: float, weight_kg: float) -> str:
    """Simplified US size-tier classifier."""
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
    """Simplified fulfillment fee table for US marketplace."""
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
    size_tier = classify_size_tier(
        input_data.length_cm,
        input_data.width_cm,
        input_data.height_cm,
        input_data.weight_kg,
    )
    fba_fee = fulfillment_fee_usd(size_tier, input_data.weight_kg)
    referral = referral_fee_usd(input_data.category, input_data.sell_price)

    ppc_cost = input_data.sell_price * input_data.ppc_pct / 100
    return_cost = input_data.sell_price * input_data.return_pct / 100
    tax_amount = input_data.sell_price * input_data.tax_rate_pct / 100

    total_cost = (
        input_data.product_cost
        + input_data.inbound_cost
        + fba_fee
        + referral
        + ppc_cost
        + return_cost
        + tax_amount
    )
    profit = input_data.sell_price - total_cost
    margin_pct = (profit / input_data.sell_price * 100) if input_data.sell_price else 0.0

    variable_cost_rate = (
        category_rate(input_data.category)
        + input_data.ppc_pct / 100
        + input_data.return_pct / 100
        + input_data.tax_rate_pct / 100
    )
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


def row_to_product_input(row: dict[str, str]) -> ProductInput:
    return ProductInput(
        sku=row.get("sku", ""),
        category=row.get("category", "default"),
        sell_price=to_float(row.get("sell_price")),
        length_cm=to_float(row.get("length_cm")),
        width_cm=to_float(row.get("width_cm")),
        height_cm=to_float(row.get("height_cm")),
        weight_kg=to_float(row.get("weight_kg")),
        product_cost=to_float(row.get("product_cost"), 0.0),
        inbound_cost=to_float(row.get("inbound_cost"), 0.0),
        ppc_pct=to_float(row.get("ppc_pct"), 0.0),
        return_pct=to_float(row.get("return_pct"), 0.0),
        tax_rate_pct=to_float(row.get("tax_rate_pct"), 0.0),
    )


def process_csv(input_csv: Path, output_csv: Path) -> int:
    with input_csv.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        with output_csv.open("w", newline="", encoding="utf-8") as f:
            f.write("")
        return 0

    outputs: list[dict[str, Any]] = []
    for row in rows:
        item = row_to_product_input(row)
        result = calculate(item)
        outputs.append({**row, **result})

    fieldnames = list(outputs[0].keys())
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(outputs)

    return len(outputs)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="US FBA calculator: single or batch CSV mode")
    p.add_argument("--input", help="Input CSV path (batch mode)")
    p.add_argument("--output", help="Output CSV path (batch mode)")

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

    if args.input or args.output:
        if not (args.input and args.output):
            raise SystemExit("Batch mode requires both --input and --output")
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
