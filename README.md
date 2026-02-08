# US FBA 成本自动计算器（中文表头 + 可视化）

这个工具现在支持：
- ✅ 中文输入表头（也兼容英文表头）
- ✅ 中文输出表头（默认）
- ✅ 单个产品命令行计算
- ✅ 批量 CSV 计算
- ✅ 可视化窗口实时计算（GUI）

---

## 1）关于你问的“佣金/FBA数据来自哪里？”

当前版本使用的是 **MVP 简化费率**，依据 Amazon US 常见费率结构做了估算模型：
- 佣金：按类目比例（如 home 15%、electronics 8%）+ 最低佣金保护
- FBA 尾程费：按简化的尺寸段 + 重量分段

> 这不是官方实时接口数据。正式上线前请用 Amazon Seller Central 最新费率公告更新 `REFERRAL_RATE` 与 `fulfillment_fee_usd()`。

核心费率位置：
- `REFERRAL_RATE` / `MIN_REFERRAL_FEE`
- `fulfillment_fee_usd()`

---

## 2）批量 CSV（中文表头）

### 输入模板
文件：`us_fba_template.csv`

表头：
`SKU,类目,售价,长cm,宽cm,高cm,重量kg,采购成本,头程成本,广告占比,退货占比,税率`

### 执行命令
Windows 推荐：
```bash
python us_fba_calculator.py --input us_fba_template.csv --output us_fba_result.csv
```

输出默认使用中文字段（例如：`大小件类型`、`FBA尾程费USD`、`利润USD`）。

如果你想输出英文字段：
```bash
python us_fba_calculator.py --input us_fba_template.csv --output us_fba_result.csv --output-lang en
```

---

## 3）单个产品命令行计算

```bash
python us_fba_calculator.py \
  --sku A100 \
  --category home \
  --sell-price 39.99 \
  --length-cm 30 --width-cm 20 --height-cm 10 \
  --weight-kg 0.8 \
  --product-cost 8.5 --inbound-cost 1.2 \
  --ppc-pct 10 --return-pct 2 --tax-rate-pct 0
```

---

## 4）可视化窗口（你要的“直接窗口输入实时计算”）

启动方式：
```bash
python us_fba_calculator.py --gui
```

功能：
- 左侧输入 SKU、类目、尺寸、重量、成本、税率
- 实时显示计算结果
- 点击“批量CSV转换”可选择输入文件并导出结果

> 如果运行报错提示缺少 tkinter：说明你的 Python 安装未包含 GUI 组件。

---

## 5）本地仓库/分支提醒

如果 GitHub 网页看不到文件，通常是：
1. 改动在 `work` 分支，不在 `main`
2. 本地还没 `git push` 到远程

可先执行：
```bash
git branch -vv
git remote -v
git push -u origin work
```
