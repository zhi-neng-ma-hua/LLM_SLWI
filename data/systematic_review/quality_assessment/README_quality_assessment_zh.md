# 质量评估字段映射说明（Stage 2 Full-text）

本说明文档用于阐明：如何基于 `data_extraction_table.xlsx` 中的字段，对纳入研究进行 10 条质量标准的系统化评估。每条标准均给出：

- 标准定义（Standard）
- 对应字段（Mapped fields）
- 字段作用与评估逻辑（Purpose & usage）

---

## 1. 研究目的清晰 + 理论/实践创新性

**Standard**

清晰界定研究目的与问题，并在理论框架与实践背景中呈现创新性或知识空白。

**Mapped fields**

- `Basic Identification.research_aims`
- `Basic Identification.research_gap_or_novelty`
- `Methodology.theoretical_foundation`

**Purpose & usage**

- `research_aims`：结构化记录“研究问题/目的是否清晰”；
- `research_gap_or_novelty`：专门捕捉“知识空白/创新点”；
- `theoretical_foundation`：判断作者是否将研究放在合理理论脉络中。

> 结论：上述字段足以支持质量标准 1。

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

- 上述字段细致刻画“谁在学什么样的 L2、处于什么教育阶段、什么学习语境”；
- 足以判断样本是否与“L2 英语写作 + LLM 干预”主题契合。

> 结论：完全覆盖质量标准 2。

---

## 3. 抽样方法 + 样本量 + 功效分析 + 代表性

**Standard**

抽样方法、样本量与功效分析清晰，样本具有代表性。

**Mapped fields**

- `Methodology.sampling_method`
- `Methodology.sample_size_and_effect`
- `Methodology.power_analysis`
- `Methodology.sampling_frame_and_representativeness`

**Purpose & usage**

- `sampling_method`：记录抽样方式；
- `sample_size_and_effect`：记录样本量及是否报告效应量；
- `power_analysis`：记录是否做功效分析；
- `sampling_frame_and_representativeness`：记录样本框架与代表性讨论。

> 结论：四个字段正面对应质量标准 3，支持度已达“院士级”粒度。

---

## 4. 实验–对照分配方式及潜在偏倚

**Standard**

实验/对照分配（随机/非随机）清晰，且解释适用性和偏倚。

**Mapped fields**

- `Methodology.group_assignment_method`
- `Study Quality and Reporting.risk_of_bias_randomization`
- `Study Quality and Reporting.baseline_equivalence`

**Purpose & usage**

- `group_assignment_method`：记录“如何分组”（随机/非随机、按班级/水平等）；
- `risk_of_bias_randomization`：评估分配与隐藏分配的偏倚风险；
- `baseline_equivalence`：判断组间基线是否可比。

> 结论：直接支撑标准 4 的三个关键点：方法、偏倚、基线可比性。

---

## 5. 纵向比较，短期与长期效应

**Standard**

设计上有随时间的比较，关注短期与长期变化。

**Mapped fields**

- `Methodology.research_design`
- `Intervention.duration`
- `Outcome.assessment_timepoints`
- `Outcome.followup_length_and_type`

**Purpose & usage**

- 区分横断 vs 纵向设计；
- 判断是否存在延迟后测/随访；
- 评估随访时长是否足以支持“长期效果”的判断。

> 结论：可用于评估研究在时间维度上的质量，满足标准 5。

---

（后续对 6–10 条按完全相同的结构整理即可）
