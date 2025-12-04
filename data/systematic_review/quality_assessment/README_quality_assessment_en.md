# Field Mapping Guide for Quality Assessment (Stage 2 Full-text, L2 Writing with LLM Intervention)

This document explains how to use fields in `data_extraction_table.xlsx` to operationalize **10 quality standards** for studies included in the Stage 2 full-text screening.

For each quality standard, we provide:

- **Standard** – What the criterion means  
- **Mapped fields** – Which data extraction fields support this criterion  
- **Purpose & usage** – How to use these fields when rating study quality

This guide is designed to be used together with `quality_assessment_table.xlsx` for:

- Guiding quality scoring and evidence documentation  
- Training new reviewers  
- Providing an auditable trail for quality assessment decisions

---

## Table of Contents

1. [Clarity of Research Aims & Theoretical/Practical Novelty](#1-clarity-of-research-aims--theoreticalpractical-novelty)  
2. [Participant Information & Key Background Variables](#2-participant-information--key-background-variables)  
3. [Sampling Method, Sample Size, Power, and Representativeness](#3-sampling-method-sample-size-power-and-representativeness)  
4. [Group Assignment and Potential Bias](#4-group-assignment-and-potential-bias)  
5. [Temporal Design: Short- and Long-term Effects](#5-temporal-design-short--and-long-term-effects)  
6. [Instrument Reliability, Validity, and L2 Applicability](#6-instrument-reliability-validity-and-l2-applicability)  
7. [Intervention Procedures, Duration, and Replicability](#7-intervention-procedures-duration-and-replicability)  
8. [Alignment Between Statistical Methods and IV/DV](#8-alignment-between-statistical-methods-and-ivdv)  
9. [Statistical Assumptions, Tests, and Effect Sizes](#9-statistical-assumptions-tests-and-effect-sizes)  
10. [Outlier Handling, Result Interpretation, and Theoretical Integration](#10-outlier-handling-result-interpretation-and-theoretical-integration)  

---

## Global Overview: Quality Standards and Field Mapping

A quick reference to see which extracted fields support each quality standard.

| #  | Quality standard (summary)                                      | Key mapped fields (examples)                                                                                                      |
|----|------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| 1  | Clarity of aims & theoretical/practical novelty                  | Basic Identification.research_aims / research_gap_or_novelty; Methodology.theoretical_foundation                                 |
| 2  | Participant information & language background                    | Participant Information.educational_level / language_proficiency / mother_tongue / learning_context / target_language / discipline / sex / age |
| 3  | Sampling method, sample size, power, representativeness          | Methodology.sampling_method / sample_size_and_effect / power_analysis / sampling_frame_and_representativeness                    |
| 4  | Group assignment and potential bias                              | Methodology.group_assignment_method; Study Quality and Reporting.risk_of_bias_randomization / baseline_equivalence               |
| 5  | Temporal design and short-/long-term effects                     | Methodology.research_design; Intervention.duration; Outcome.assessment_timepoints / followup_length_and_type                     |
| 6  | Instrument reliability/validity & rater training                 | Methodology.data_collection_instrument / data_collection_validity_reliability / scoring_procedure_and_rater_training            |
| 7  | Intervention procedures, duration, and replicability             | Intervention.duration / intervention_implementation / writing_stage / setting / llm_* fields                                     |
| 8  | Alignment between statistical methods and IV/DV                  | Methodology.data_analysis_method; Outcome.primary_outcome_variables / independent_variables_and_factors; Methodology.unit_of_analysis |
| 9  | Statistical assumptions, tests, and effect sizes                 | Outcome.statistical_significance / effect_size_summary; Study Quality and Reporting.assumption_check_and_data_diagnostics / data_preprocessing_and_transformation |
| 10 | Outlier handling, result interpretation, and theoretical integration | Study Quality and Reporting.outlier_treatment_and_sensitivity_analysis; Outcome.limitation / challenge / implication; Methodology.theoretical_foundation |

---

## Field Naming Notes

- `Basic Identification.research_aims` means the `research_aims` field under the **Basic Identification** module.  
- `Methodology.research_design` means the `research_design` field under the **Methodology** module.

In `data_extraction_table.xlsx`, we recommend using flattened column names such as:

- `BasicIdentification_research_aims`  
- `Methodology_research_design`  

This makes it easier to process the table programmatically (e.g., with Python or R).

---

## 1. Clarity of Research Aims & Theoretical/Practical Novelty

**Standard**

The study clearly states its research aims and questions and situates them within a theoretical and/or practical context, highlighting novelty or a clear knowledge gap.

**Mapped fields**

- `Basic Identification.research_aims`  
- `Basic Identification.research_gap_or_novelty`  
- `Methodology.theoretical_foundation`

**Purpose & usage**

- `research_aims`: Captures whether the research aims/questions are **clearly and specifically articulated**, rather than vague or generic.  
- `research_gap_or_novelty`: Captures the **claimed knowledge gap or innovation**, e.g., what is new compared to traditional feedback or prior LLM studies.  
- `theoretical_foundation`: Indicates whether the study is grounded in a **coherent theoretical framework** (e.g., sociocultural theory, process writing theory), instead of being theory-free.

> If these fields are well populated and coherent, you can justify a high rating for Quality Standard 1.

---

## 2. Participant Information & Key Background Variables

**Standard**

Participant characteristics and language-related background variables are reported in sufficient detail.

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

These fields should allow you to reconstruct:

- **Who** the learners are (age, sex, educational level)  
- **Which L2** they are learning (here, primarily English)  
- **In what context** they are learning (EFL, ESL, ELL, EMI, etc.)  
- **What discipline** they are studying (e.g., English major, engineering, education)

Use them to assess:

- Whether the sample is truly about **L2 English writing** with LLM mediation  
- Whether the study provides enough background to interpret generalizability and subgroup differences

> If these fields are complete and consistent, the study meets Quality Standard 2.

---

## 3. Sampling Method, Sample Size, Power, and Representativeness

**Standard**

Sampling procedures, sample size, and power analysis are reported clearly, and sample representativeness is discussed.

**Mapped fields**

- `Methodology.sampling_method`  
- `Methodology.sample_size_and_effect`  
- `Methodology.power_analysis`  
- `Methodology.sampling_frame_and_representativeness`

**Purpose & usage**

- `sampling_method`: Documents how participants were recruited (convenience, random, cluster, voluntary sign-up, etc.).  
- `sample_size_and_effect`: Records total N, group Ns, and whether **effect sizes** (e.g., Cohen’s d, η², r, OR) are reported.  
- `power_analysis`: Indicates whether any **power analysis / sample size justification** is provided.  
- `sampling_frame_and_representativeness`: Captures whether the study discusses how representative the sample is (e.g., one university, one class, regional bias).

> Together, these fields directly operationalize Quality Standard 3.

---

## 4. Group Assignment and Potential Bias

**Standard**

The allocation of participants to experimental/control conditions (random or non-random) is clearly described, and potential bias is considered.

**Mapped fields**

- `Methodology.group_assignment_method`  
- `Study Quality and Reporting.risk_of_bias_randomization`  
- `Study Quality and Reporting.baseline_equivalence`

**Purpose & usage**

- `group_assignment_method`: Records **how groups were formed** (true randomization, quasi-experimental grouping, pre-existing classes, etc.).  
- `risk_of_bias_randomization`: Assesses the **risk of bias in allocation and allocation concealment**.  
- `baseline_equivalence`: Indicates whether baseline comparability (e.g., pre-test scores, key covariates) between groups is reported.

> These fields collectively support evaluation of methods, bias, and baseline comparability for Quality Standard 4.

---

## 5. Temporal Design: Short- and Long-term Effects

**Standard**

The study design captures temporal change and distinguishes short-term and, where appropriate, long-term effects.

**Mapped fields**

- `Methodology.research_design`  
- `Intervention.duration`  
- `Outcome.assessment_timepoints`  
- `Outcome.followup_length_and_type`

**Purpose & usage**

- `research_design`: Distinguishes cross-sectional vs. longitudinal, pre-post vs. repeated measures designs.  
- `duration`: Describes overall intervention length and frequency (e.g., 8 weeks, 2 sessions/week).  
- `assessment_timepoints`: Specifies when assessments took place (pre-test, immediate post-test, delayed post-test).  
- `followup_length_and_type`: Records the follow-up interval and outcome type, supporting claims about **long-term impact**.

> Use these fields to assess whether the study meaningfully addresses temporal change and meets Quality Standard 5.

---

## 6. Instrument Reliability, Validity, and L2 Applicability

**Standard**

Measurement instruments are accompanied by reliability and validity evidence, with consideration of their appropriateness for the L2 population.

**Mapped fields**

- `Methodology.data_collection_instrument`  
- `Methodology.data_collection_validity_reliability`  
- `Methodology.scoring_procedure_and_rater_training`

**Purpose & usage**

- `data_collection_instrument`: Lists the main measurement tools (writing tasks, scales, interviews, logs, automated tools, etc.).  
- `data_collection_validity_reliability`: Records evidence on reliability and validity (Cronbach’s α, factor structure, test–retest, etc.), especially for L2 learners.  
- `scoring_procedure_and_rater_training`: Captures how writing was scored, whether raters were trained, and rater agreement indices (e.g., inter-rater reliability).

> Together, these fields support a robust evaluation of measurement quality under Standard 6.

---

## 7. Intervention Procedures, Duration, and Replicability

**Standard**

The intervention procedures and dosage (duration, frequency) are described with sufficient detail to allow replication.

**Mapped fields**

- `Intervention.duration`  
- `Intervention.intervention_implementation`  
- `Intervention.writing_stage`  
- `Intervention.setting`  
- LLM-specific fields, e.g.:  
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

- these fields together allow you to reconstruct:
  - **how long** the intervention ran (weeks, sessions, minutes/session);  
  - **what exactly happened** in the classroom or online (tasks, steps, supports);  
  - **how LLMs were used** (by students directly, mediated by instructors, or embedded in platforms);  
  - the **writing stage(s)** where LLMs intervened (planning, drafting, revising, feedback interpretation, etc.).

> If another instructor at a different institution could reasonably reproduce the intervention using these fields, the study meets Standard 7.

---

## 8. Alignment Between Statistical Methods and IV/DV

**Standard**

The statistical methods used are appropriate for the independent and dependent variables and match the research questions and data structure.

**Mapped fields**

- `Methodology.data_analysis_method`  
- `Outcome.primary_outcome_variables`  
- `Outcome.independent_variables_and_factors`  
- `Methodology.unit_of_analysis`

**Purpose & usage**

- `data_analysis_method`: Records the statistical techniques used (t-tests, ANOVA/ANCOVA, regression, MLM, SEM, content/ thematic analysis, etc.).  
- `primary_outcome_variables`: Identifies the **main dependent variables (DVs)** (e.g., overall writing score, fluency, anxiety scale score).  
- `independent_variables_and_factors`: Identifies the **key independent variables (IVs)/factors** (e.g., group, time, proficiency level, LLM usage frequency).  
- `unit_of_analysis`: Clarifies whether the analysis was conducted at the learner, text, class, or school level and whether this matches the statistical model.

> These fields allow you to judge whether the methods are technically and conceptually aligned with the study design (Standard 8).

---

## 9. Statistical Assumptions, Tests, and Effect Sizes

**Standard**

The study addresses statistical assumptions, reports appropriate tests, and provides effect sizes where relevant.

**Mapped fields**

- `Outcome.statistical_significance`  
- `Outcome.effect_size_summary`  
- `Study Quality and Reporting.assumption_check_and_data_diagnostics`  
- `Study Quality and Reporting.data_preprocessing_and_transformation`

**Purpose & usage**

- `statistical_significance`: Summarizes main results (p-values, direction of effects).  
- `effect_size_summary`: Records whether effect sizes (e.g., Cohen’s d, η², r) are reported and how large they are (small/medium/large).  
- `assumption_check_and_data_diagnostics`: Indicates whether assumptions (normality, homogeneity, sphericity, etc.) were checked and reported.  
- `data_preprocessing_and_transformation`: Captures any data preprocessing (e.g., log transformations, aggregation) that could affect statistical assumptions.

> The combination of these fields supports a high-level, journal-grade evaluation of Standard 9.

---

## 10. Outlier Handling, Result Interpretation, and Theoretical Integration

**Standard**

Outliers and extreme values are handled transparently, their impact on findings is considered, and results are interpreted in light of the theoretical framework.

**Mapped fields**

- `Study Quality and Reporting.outlier_treatment_and_sensitivity_analysis`  
- `Outcome.limitation`  
- `Outcome.challenge`  
- `Outcome.implication`  
- `Methodology.theoretical_foundation` (for checking whether interpretations link back to theory)

**Purpose & usage**

- `outlier_treatment_and_sensitivity_analysis`: Documents how outliers/extreme values were handled and whether any robustness/sensitivity analyses were conducted.  
- `limitation`: Captures the study’s self-acknowledged limitations (design, sample, measures, duration, LLM version, etc.).  
- `challenge`: Captures practical challenges and risks encountered during implementation (e.g., technical stability, student over-reliance, ethical concerns).  
- `implication`: Records theoretical and pedagogical implications proposed by the authors.  
- `theoretical_foundation`: Used here to verify whether interpretations meaningfully **connect back to theory** instead of staying purely descriptive.

> Use these fields to judge whether the study treats data responsibly and interprets results in a theoretically informed way, as required by Standard 10.

---

## Practical Tips for Using This Mapping with `quality_assessment_table.xlsx`

1. **One quality standard → at least two columns in the QA table**
   - e.g. `Q1_clarity_novelty_rating` (e.g., 0/1/2 or Low/Medium/High)  
   - and `Q1_clarity_novelty_evidence` (brief notes referencing the relevant fields and, optionally, page numbers).

2. **Recommended workflow**
   - Read the full text with `data_extraction_table.xlsx` and this mapping at hand.  
   - For each quality standard (1–10), check the **Mapped fields** and fill in both rating and evidence in `quality_assessment_table.xlsx`.  
   - If you find that a decision cannot be supported by existing fields, note this in the evidence/comment cell for that standard.

3. **Team use**
   - This mapping can be used to train new reviewers to ensure **consistent interpretation** of the quality standards.  
   - It also allows external collaborators or reviewers to trace each quality rating back to specific, structured data fields.

---
