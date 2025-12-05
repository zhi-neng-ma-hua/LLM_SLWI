<!-- README_screening_tools_en.md -->

# Double-blind / Triple-blind Screening Utility Scripts

This document describes utility scripts related to the double-blind / triple-blind screening workflow in this project, organized by screening stage (initial vs. second-stage) to support clear structure and future extension.

---

## Initial Screening Stage (Title / Abstract Double-blind)

During the **initial title/abstract double-blind screening stage**, the four currently implemented Python scripts handle unified processing and summarization of screening results, including batch merging, consistency checks, decision distributions, and final include/exclude statistics after triple adjudication.  

All PDFs associated with the initial screening stage are stored under:  `data/systematic_review/double_blind/stage1_title_abstract/pdfs/`

- **`merge_double_blind_batches.py`**
  
  Merges batch-level double-blind screening CSV files for R1 and R2 into single per-round result files, normalizes the `Notes` column to JSON where possible, and regenerates a globally consistent `No.` index.

- **`double_blind_consistency.py`**
  
  Aligns R1 and R2 results by `Title + Year`, checks the consistency of both `Decision` and `No.`, and exports an R1–R2 merged table with `Need_R3` flags together with a textual consistency report.

- **`double_blind_summary.py`**
  
  Summarizes the `Decision` distribution for R1 and R2 separately, and for all records with `Decision != "exclude"` lists their `No.` values grouped by `Decision`, supporting manual review and quality control in the initial screening stage.

- **`triple_blind_consistency.py`**
  
  Uses the three-round (R1/R2/R3) initial screening results to summarize `R3_Decision` distributions and restriction-related `R3_Notes` (e.g. access, payment, language constraints) when `Need_R3 = "yes"`, and to compute final included/excluded study counts with the corresponding `No.` lists.

---

## Second Screening Stage (Full-text Double-blind)

Scripts for the **second-stage (full-text) double-blind screening** are not yet covered in this document.  

All PDFs associated with the second-stage (full-text) screening are intended to be stored under:  `data/systematic_review/double_blind/stage2_full_text/pdfs/`  

Once Python tools for the full-text stage are added, this section can be extended with their roles and usage, mirroring the structure used for the initial screening stage.
