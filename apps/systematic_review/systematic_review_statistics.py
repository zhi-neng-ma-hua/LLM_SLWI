# -*- coding: utf-8 -*-
"""
systematic_review_statistics.py

Purpose
-------
Summarise key data files across all stages of the systematic review and print
the results to the console while also writing a structured plain-text report.

Scope
-----
1. Raw search and deduplication
   data/systematic_review/raw

2. Stage 1 – Title / abstract double-blind screening
   data/systematic_review/double_blind/stage1_title_abstract

3. Stage 2 – Full-text double-blind screening
   data/systematic_review/double_blind/stage2_full_text

4. Quality assessment
   data/systematic_review/quality_assessment/quality_assessment_table.xlsx

Output
------
data/systematic_review/systematic_review_statistics_summary.txt

Author: Aiden Cao <zhinengmahua@gmail.com>
Date  : 2025-12-06
"""

import json
import logging
from pathlib import Path
from typing import Callable, List, Optional

import pandas as pd

from utils.logger_manager import LoggerManager
from utils.data_io import load_table
from utils.exceptions import DataValidationError


# ============================== logging config ============================== #


def setup_logger(name: str = "systematic_review_statistics", verbose: bool = True) -> logging.Logger:
    """
    Initialise and return a configured logger.

    :param name: Logger name.
    :param verbose: If True, enable DEBUG; otherwise INFO.
    :return: Configured logging.Logger instance.
    """
    return LoggerManager.setup_logger(
        logger_name=name,
        module_name=__name__,
        verbose=verbose,
    )


# ============================== report builder ============================== #


class ReportBuilder:
    """
    Helper to accumulate plain-text report lines and write them to disk.
    """

    def __init__(self) -> None:
        """
        Initialise the report builder with an empty line buffer.
        """
        self._lines: List[str] = []

    def add_line(self, text: str = "") -> None:
        """
        Append a single line to the report and print it to stdout.

        :param text: Text content of the line.
        """
        print(text)
        self._lines.append(text)

    def write_to(self, path: Path) -> None:
        """
        Write all accumulated lines to the specified file path.

        :param path: Output file path for the report.
        """
        path.write_text("\n".join(self._lines), encoding="utf-8")


# ============================== helper functions ============================== #


def format_value_counts(series: pd.Series) -> List[str]:
    """
    Format the value_counts of a Series as a list of human-readable lines.

    :param series: Series to be summarised.
    :return: List of lines, each describing a value and its count.
    """
    lines: List[str] = []
    if series is None or series.empty:
        lines.append("(no data)")
        return lines

    vc = series.value_counts(dropna=False)
    for value, count in vc.items():
        lines.append(f"{repr(value)}: {count}")
    return lines


def value_counts_as_json(series: pd.Series) -> str:
    """
    Convert Series.value_counts() into a JSON string with 4-space indentation.

    Conventions:
    - NaN / <NA> are represented as the key "<NA>".
    - All other values are converted via str(value).

    :param series: Series to be summarised.
    :return: JSON string (ensure_ascii=False, indent=4).
    """
    if series is None or series.empty:
        stats = {"<EMPTY>": 0}
        return json.dumps(stats, ensure_ascii=False, indent=4)

    vc = series.value_counts(dropna=False)

    def _key(val: object) -> str:
        if pd.isna(val):
            return "<NA>"
        return str(val)

    stats = {_key(idx): int(cnt) for idx, cnt in vc.items()}
    return json.dumps(stats, ensure_ascii=False, indent=4)


def load_excel(path: Path, logger: Optional[logging.Logger] = None) -> pd.DataFrame:
    """
    Wrapper to load Excel / table files with unified error handling.

    :param path: File path to load.
    :param logger: Optional logger for load diagnostics.
    :return: Loaded DataFrame.
    :raises DataValidationError: If loading fails.
    """
    try:
        df = load_table(path, logger=logger)
        return df
    except Exception as exc:
        raise DataValidationError(f"Failed to read file: {path} | Error: {exc}")


# ============================== raw data statistics ============================== #


