# US FBA 成本自动计算器（更好上手版）

这个工具用于美国站（US）快速估算：
- 大小件类型（`size_tier`）
- FBA 尾程费（`fba_fee_usd`）
- 销售佣金（`referral_fee_usd`）
- 税费（`tax_amount_usd`）
- 总成本、利润、利润率、保本售价

> 说明：当前费率是 MVP 简化规则，用于快速测算；正式使用前请按 Amazon US 官方最新费率更新。

---

## 1. “本地仓库”是什么？在哪里？

你现在看到的这套文件在**本地 git 仓库**里（也就是你当前代码工作目录）。
当前路径是：
- `/workspace/rest`

在终端里运行：
```bash
pwd
git status -sb
git branch -vv
```
可以看到你正在哪个分支（例如 `work`），文件是否已提交。

---

## 2. 快速开始（单个产品）

直接运行：

```bash
python3 us_fba_calculator.py
```

它会用默认示例参数计算，并输出输入与结果。

你也可以传入自己的参数：

```bash
python3 us_fba_calculator.py \
  --sku A100 \
  --category home \
  --sell-price 39.99 \
  --length-cm 30 \
  --width-cm 20 \
  --height-cm 10 \
  --weight-kg 0.8 \
  --product-cost 8.5 \
  --inbound-cost 1.2 \
  --ppc-pct 10 \
  --return-pct 2 \
  --tax-rate-pct 0
```

---

## 3. 一键批量算（CSV）

### 输入模板
参考：`us_fba_template.csv`

字段：
- `sku, category, sell_price, length_cm, width_cm, height_cm, weight_kg, product_cost, inbound_cost, ppc_pct, return_pct, tax_rate_pct`

### 运行批量计算

```bash
python3 us_fba_calculator.py --input us_fba_template.csv --output us_fba_result.csv
```

运行后会生成 `us_fba_result.csv`，每一行会新增：
- `size_tier`
- `fba_fee_usd`
- `referral_fee_usd`
- `tax_amount_usd`
- `total_cost_usd`
- `profit_usd`
- `margin_pct`
- `break_even_price_usd`

---

## 4. 为什么 GitHub 网页看不到文件？（分支切换步骤）

通常是因为你在网页看的是 `main`，而本地改动在 `work` 分支。

操作步骤（GitHub 页面）：
1. 打开仓库首页。
2. 点击左上角分支下拉（一般显示 `main`）。
3. 输入并切换到 `work` 分支。
4. 切换后就能看到本地提交过并推送到该分支的文件。

如果 `work` 还没推送，先在终端执行：

```bash
git remote -v
git push -u origin work
```

---

## 5. 计算逻辑（简化）

1. 根据尺寸重量判断 `size_tier`
2. 根据 `size_tier + weight_kg` 匹配尾程费
3. 根据类目匹配佣金率并应用最低佣金保护
4. 叠加广告/退货/税费成本
5. 输出利润、利润率、保本售价
