<!-- README_screening_tools_zh.md -->

# 双盲 / 三轮筛选工具脚本说明

本说明文档用于介绍本项目中与文献双盲 / 三轮筛选流程相关的工具脚本，并按照筛选阶段（初筛 / 二筛）进行归类，便于后续按阶段扩展和维护。

---

## 初筛阶段（Title / Abstract 双盲筛选）

在 **初筛阶段（题目 / 摘要双盲筛选）**，当前已实现的 4 个 Python 脚本负责对筛选结果进行统一整理与统计，包括批次合并、一致性检查、决策分布汇总，以及三轮裁决后的最终纳入 / 排除统计。  

初筛阶段对应的文献 PDF 文件统一存放于：  `data/systematic_review/double_blind/stage1_title_abstract/pdfs/`

- **`merge_double_blind_batches.py`**
  
  将 R1、R2 的双盲筛选批次 CSV 文件合并为单一结果文件，并对 `Notes` 列进行 JSON 格式标准化，同时重新生成全局统一的 `No.` 编号。

- **`double_blind_consistency.py`**
  
  按 `Title + Year` 对齐 R1、R2 结果，检查 `Decision` 与 `No.` 的一致性，并导出带有 `Need_R3` 标记的 R1–R2 合并表及对应一致性文本报告。

- **`double_blind_summary.py`**
  
  分别统计 R1、R2 的 `Decision` 分布，并按 `Decision` 分组列出所有 `Decision != "exclude"` 记录的 `No.` 列表，用于初筛阶段的人工复核与质控。

- **`triple_blind_consistency.py`**
  
  基于初筛阶段的三轮（R1/R2/R3）筛选结果，在 `Need_R3 = "yes"` 条件下汇总 `R3_Decision` 分布及与访问 / 付费 / 语言限制相关的 `R3_Notes`，并统计最终纳入 / 排除文献数量及对应 `No.` 列表。

---

## 二筛阶段（Full-text 双盲筛选）

**二筛阶段（Full-text 双盲筛选）** 的处理脚本尚未在本说明中列出。  

二筛阶段对应的文献 PDF 文件计划统一存放于：  `data/systematic_review/double_blind/stage2_full_text/pdfs/`  

后续如新增用于二筛阶段的 Python 工具脚本，可在本节补充相应的功能简介与使用说明，以保持与初筛阶段说明风格的一致性。