class RawDataStatistics:
    """
    Statistics for raw search results and merged / deduplicated data.

    Directory:
    - data/systematic_review/raw
    """

    def __init__(self, raw_root: Path, add_line: Callable[[str], None], logger: logging.Logger) -> None:
        """
        Initialise the raw data statistics collector.

        :param raw_root: Root directory for raw data (data/systematic_review/raw).
        :param add_line: Callback that appends lines to the report.
        :param logger: Logger instance.
        """
        self.raw_root = raw_root
        self.add_line = add_line
        self.logger = logger

    def _section_title(self, title: str) -> None:
        """
        Print and record a first-level section title.

        :param title: Section title text.
        """
        self.add_line("")
        self.add_line("=" * 80)
        self.add_line(title)
        self.add_line("=" * 80)

    def _subsection_title(self, title: str) -> None:
        """
        Print and record a second-level subsection title.

        :param title: Subsection title text.
        """
        self.add_line("")
        self.add_line(f"[{title}]")

    def run(self) -> None:
        """
        Execute raw search and deduplication statistics.
        """
        self._section_title("I. Raw search results and deduplication")
        self._stats_per_database()
        self._stats_merged_deduplicated()

    def _stats_per_database(self) -> None:
        """
        Count the number of raw records per source database.
        """
        self._subsection_title("1.1 Record counts per database")

        files = {
            "ERIC": self.raw_root / "eric.xlsx",
            "IEEE Xplore": self.raw_root / "ieee_xplore.xlsx",
            "Scopus": self.raw_root / "scopus.xlsx",
            "Web of Science": self.raw_root / "web_of_science.xlsx",
        }

        total = 0
        for name, path in files.items():
            df = load_excel(path, logger=self.logger)
            n = len(df)
            total += n
            self.add_line(f"- {name:<15}: {n:>6} records")

        self.add_line(f"- {'Total':<15}: {total:>6} records")

    def _stats_merged_deduplicated(self) -> None:
        """
        Count the number of records in merged_and_deduplicated_data.xlsx.
        """
        self._subsection_title("1.2 Record count after merge + deduplication")
        merged_path = self.raw_root / "merged_and_deduplicated_data.xlsx"
        df_merged = load_excel(merged_path, logger=self.logger)
        self.add_line(f"- merged_and_deduplicated_data.xlsx: {len(df_merged)} records")


# ============================== stage 1: title / abstract screening ============================== #


