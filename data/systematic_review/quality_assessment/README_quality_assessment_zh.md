# L2 写作 LLM 干预研究：质量评估字段映射说明（Stage 2 Full-text）

本说明文档用于阐明：如何利用 `data_extraction_table.xlsx` 中的字段，对纳入研究进行 **10 条质量标准** 的系统化评估。  
每条质量标准均提供：

- ✅ **Standard**：质量标准的定义  
- ✅ **Mapped fields**：在数据提取表中，与该标准直接相关的字段  
- ✅ **Purpose & usage**：这些字段如何支持你做出质量判断

> 建议用途：  
> - 与 `quality_assessment_table.xlsx` 搭配，用于指导评分与证据记录；  
> - 作为培训新评审者的“字段–质量标准对照表”；  
> - 作为质量评估过程的可审计依据。

---

## 目录

1. [研究目的清晰 + 理论/实践创新性](#1-研究目的清晰--理论实践创新性)  
2. [参与者信息 + 关键背景变量](#2-参与者信息--关键背景变量语言水平母语等)  
3. [抽样方法 + 样本量 + 功效分析 + 代表性](#3-抽样方法--样本量--功效分析--代表性)  
4. [实验–对照分配方式及潜在偏倚](#4-实验对照分配方式及潜在偏倚)  
5. [纵向比较，短期与长期效应](#5-纵向比较短期与长期效应)  
6. [工具信度与效度（含群体适用性）](#6-工具信度与效度含对特定语言群体的适用性)  
7. [实验步骤和干预时长的可操作性](#7-实验步骤和干预时长的可操作性)  
8. [统计方法与自变量/因变量的匹配](#8-统计方法与自变量因变量的匹配)  
9. [统计假设、检验方法与效应大小](#9-统计假设检验方法与效应大小)  
10. [异常值处理、结果解释与理论整合](#10-异常值处理结果解释与理论整合)  

---

## 全局速览：质量标准与字段映射一览表

> 这一节方便你快速定位“某个质量标准依托哪些字段”。

| #  | 质量标准简述                                   | 核心映射字段示例                                                                                     |
|----|-----------------------------------------------|------------------------------------------------------------------------------------------------------|
| 1  | 研究目的清晰 + 理论/实践创新性                | Basic Identification.research_aims / research_gap_or_novelty；Methodology.theoretical_foundation    |
| 2  | 参与者信息 + 语言背景                         | Participant Information.educational_level / language_proficiency / mother_tongue / learning_context |
| 3  | 抽样方法 + 样本量 + 功效分析 + 代表性         | Methodology.sampling_method / sample_size_and_effect / power_analysis / sampling_frame_and_representativeness |
| 4  | 实验–对照分配与偏倚                           | Methodology.group_assignment_method；Study Quality and Reporting.risk_of_bias_randomization / baseline_equivalence |
| 5  | 纵向设计 + 短期与长期效应                     | Methodology.research_design；Intervention.duration；Outcome.assessment_timepoints / followup_length_and_type |
| 6  | 工具信度与效度 + 评分者训练                   | Methodology.data_collection_instrument / data_collection_validity_reliability / scoring_procedure_and_rater_training |
| 7  | 干预步骤 + 时长 + 可复现性                    | Intervention.duration / intervention_implementation / writing_stage / setting / llm_* 相关字段       |
| 8  | 统计方法与 IV/DV 匹配                         | Methodology.data_analysis_method；Outcome.primary_outcome_variables / independent_variables_and_factors / unit_of_analysis |
| 9  | 统计假设、检验方法与效应大小                  | Outcome.statistical_significance / effect_size_summary；Study Quality and Reporting.assumption_check_and_data_diagnostics / data_preprocessing_and_transformation |
| 10 | 异常值处理 + 结果解释 + 理论整合              | Study Quality and Reporting.outlier_treatment_and_sensitivity_analysis；Outcome.limitation / challenge / implication；Methodology.theoretical_foundation |

---

## 字段命名说明

为便于阅读，本说明中的字段采用以下表示方式：

- `Basic Identification.research_aims`  
  表示：在 `Basic Identification` 模块下的 `research_aims` 字段。
- `Methodology.research_design`  
  表示：在 `Methodology` 模块下的 `research_design` 字段。

在 `data_extraction_table.xlsx` 中，建议使用类似 `BasicIdentification_research_aims` 这样的扁平化列名，以便与代码处理兼容。

---

## 1. 研究目的清晰 + 理论/实践创新性

**Standard**

清晰界定研究目的与问题，并在理论框架与实践背景中呈现创新性或知识空白。

**Mapped fields**

- `Basic Identification.research_aims`  
- `Basic Identification.research_gap_or_novelty`  
- `Methodology.theoretical_foundation`

**Purpose & usage**

- `research_aims`：结构化记录**研究目标/问题是否被清晰陈述**。  
- `research_gap_or_novelty`：专门捕捉作者声称的**知识空白、创新点或贡献**。  
- `theoretical_foundation`：用于判断作者是否将研究置于**合理的理论脉络**下，而不是“经验之谈”。

> 结论：上述字段足以支撑质量标准 1 的评估（清晰度 + 理论/实践创新性）。

---

## 2. 参与者信息 + 关键背景变量（语言水平、母语等）

**Standard**

参与者基本信息及语言相关背景变量说明充分。

**Mapped fields**

- `Participant Information.educational_level`  
- `Participant Information.language_proficiency`  
- `Participant Information.mother_tongue`  
- `Participant Information.learning_context`  
- `Participant Information.target_language`  
- `Participant Information.discipline`  
- `Participant Information.sex`  
- `Participant Information.age`

**Purpose & usage**

- 这些字段细致地刻画了：**谁**（年龄、性别、教育阶段）、在**什么语境**（EFL/ESL/ELL/EMI）、用**什么母语**，学习**什么目标语言**以及**学科背景**。  
- 你可以据此判断：
  - 样本是否真的是 L2 英语写作者；  
  - 是否与 “LLM 赋能英语写作干预” 的综述主题契合；  
  - 研究是否报告了足够的背景变量来支持外推与亚组分析。

> 结论：上述字段可以完整覆盖质量标准 2。

---

## 3. 抽样方法 + 样本量 + 功效分析 + 代表性

**Standard**

抽样方法、样本量与功效分析清晰，样本具有一定代表性或可解释的局限。

**Mapped fields**

- `Methodology.sampling_method`  
- `Methodology.sample_size_and_effect`  
- `Methodology.power_analysis`  
- `Methodology.sampling_frame_and_representativeness`

**Purpose & usage**

- `sampling_method`：描述抽样方式（便利抽样、随机抽样、整群抽样、自愿报名等）。  
- `sample_size_and_effect`：记录样本量、组别人数，以及是否报告效应量（如 d、η²、r、OR 等）。  
- `power_analysis`：记录研究是否进行功效分析（power analysis）或样本量合理性说明。  
- `sampling_frame_and_representativeness`：记录样本框架及其代表性讨论（例如某校某专业是否可外推）。

> 结论：这四个字段是对质量标准 3 的“正面设计”，支持力度非常充分。

---

## 4. 实验–对照分配方式及潜在偏倚

**Standard**

实验/对照分配（随机/非随机）清晰，并对适用性和风险偏倚进行说明。

**Mapped fields**

- `Methodology.group_assignment_method`  
- `Study Quality and Reporting.risk_of_bias_randomization`  
- `Study Quality and Reporting.baseline_equivalence`

**Purpose & usage**

- `group_assignment_method`：记录**实验组/对照组如何形成**（随机、按班级、按成绩分层等）。  
- `risk_of_bias_randomization`：用于**评估分配与隐藏分配的偏倚风险**。  
- `baseline_equivalence`：记录是否报告组间基线可比性（前测成绩、关键背景变量）。

> 结论：这三类字段分别覆盖了方法、偏倚、基线可比性三个支柱，足以支撑标准 4。

---

## 5. 纵向比较，短期与长期效应

**Standard**

设计上有随时间的比较，关注短期变化与长期变化（如后测 + 延迟后测）。

**Mapped fields**

- `Methodology.research_design`  
- `Intervention.duration`  
- `Outcome.assessment_timepoints`  
- `Outcome.followup_length_and_type`

**Purpose & usage**

- `research_design`：区分横断 vs 纵向、前后测 vs 重复测量、是否有多时间点。  
- `duration`：记录干预总时长与频率（是否足以观察变化）。  
- `assessment_timepoints`：明确前测/后测/延迟后测等评价时间点。  
- `followup_length_and_type`：记录随访时长与类型，为“长期效果”提供证据。

> 结论：上述字段能帮助你判断研究是否严肃地考察了短期与长期效应，满足标准 5。

---

## 6. 工具信度与效度（含对特定语言群体的适用性）

**Standard**

数据收集工具的信度、效度及针对 L2 群体的适用性说明充分。

**Mapped fields**

- `Methodology.data_collection_instrument`  
- `Methodology.data_collection_validity_reliability`  
- `Methodology.scoring_procedure_and_rater_training`

**Purpose & usage**

- `data_collection_instrument`：记录使用了哪些测量工具（写作任务、量表、访谈等）。  
- `data_collection_validity_reliability`：记录工具的信度、效度及其对当前 L2 群体的适用性（Cronbach’s α、结构效度等）。  
- `scoring_procedure_and_rater_training`：尤其针对写作评分，记录评分流程、评分者训练、评分者一致性。

> 结论：这三组字段可充分支撑质量标准 6（测量可靠、可解释、适用于 L2 群体）。

---

## 7. 实验步骤和干预时长的可操作性

**Standard**

实验/教学干预的步骤与时长说明充分，具有可操作性与可复现性。

**Mapped fields**

- `Intervention.duration`  
- `Intervention.intervention_implementation`  
- `Intervention.writing_stage`  
- `Intervention.setting`  
- 以及所有与 LLM 直接相关的字段，例如：  
  - `Intervention.llm_model_type`  
  - `Intervention.llm_model_configuration`  
  - `Intervention.llm_integration_mode`  
  - `Intervention.prompting_strategy`  
  - `Intervention.training_support_llm_literacy`  
  - `Intervention.role_llm`  
  - `Intervention.role_instructor`  
  - `Intervention.llm_access_policy`  
  - `Intervention.llm_safety_guardrails`

**Purpose & usage**

- 这组字段让你可以重构出：  
  - 干预持续多长时间、多频次；  
  - 在哪种课程/学校/环境中实施；  
  - LLM 如何嵌入写作流程（在哪个写作阶段介入，谁来操作）。  
- 读者是否能据此在**另一所学校/另一个班级复现实验**，与这一标准高度相关。

> 结论：上述字段为复杂的 LLM 写作干预提供了足够的可操作性信息，满足质量标准 7。

---

## 8. 统计方法与自变量/因变量的匹配

**Standard**

采用恰当的统计方法评估主要自变量与因变量，且与研究问题和数据类型匹配。

**Mapped fields**

- `Methodology.data_analysis_method`  
- `Outcome.primary_outcome_variables`  
- `Outcome.independent_variables_and_factors`  
- `Methodology.unit_of_analysis`

**Purpose & usage**

- `data_analysis_method`：记录使用的统计方法（t 检验、ANOVA、回归、多层模型等）。  
- `primary_outcome_variables`：明确**主要因变量（DV）**是什么（整体写作分数、维度得分、情感量表等）。  
- `independent_variables_and_factors`：记录主要自变量/因子（组别、时间、水平、频次等）。  
- `unit_of_analysis`：判定数据层级（个体/班级/学校）与统计模型是否匹配。

> 结论：通过这些字段，你可以系统评估“分析方法是否匹配研究问题与数据结构”，完全满足标准 8。

---

## 9. 统计假设、检验方法与效应大小

**Standard**

说明数据是否满足统计假设，报告适当的检验方法与效应大小。

**Mapped fields**

- `Outcome.statistical_significance`  
- `Outcome.effect_size_summary`  
- `Study Quality and Reporting.assumption_check_and_data_diagnostics`  
- `Study Quality and Reporting.data_preprocessing_and_transformation`

**Purpose & usage**

- `statistical_significance`：概括主要结果的显著性（p 值、方向）。  
- `effect_size_summary`：记录是否报告效应量以及大小解释（小/中/大效应）。  
- `assumption_check_and_data_diagnostics`：记录是否检查正态性、方差齐性、球形性等统计前提。  
- `data_preprocessing_and_transformation`：记录数据预处理、转换（如对数变换、聚合）是否影响统计前提。

> 结论：这组字段比一般综述常用的质量框架更精细，达到高水平期刊要求，充分支撑标准 9。

---

## 10. 异常值处理、结果解释与理论整合

**Standard**

对数据与异常值进行合理处理和解释，分析其对结果的潜在影响，并在理论背景下进行整合性讨论。

**Mapped fields**

- `Study Quality and Reporting.outlier_treatment_and_sensitivity_analysis`  
- `Outcome.limitation`  
- `Outcome.challenge`  
- `Outcome.implication`  
- `Methodology.theoretical_foundation`（用于检查解释是否回扣理论）

**Purpose & usage**

- `outlier_treatment_and_sensitivity_analysis`：记录**极端值/异常值处理**及是否进行了稳健性分析或敏感性分析。  
- `limitation` / `challenge`：帮助评估作者是否诚实、深入地讨论研究局限和实施中的挑战。  
- `implication`：记录理论与教学实践层面的启示与建议。  
- 搭配 `theoretical_foundation` 可以判断结果解释是否真正**回到理论框架**，而不是仅停留在表层现象。

> 结论：上述字段完整覆盖了标准 10 中的“数据处理–结果解释–理论整合”三层要求。

---

## 使用建议（与质量评估表结合）

1. **在 `quality_assessment_table.xlsx` 中为每条质量标准预留：**
   - 一个评分字段（如 `Q1_rating`，0/1/2 或 Low/Medium/High）；  
   - 一个证据字段（如 `Q1_evidence`，可简要引用本说明中的字段内容和原文页码）。

2. **评分顺序建议：**
   - 按本 README 的 1–10 顺序逐条评估；  
   - 每条质量标准的评分，都应能在 `data_extraction_table.xlsx` 中找到对应字段支撑。

3. **团队协作建议：**
   - 可将本说明作为评审培训材料；  
   - 评审过程中如遇字段不足以支撑某一质量判断，可在 `quality_assessment_table.xlsx` 中添加 `Qx_notes` 记录具体问题，便于后续迭代数据提取表。

---

> 如需英文版或双语版映射说明，可以在本 README 基础上新增 “EN Version” 部分，采用相同结构，便于与国际合作者共享。
