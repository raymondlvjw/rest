# US FBA 成本工具（Streamlit 可视化版）

你提到的问题（CSV加载失败、无法新增行、界面不好看）已改为 **Streamlit** 方案。现在是一个网页化可视化工具：

- 选择当前文件夹下 CSV 并打开
- 直接在表格里编辑
- 新增空白行
- 实时自动重算 FBA/佣金/利润
- 覆盖保存到原 CSV
- 导出为新 CSV

---

## 1) 快速启动

### 方式A（Windows 双击）
双击：`launch_gui.bat`

### 方式B（命令行）
```bash
streamlit run streamlit_app.py
```

如果没有安装依赖：
```bash
pip install -r requirements.txt
```

---

## 2) 使用步骤

1. 打开页面后，在顶部下拉框选择当前目录中的 CSV。
2. 点击 **打开选中文件**。
3. 在中间表格直接编辑（可改原数据列）。
4. 点击 **新增空白行** 可快速插入新产品。
5. 系统会自动重算输出列（大小件、FBA、佣金、利润等）。
6. 点击 **覆盖保存到当前CSV** 可同步覆盖原文件。
7. 点击 **导出为新CSV** 可下载另存。

---

## 3) 数据来源说明

当前佣金/FBA数据为 **MVP 简化估算规则**，来源于 Amazon US 常见费率结构建模，不是官方实时 API。
正式使用请按 Seller Central 最新费率更新：
- `REFERRAL_RATE` / `MIN_REFERRAL_FEE`
- `fulfillment_fee_usd()`

---

## 4) 命令行批量（保留）

```bash
python us_fba_calculator.py --input us_fba_template.csv --output us_fba_result.csv
```

---

## 5) 文件说明

- `us_fba_calculator.py`：核心计算与批量CSV处理
- `streamlit_app.py`：可视化页面（推荐）
- `us_fba_template.csv`：中文模板
- `launch_gui.bat`：Windows 双击启动脚本

---

## 6) 交互优化说明（已修复你反馈的“输入闪一下/要输两次”）

已修复为“输入表”和“结果表”分离：
- 上方只编辑输入字段（SKU、尺寸、重量、成本等）
- 下方自动展示计算结果

这样不会再把计算结果列反向写回编辑控件，避免出现：
- 首次输入被覆盖
- 修改后要再输入一次才更新

说明：Streamlit 每次编辑都会触发一次 rerun（这是框架机制），页面有轻微刷新是正常现象；但数据不应再丢失，计算也会同轮更新。