class Stage1ScreeningStatistics:
    """
    Stage 1: title / abstract double-blind screening statistics.

    File:
    - data/systematic_review/double_blind/stage1_title_abstract/R1_R2_R3_analysis_results.xlsx
    """

    def __init__(self, stage1_root: Path, add_line: Callable[[str], None], logger: logging.Logger) -> None:
        """
        Initialise Stage 1 screening statistics.

        :param stage1_root: Directory for Stage 1 results (stage1_title_abstract).
        :param add_line: Callback to append lines to the report.
        :param logger: Logger instance.
        """
        self.stage1_root = stage1_root
        self.add_line = add_line
        self.logger = logger

    def _section_title(self, title: str) -> None:
        """
        Print and record a first-level section title.

        :param title: Section title text.
        """
        self.add_line("")
        self.add_line("=" * 80)
        self.add_line(title)
        self.add_line("=" * 80)

    def _subsection_title(self, title: str) -> None:
        """
        Print and record a second-level subsection title.

        :param title: Subsection title text.
        """
        self.add_line("")
        self.add_line(f"[{title}]")

    def run(self) -> None:
        """
        Execute Stage 1 (title / abstract) screening statistics.
        """
        self._section_title("II. Stage 1 double-blind screening (title / abstract)")

        path = self.stage1_root / "R1_R2_R3_analysis_results.xlsx"
        df = load_excel(path, logger=self.logger)

        self._basic_stats(path, df)
        self._agreement_and_r3(df)
        self._final_include_exclude(df)

    def _basic_stats(self, path: Path, df: pd.DataFrame) -> None:
        """
        Summarise file-level record count and decision distributions (JSON).

        :param path: Stage 1 result file path.
        :param df: Loaded DataFrame.
        """
        self._subsection_title("2.1 Record count and decision distributions")

        self.add_line(f"- File name : {path.name}")
        self.add_line(f"- Total rows: {len(df)}")

        # R1/R2 decision distributions (JSON)
        for col in ["R1_Decision", "R2_Decision"]:
            if col in df.columns:
                self.add_line(f"\n{col} value distribution (JSON):")
                self.add_line(value_counts_as_json(df[col]))
            else:
                self.add_line(f"\nColumn {col} is missing.")

        # Need_R3 distribution (JSON)
        if "Need_R3" in df.columns:
            self.add_line("\nNeed_R3 value distribution (JSON):")
            self.add_line(value_counts_as_json(df["Need_R3"]))
        else:
            self.add_line("\nColumn Need_R3 is missing.")

        # R3_Decision distribution (JSON)
        if "R3_Decision" in df.columns:
            self.add_line("\nR3_Decision value distribution (JSON):")
            self.add_line(value_counts_as_json(df["R3_Decision"]))
        else:
            self.add_line("\nColumn R3_Decision is missing.")

    def _agreement_and_r3(self, df: pd.DataFrame) -> None:
        """
        Summarise R1/R2 agreement patterns and potential R3 involvement (JSON), with coverage check.

        :param df: Stage 1 result DataFrame.
        """
        self._subsection_title("2.2 R1/R2 agreement and R3 involvement")

        r1 = df.get("R1_Decision")
        r2 = df.get("R2_Decision")

        if r1 is None or r2 is None:
            self.add_line("Columns R1_Decision or R2_Decision are missing; cannot compute agreement / R3 involvement.")
            return

        both_include = (r1 == "include") & (r2 == "include")
        both_exclude = (r1 == "exclude") & (r2 == "exclude")
        both_unsure = (r1 == "unsure") & (r2 == "unsure")
        disagree = (r1 != r2)

        stats = {
            "R1_eq_R2_include": int(both_include.sum()),
            "R1_eq_R2_exclude": int(both_exclude.sum()),
            "R1_eq_R2_unsure": int(both_unsure.sum()),
            "R1_neq_R2": int(disagree.sum()),
        }

        self.add_line("- R1/R2 agreement patterns (JSON):")
        self.add_line(json.dumps(stats, ensure_ascii=False, indent=4))

        # Coverage check: rows not captured by any agreement pattern
        if "No." in df.columns:
            covered_mask = both_include | both_exclude | both_unsure | disagree
            uncovered_mask = ~covered_mask
            uncovered_count = int(uncovered_mask.sum())
            if uncovered_count > 0:
                missing_nos = df.loc[uncovered_mask, "No."].tolist()
                self.add_line(f"  · Warning: {uncovered_count} rows not covered by any agreement pattern, No.:")
                self.add_line(f"    {missing_nos}")

    def _final_include_exclude(self, df: pd.DataFrame) -> None:
        """
        Summarise final include / exclude status in Stage 1 based on R1/R2/R3_Decision.

        Final inclusion:
          1) R1 = R2 = 'include'
          2) R1 = R2 = 'unsure' and R3_Decision = 'include'
          3) R1 != R2           and R3_Decision = 'include'

        Final exclusion:
          1) R1 = R2 = 'exclude'
          2) R1 = R2 = 'unsure' and R3_Decision = 'exclude'
          3) R1 != R2           and R3_Decision = 'exclude'

        :param df: Stage 1 result DataFrame.
        """
        self._subsection_title("2.3 Final inclusion / exclusion at Stage 1 (based on R1/R2/R3_Decision)")

        r1 = df.get("R1_Decision")
        r2 = df.get("R2_Decision")
        r3 = df.get("R3_Decision")

        if r1 is None or r2 is None or r3 is None:
            self.add_line("Columns R1_Decision / R2_Decision / R3_Decision are missing; cannot compute final status.")
            return

        both_include = (r1 == "include") & (r2 == "include")
        both_exclude = (r1 == "exclude") & (r2 == "exclude")
        both_unsure = (r1 == "unsure") & (r2 == "unsure")
        disagree = (r1 != r2)

        include_direct = both_include
        include_unsure_r3 = both_unsure & (r3 == "include")
        include_disagree_r3 = disagree & (r3 == "include")
        final_include_mask = include_direct | include_unsure_r3 | include_disagree_r3

        exclude_direct = both_exclude
        exclude_unsure_r3 = both_unsure & (r3 == "exclude")
        exclude_disagree_r3 = disagree & (r3 == "exclude")
        final_exclude_mask = exclude_direct | exclude_unsure_r3 | exclude_disagree_r3

        self.add_line("Final inclusion at Stage 1 (by condition):")
        self.add_line(f"  · Cond 1: R1 = R2 = 'include'                             → {int(include_direct.sum())}")
        self.add_line(f"  · Cond 2: R1 = R2 = 'unsure' & R3 = 'include'           → {int(include_unsure_r3.sum())}")
        self.add_line(f"  · Cond 3: R1 != R2         & R3 = 'include'             → {int(include_disagree_r3.sum())}")
        self.add_line(f"  ⇒ Total final include: {int(final_include_mask.sum())}")

        self.add_line("\nFinal exclusion at Stage 1 (by condition):")
        self.add_line(f"  · Cond 1: R1 = R2 = 'exclude'                             → {int(exclude_direct.sum())}")
        self.add_line(f"  · Cond 2: R1 = R2 = 'unsure' & R3 = 'exclude'           → {int(exclude_unsure_r3.sum())}")
        self.add_line(f"  · Cond 3: R1 != R2         & R3 = 'exclude'             → {int(exclude_disagree_r3.sum())}")
        self.add_line(f"  ⇒ Total final exclude: {int(final_exclude_mask.sum())}")


