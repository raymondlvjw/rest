# US FBA 成本工具（可视化实时计算 + CSV编辑）

## 你这次要求的能力（已支持）
- 直接打开可视化窗口输入产品信息，实时计算费用。
- 在窗口里选择**当前文件夹下**的 CSV 文件并查看内容。
- 可以新增数据行、更新已有行。
- 可以“覆盖保存”回原 CSV（同步更新）。
- 也支持“导出为新CSV”。

---

## 1) 数据来源说明（你问的佣金/FBA来源）
当前脚本中的佣金和 FBA 是 **MVP 简化估算规则**：
- 佣金：类目比例（如 home 15%、electronics 8%）+ 最低佣金保护
- FBA：按尺寸段 + 重量段的简化分段

不是 Amazon 官方实时 API 数据；正式上线前请按 Seller Central 最新费率更新脚本里的：
- `REFERRAL_RATE` / `MIN_REFERRAL_FEE`
- `fulfillment_fee_usd()`

---

## 2) 可视化窗口使用（推荐）
### 方式A：双击启动（Windows）
直接双击：`launch_gui.bat`

### 方式B：命令启动
```bash
python us_fba_calculator.py --gui
```

### 窗口内操作流程
1. 点击 **刷新当前目录CSV**（扫描当前目录所有 `.csv`）。
2. 下拉选择目标文件，点击 **打开选中文件**。
3. 点击某一行后，下方编辑区会载入该行内容。修改后点 **新增/更新当前行**。
4. 若要新增，点 **新增空白行**，填写后点 **新增/更新当前行**。
5. 点 **覆盖保存到当前CSV**，会直接覆盖原文件。
6. 点 **导出为新CSV** 可另存一份。

---

## 3) CSV表头（中文）
输入与输出都使用中文字段：
- 核心输入：`SKU,类目,售价,长cm,宽cm,高cm,重量kg,采购成本,头程成本,广告占比,退货占比,税率`
- 计算输出：`大小件类型,FBA尾程费USD,佣金USD,税费USD,总成本USD,利润USD,利润率%,保本售价USD`

模板文件：`us_fba_template.csv`

---

## 4) 命令行批量（仍可用）
```bash
python us_fba_calculator.py --input us_fba_template.csv --output us_fba_result.csv
```

---

## 5) 常见问题
- `--gui` 报错 no display：表示当前环境无桌面（如服务器容器），在本机 Windows 运行即可。
- 打开后没看到新文件：先确认你保存覆盖的是当前窗口顶部状态里显示的那个 CSV。