# ============================== stage 2: full-text screening ============================== #


class Stage2ScreeningStatistics:
    """
    Stage 2: full-text double-blind screening statistics.

    File:
    - data/systematic_review/double_blind/stage2_full_text/R1_R2_R3_analysis_results.xlsx
    """

    def __init__(self, stage2_root: Path, add_line: Callable[[str], None], logger: logging.Logger) -> None:
        """
        Initialise Stage 2 screening statistics.

        :param stage2_root: Stage 2 directory (stage2_full_text).
        :param add_line: Callback to append lines to the report.
        :param logger: Logger instance.
        """
        self.stage2_root = stage2_root
        self.add_line = add_line
        self.logger = logger

    def _section_title(self, title: str) -> None:
        """
        Print and record a first-level section title.

        :param title: Section title text.
        """
        self.add_line("")
        self.add_line("=" * 80)
        self.add_line(title)
        self.add_line("=" * 80)

    def _subsection_title(self, title: str) -> None:
        """
        Print and record a second-level subsection title.

        :param title: Subsection title text.
        """
        self.add_line("")
        self.add_line(f"[{title}]")

    def run(self) -> None:
        """
        Execute Stage 2 (full-text) screening statistics.
        """
        self._section_title("III. Stage 2 double-blind screening (full text)")

        path = self.stage2_root / "R1_R2_R3_analysis_results.xlsx"
        df = load_excel(path, logger=self.logger)

        self._basic_stats(path, df)
        self._agreement_r3_and_remark(df)
        self._final_include_exclude(df)

    def _basic_stats(self, path: Path, df: pd.DataFrame) -> None:
        """
        Summarise Stage 2 file-level record count and decision distributions (JSON).

        :param path: Stage 2 result file path.
        :param df: Loaded DataFrame.
        """
        self._subsection_title("3.1 Record count and decision distributions")

        self.add_line(f"- File name : {path.name}")
        self.add_line(f"- Total rows: {len(df)}")

        # R1/R2 decision distributions (JSON)
        for col in ["R1_Decision", "R2_Decision"]:
            if col in df.columns:
                self.add_line(f"\n{col} value distribution (JSON):")
                self.add_line(value_counts_as_json(df[col]))
            else:
                self.add_line(f"\nColumn {col} is missing.")

        # R3_Decision distribution (JSON)
        r3 = df.get("R3_Decision")
        if r3 is not None:
            self.add_line("\nR3_Decision value distribution (JSON):")
            self.add_line(value_counts_as_json(r3))
        else:
            self.add_line("\nColumn R3_Decision is missing.")

    def _agreement_r3_and_remark(self, df: pd.DataFrame) -> None:
        """
        Summarise R1/R2 agreement patterns, R3 involvement, and Remark-related characteristics.

        Additional statistics when R1_Decision and R2_Decision are both empty (""):
        - Count of rows where Remark starts with 'Access restrictions';
        - Count of rows where Remark starts with 'Duplicate with';
        - Count of rows where Remark starts with 'Retracted'.

        Also:
        - Output R1/R2 agreement pattern counts as JSON (including the empty pattern);
        - If the total pattern count does not equal the number of rows, list uncovered No.;
        - Always output the list of No. where R1 != R2 for focused manual inspection.

        :param df: Stage 2 result DataFrame.
        """
        self._subsection_title("3.2 R1/R2 agreement, R3 involvement and Remark patterns")

        r1 = df.get("R1_Decision")
        r2 = df.get("R2_Decision")
        remark = df.get("Remark")

        # Agreement patterns and R3 involvement (JSON)
        if r1 is None or r2 is None:
            self.add_line("Columns R1_Decision or R2_Decision are missing; cannot compute agreement / R3 involvement.")
        else:
            both_include = (r1 == "include") & (r2 == "include")
            both_exclude = (r1 == "exclude") & (r2 == "exclude")
            both_unsure = (r1 == "unsure") & (r2 == "unsure")
            both_empty = (r1 == "") & (r2 == "")
            disagree = (r1 != r2)

            stats = {
                "R1_eq_R2_include": int(both_include.sum()),
                "R1_eq_R2_exclude": int(both_exclude.sum()),
                "R1_eq_R2_unsure": int(both_unsure.sum()),
                "R1_eq_R2_empty": int(both_empty.sum()),
                "R1_neq_R2": int(disagree.sum()),
            }

            self.add_line("- R1/R2 agreement patterns (JSON):")
            self.add_line(json.dumps(stats, ensure_ascii=False, indent=4))

            # Coverage check (include empty pattern)
            if "No." in df.columns:
                covered_mask = both_include | both_exclude | both_unsure | both_empty | disagree
                uncovered_mask = ~covered_mask
                uncovered_count = int(uncovered_mask.sum())
                if uncovered_count > 0:
                    missing_nos = df.loc[uncovered_mask, "No."].tolist()
                    self.add_line(f"  · Warning: {uncovered_count} rows not covered by any agreement pattern, No.:")
                    self.add_line(f"    {missing_nos}")

        # When both R1/R2 decisions are empty, count Remark prefixes
        if remark is not None and r1 is not None and r2 is not None:
            empty_both = (r1 == "") & (r2 == "")
            remark_str = remark.astype(str)

            access_prefix_mask = empty_both & remark_str.str.startswith("Access restrictions", na=False)
            duplicate_prefix_mask = empty_both & remark_str.str.startswith("Duplicate with", na=False)
            retracted_prefix_mask = empty_both & remark_str.str.startswith("Retracted", na=False)

            self.add_line("\n- Rows with R1_Decision and R2_Decision both empty, by Remark prefix:")
            self.add_line(f"  · Remark starting with 'Access restrictions': {int(access_prefix_mask.sum())}")
            self.add_line(f"  · Remark starting with 'Duplicate with'    : {int(duplicate_prefix_mask.sum())}")
            self.add_line(f"  · Remark starting with 'Retracted'         : {int(retracted_prefix_mask.sum())}")
        elif remark is None:
            self.add_line("Column Remark is missing; cannot summarise reasons for missing decisions.")

    def _final_include_exclude(self, df: pd.DataFrame) -> None:
        """
        Summarise final inclusion / exclusion at Stage 2 based on R1/R2/R3_Decision.

        Final inclusion:
          1) R1 = R2 = 'include'
          2) R1 = R2 = 'unsure' and R3_Decision = 'include'
          3) R1 != R2           and R3_Decision = 'include'

        Final exclusion:
          1) R1 = R2 = 'exclude'
          2) R1 = R2 = 'unsure' and R3_Decision = 'exclude'
          3) R1 != R2           and R3_Decision = 'exclude'
          4) R1 = R2 = ''       (not screened at full-text, treated as excluded)

        :param df: Stage 2 result DataFrame.
        """
        self._subsection_title("3.3 Final inclusion / exclusion at Stage 2 (based on R1/R2/R3_Decision)")

        r1 = df.get("R1_Decision")
        r2 = df.get("R2_Decision")
        r3 = df.get("R3_Decision")

        if r1 is None or r2 is None or r3 is None:
            self.add_line("Columns R1_Decision / R2_Decision / R3_Decision are missing; cannot compute final status.")
            return

        both_include = (r1 == "include") & (r2 == "include")
        both_exclude = (r1 == "exclude") & (r2 == "exclude")
        both_unsure = (r1 == "unsure") & (r2 == "unsure")
        both_empty = (r1 == "") & (r2 == "")
        disagree = (r1 != r2)

        include_direct = both_include
        include_unsure_r3 = both_unsure & (r3 == "include")
        include_disagree_r3 = disagree & (r3 == "include")
        final_include_mask = include_direct | include_unsure_r3 | include_disagree_r3

        exclude_direct = both_exclude
        exclude_unsure_r3 = both_unsure & (r3 == "exclude")
        exclude_disagree_r3 = disagree & (r3 == "exclude")
        exclude_empty = both_empty
        final_exclude_mask = exclude_direct | exclude_unsure_r3 | exclude_disagree_r3 | exclude_empty

        self.add_line("Final inclusion at Stage 2 (by condition):")
        self.add_line(f"  · Cond 1: R1 = R2 = 'include'                             → {int(include_direct.sum())}")
        self.add_line(f"  · Cond 2: R1 = R2 = 'unsure' & R3 = 'include'           → {int(include_unsure_r3.sum())}")
        self.add_line(f"  · Cond 3: R1 != R2         & R3 = 'include'             → {int(include_disagree_r3.sum())}")
        self.add_line(f"  ⇒ Total final include: {int(final_include_mask.sum())}")

        self.add_line("\nFinal exclusion at Stage 2 (by condition):")
        self.add_line(f"  · Cond 1: R1 = R2 = 'exclude'                             → {int(exclude_direct.sum())}")
        self.add_line(f"  · Cond 2: R1 = R2 = 'unsure' & R3 = 'exclude'           → {int(exclude_unsure_r3.sum())}")
        self.add_line(f"  · Cond 3: R1 != R2         & R3 = 'exclude'             → {int(exclude_disagree_r3.sum())}")
        self.add_line(f"  · Cond 4: R1 = R2 = '' (not full-text screened, excluded) → {int(exclude_empty.sum())}")
        self.add_line(f"  ⇒ Total final exclude: {int(final_exclude_mask.sum())}")


# ============================== quality assessment statistics ============================== #


class QualityAssessmentStatistics:
    """
    Quality assessment table statistics.

    File:
    - data/systematic_review/quality_assessment/quality_assessment_table.xlsx
    """

    def __init__(self, qa_root: Path, add_line: Callable[[str], None], logger: logging.Logger) -> None:
        """
        Initialise the quality assessment statistics module.

        :param qa_root: Directory for quality assessment files.
        :param add_line: Callback to append lines to the report.
        :param logger: Logger instance.
        """
        self.qa_root = qa_root
        self.add_line = add_line
        self.logger = logger

    def _section_title(self, title: str) -> None:
        """
        Print and record a first-level section title.

        :param title: Section title text.
        """
        self.add_line("")
        self.add_line("=" * 80)
        self.add_line(title)
        self.add_line("=" * 80)

    def _subsection_title(self, title: str) -> None:
        """
        Print and record a second-level subsection title.

        :param title: Subsection title text.
        """
        self.add_line("")
        self.add_line(f"[{title}]")

    def run(self) -> None:
        """
        Execute all quality assessment statistics.
        """
        self._section_title("IV. Quality assessment (quality_assessment_table.xlsx)")

        path = self.qa_root / "quality_assessment_table.xlsx"
        df = load_excel(path, logger=self.logger)

        self._score_distributions(df)
        self._total_score(df)
        self._quality_category(df)

    def _score_distributions(self, df: pd.DataFrame) -> None:
        """
        Summarise the distributions of q1–q10 item scores (JSON).

        :param df: Quality assessment DataFrame.
        """
        self._subsection_title("4.1 Item-level score distributions (q1–q10)")

        score_cols = [
            "q1_research_aims_clarity_score",
            "q2_participant_info_score",
            "q3_sampling_and_power_score",
            "q4_group_allocation_and_bias_score",
            "q5_longitudinal_design_score",
            "q6_measurement_reliability_validity_score",
            "q7_intervention_procedure_and_duration_score",
            "q8_statistical_method_appropriateness_score",
            "q9_assumption_and_effect_size_score",
            "q10_outliers_and_interpretation_score",
        ]

        for col in score_cols:
            if col in df.columns:
                self.add_line(f"\n{col} value distribution (JSON):")
                self.add_line(value_counts_as_json(df[col]))
            else:
                self.add_line(f"\nColumn {col} is missing.")

    def _total_score(self, df: pd.DataFrame) -> None:
        """
        Summarise the distribution of total_quality_score (JSON).

        :param df: Quality assessment DataFrame.
        """
        self._subsection_title("4.2 total_quality_score distribution")

        if "total_quality_score" in df.columns:
            self.add_line("total_quality_score value distribution (JSON):")
            self.add_line(value_counts_as_json(df["total_quality_score"]))
        else:
            self.add_line("Column total_quality_score is missing.")

    def _quality_category(self, df: pd.DataFrame) -> None:
        """
        Summarise quality_category distribution and count the number of 'High' studies.

        :param df: Quality assessment DataFrame.
        """
        self._subsection_title("4.3 quality_category distribution and High-quality studies")

        qc = df.get("quality_category")
        if qc is None:
            self.add_line("Column quality_category is missing.")
            return

        self.add_line("quality_category value distribution (JSON):")
        self.add_line(value_counts_as_json(qc))

        high_mask = qc == "High"
        self.add_line(f"\nNumber of studies with quality_category = 'High' (included in final sample): {int(high_mask.sum())}")


# ============================== orchestrator ============================== #


class SystematicReviewStatistics:
    """
    Top-level orchestrator for all systematic-review statistics.

    Responsibilities:
    - Resolve project and data root paths.
    - Manage the shared report builder.
    - Sequentially invoke Raw / Stage1 / Stage2 / QA statistics.
    """

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """
        Initialise the orchestrator and construct per-stage statistics modules.

        :param logger: Optional logger; if None, a default logger is created.
        """
        self.logger = logger or setup_logger()

        # apps/systematic_review/systematic_review_statistics.py
        # parents[0] = apps/systematic_review
        # parents[1] = apps
        # parents[2] = project_root
        project_root = Path(__file__).resolve().parents[2]
        data_root = project_root / "data" / "systematic_review"

        self.project_root = project_root
        self.data_root = data_root

        # Shared report builder
        self.report = ReportBuilder()

        # Per-stage statistics modules
        self.raw_stats = RawDataStatistics(
            raw_root=data_root / "raw",
            add_line=self.report.add_line,
            logger=self.logger,
        )
        self.stage1_stats = Stage1ScreeningStatistics(
            stage1_root=data_root / "double_blind" / "stage1_title_abstract",
            add_line=self.report.add_line,
            logger=self.logger,
        )
        self.stage2_stats = Stage2ScreeningStatistics(
            stage2_root=data_root / "double_blind" / "stage2_full_text",
            add_line=self.report.add_line,
            logger=self.logger,
        )
        self.qa_stats = QualityAssessmentStatistics(
            qa_root=data_root / "quality_assessment",
            add_line=self.report.add_line,
            logger=self.logger,
        )

    def run(self) -> None:
        """
        Run the full statistics pipeline and write the final summary report.

        Steps:
        1. Raw search and deduplication statistics.
        2. Stage 1 screening statistics.
        3. Stage 2 screening statistics.
        4. Quality assessment statistics.
        5. Write the .txt report.
        """
        self.logger.info("[MAIN] Systematic review statistics – started")

        self.raw_stats.run()
        self.stage1_stats.run()
        self.stage2_stats.run()
        self.qa_stats.run()

        report_path = self.data_root / "systematic_review_statistics_summary.txt"
        self.report.write_to(report_path)
        self.logger.info(f"[MAIN] Summary report written to: {report_path}")
        self.logger.info("[MAIN] Systematic review statistics – completed")


# ============================== script entry point ============================== #


def main() -> None:
    """
    Script entry point for running the systematic-review statistics pipeline.
    """
    logger = setup_logger(verbose=True)
    stats = SystematicReviewStatistics(logger=logger)
    stats.run()


if __name__ == "__main__":
    main()