# -*- coding: utf-8 -*-
"""
stage1_exclusion_stats.py

Purpose
-------
For Stage 1 (Title/Abstract) triple-blind screening results, this module:

1. Computes the numbers of included / excluded / unresolved records and the
   counts of exclusions under rule1–rule4;
2. Decomposes finally excluded records into:
    A. priority reasons (R3_Notes prefixes: Access / Payment / Non-English);
    B. remaining records, for which JSON-based c1–c4 fail counts are computed
       according to rule1–rule4;
3. Returns a structured result dictionary to be consumed by
   double_blind_exclusion_runner.py and written to JSON.

I. Inclusion / exclusion rules (Stage 1)
---------------------------------------
Decision columns:
    R1_Decision, R2_Decision, R3_Decision

Final exclusion (Stage 1) if any of the following holds:
    rule1: R1_Decision = R2_Decision = "exclude"
    rule2: R1_Decision = R2_Decision = "unsure" and R3_Decision = "exclude"
    rule3: R1_Decision = R2_Decision = ""      and R3_Decision = "exclude"
    rule4: R1_Decision != R2_Decision          and R3_Decision = "exclude"

Final inclusion (Stage 1) if any of the following holds:
    rule1_inc: R1_Decision = R2_Decision = "include"
    rule2_inc: R1_Decision = R2_Decision = "unsure" and R3_Decision = "include"
    rule3_inc: R1_Decision != R2_Decision           and R3_Decision = "include"

II. Exclusion-reason statistics (two-part, to avoid double-counting)
--------------------------------------------------------------------
For Stage 1 finally excluded records, statistics are computed in two parts:

A. Priority reasons (external reasons, no JSON parsing)
   If R3_Notes starts with any of the following prefixes (case-insensitive):
       "Access restrictions"
       "Payment restrictions"
       "Non-English literature"
   the record is treated as excluded for external reasons and counted in:
       {"access": n1, "payment": n2, "non_english": n3, "total": n_all}
   These records are then removed from subsequent JSON-based statistics.

B. Remaining exclusions (JSON-based c1–c4 fail statistics)
   For finally excluded records not captured by A, the following rules apply:

   - rule1 (R1 = R2 = "exclude"):
        Use both R1_Notes and R2_Notes, parse JSON, and count c1–c4
        entries with status = "fail"; the two counts are summed.
   - rule2 (R1 = R2 = "unsure" and R3 = "exclude"):
        Use R3_Notes, parse JSON, and count c1–c4 fails.
   - rule3 (R1 = R2 = "" and R3 = "exclude"):
        Use R3_Notes, parse JSON, and count c1–c4 fails.
   - rule4 (R1 != R2 and R3 = "exclude"):
        Use R3_Notes, parse JSON, and count c1–c4 fails.

III. Public interface of this module
------------------------------------
Given a Stage 1 triple-blind result Excel file:

1. Compute included / excluded / unresolved counts and rule1–rule4 exclusion counts;
2. Decompose finally excluded records into:
    A. priority reasons (R3_Notes prefixes: Access / Payment / Non-English);
    B. remaining records with JSON-based c1–c4 fail counts under rule1–rule4;
3. Return a structured result dictionary to be aggregated by
   double_blind_exclusion_runner.py and written to JSON.

Return structure
----------------
analyze_stage1(data_path, ...) -> {
    "summary": {...},
    "priority_counts": {...},
    "row_fail_stats": [...]
}

Author: Aiden Cao <zhinengmahua@gmail.com>
Date  : 2025-12-06
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from apps.systematic_review.utils.data_io import load_table
from apps.systematic_review.utils.exceptions import DataValidationError
from apps.systematic_review.utils.logger_manager import LoggerManager

# ---------------------------------------------------------------------------
# Column names and type constants (Stage 1 only)
# ---------------------------------------------------------------------------

# Decision columns
COL_R1_DECISION = "R1_Decision"
COL_R2_DECISION = "R2_Decision"
COL_R3_DECISION = "R3_Decision"

# Notes columns
COL_R1_NOTES = "R1_Notes"
COL_R2_NOTES = "R2_Notes"
COL_R3_NOTES = "R3_Notes"

# Primary key column
COL_NO = "No."

# Stage 1 priority prefixes: category -> tuple of prefixes (lowercase comparison)
PRIORITY_PREFIX_MAP: Dict[str, Tuple[str, ...]] = {
    "access": ("access restrictions",),
    "payment": ("payment restrictions",),
    "non_english": ("non-english literature",),
}


def setup_logger(
    name: str = "stage1_exclusion_stats",
    verbose: bool = True,
) -> logging.Logger:
    """
    Configure and return a logger instance.

    :param name: Logger name.
    :param verbose: Whether to enable DEBUG-level logs.
    :return: Configured logging.Logger instance.
    """
    return LoggerManager.setup_logger(
        logger_name=name,
        module_name=__name__,
        verbose=verbose,
    )


# ============================================================================
# Class 1: Data loading and normalization
# ============================================================================


class Stage1DataLoader:
    """
    Loader for Stage 1 result table and normalizer for decision columns.
    """

    REQUIRED_COLS = {COL_R1_DECISION, COL_R2_DECISION, COL_R3_DECISION}

    def __init__(self, data_path: Path, logger: logging.Logger) -> None:
        self.data_path = data_path
        self.logger = logger

    def load(self) -> pd.DataFrame:
        """
        Load and normalize the Stage 1 result table.

        :return: Normalized DataFrame.
        :raises DataValidationError: If the file does not exist, cannot be loaded,
                                     or required columns are missing.
        """
        if not self.data_path.is_file():
            raise DataValidationError(f"Stage 1 result file not found: {self.data_path}")

        try:
            df = load_table(self.data_path, logger=self.logger)
        except Exception as exc:
            raise DataValidationError(
                f"Failed to load Stage 1 result file: {self.data_path}, error: {exc}"
            )

        self.logger.info(
            f"[Stage 1] FILE_LOADED: {self.data_path.name} | rows={len(df)} | "
            f"columns={list(df.columns)}"
        )

        missing = self.REQUIRED_COLS - set(df.columns)
        if missing:
            raise DataValidationError(
                f"Stage 1 result file is missing required decision columns: {missing}"
            )

        df = df.copy()
        for col in self.REQUIRED_COLS:
            df[col] = df[col].astype(str).str.strip().str.lower()

        self.logger.info(
            f"[Stage 1] Decision columns normalized: {self.data_path} (n={len(df)})"
        )
        return df


# ============================================================================
# Class 2: Decision mask builder (rule1–rule4 + inclusion mask)
# ============================================================================


class Stage1DecisionMaskBuilder:
    """
    Build inclusion and exclusion masks from normalized decision columns.
    """

    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df

    def build_excluded_mask(self) -> pd.Series:
        """
        Build the final exclusion mask.

        :return: Boolean Series marking finally excluded records.
        """
        r1 = self.df[COL_R1_DECISION]
        r2 = self.df[COL_R2_DECISION]
        r3 = self.df[COL_R3_DECISION]

        mask_rule1 = (r1 == "exclude") & (r2 == "exclude")
        mask_rule2 = (r1 == "unsure") & (r2 == "unsure") & (r3 == "exclude")
        mask_rule3 = (r1 == "") & (r2 == "") & (r3 == "exclude")
        mask_rule4 = (r1 != r2) & (r3 == "exclude")

        return mask_rule1 | mask_rule2 | mask_rule3 | mask_rule4

    def build_included_mask(self) -> pd.Series:
        """
        Build the final inclusion mask.

        :return: Boolean Series marking finally included records.
        """
        r1 = self.df[COL_R1_DECISION]
        r2 = self.df[COL_R2_DECISION]
        r3 = self.df[COL_R3_DECISION]

        mask_inc1 = (r1 == "include") & (r2 == "include")
        mask_inc2 = (r1 == "unsure") & (r2 == "unsure") & (r3 == "include")
        mask_inc3 = (r1 != r2) & (r3 == "include")

        return mask_inc1 | mask_inc2 | mask_inc3


# ============================================================================
# Class 3: Global counts and summary
# ============================================================================


class Stage1SummaryCalculator:
    """
    Compute Stage 1 global counts.

    Includes:
    - total / included / excluded / unresolved
    - rule1–rule4 exclusion counts.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        included_mask: pd.Series,
        excluded_mask: pd.Series,
        logger: logging.Logger,
    ) -> None:
        self.df = df
        self.included_mask = included_mask
        self.excluded_mask = excluded_mask
        self.logger = logger
        self.label = "Stage 1 (Title/Abstract)"

    def compute_summary(self) -> Dict[str, int]:
        """
        Compute the summary statistics.

        :return: Summary dictionary.
        """
        total = len(self.df)
        included_count = int(self.included_mask.sum())
        excluded_count = int(self.excluded_mask.sum())
        unresolved_mask = ~(self.included_mask | self.excluded_mask)
        unresolved_count = int(unresolved_mask.sum())

        self.logger.info(
            f"[{self.label}] total={total}, included={included_count}, "
            f"excluded={excluded_count}, unresolved={unresolved_count}"
        )

        if unresolved_count > 0:
            self.logger.warning(
                f"[{self.label}] {unresolved_count} records are not covered by "
                f"inclusion/exclusion rules; manual inspection recommended."
            )

        if included_count + excluded_count != total:
            self.logger.warning(
                f"[{self.label}] included + excluded != total "
                f"({included_count} + {excluded_count} != {total})"
            )

        r1 = self.df[COL_R1_DECISION]
        r2 = self.df[COL_R2_DECISION]
        r3 = self.df[COL_R3_DECISION]

        mask_rule1 = (r1 == "exclude") & (r2 == "exclude")
        mask_rule2 = (r1 == "unsure") & (r2 == "unsure") & (r3 == "exclude")
        mask_rule3 = (r1 == "") & (r2 == "") & (r3 == "exclude")
        mask_rule4 = (r1 != r2) & (r3 == "exclude")

        summary: Dict[str, int] = {
            "total": total,
            "included": included_count,
            "excluded": excluded_count,
            "unresolved": unresolved_count,
            "rule1_excluded": int(mask_rule1.sum()),
            "rule2_excluded": int(mask_rule2.sum()),
            "rule3_excluded": int(mask_rule3.sum()),
            "rule4_excluded": int(mask_rule4.sum()),
        }

        self.logger.info(
            f"[{self.label}] exclusion breakdown: "
            f"rule1={summary['rule1_excluded']}, "
            f"rule2={summary['rule2_excluded']}, "
            f"rule3={summary['rule3_excluded']}, "
            f"rule4={summary['rule4_excluded']}"
        )
        return summary


# ============================================================================
# Class 4: JSON fail parsing utility
# ============================================================================


class Stage1JsonFailCounter:
    """
    Utility for parsing JSON fail information and counting c1–c4 fails.
    """

    @staticmethod
    def count_fail(value: Any) -> Dict[str, int]:
        """
        Parse a single Notes JSON cell and count c1–c4 entries with status = "fail".

        Supported formats:
        - {"c1": {"status": "fail"}, "c2": {"status": "pass"}, ...}
        - {"c1": "fail", "c2": "pass", ...}

        :param value: Notes cell content; may be str / dict / other.
        :return: {"c1": x, "c2": y, "c3": z, "c4": w}
        """
        counts = {"c1": 0, "c2": 0, "c3": 0, "c4": 0}

        if value is None or (isinstance(value, float) and pd.isna(value)):
            return counts

        if isinstance(value, str):
            text = value.strip()
            if not text:
                return counts
            try:
                data = json.loads(text)
            except Exception:
                return counts
        else:
            data = value

        if isinstance(data, dict):
            for key in ("c1", "c2", "c3", "c4"):
                if key not in data:
                    continue
                v = data[key]
                if isinstance(v, dict):
                    status = v.get("status")
                else:
                    status = v
                if isinstance(status, str) and status.strip().lower() == "fail":
                    counts[key] += 1

        return counts


# ============================================================================
# Class 5: Exclusion-reason analysis (priority reasons + JSON fail)
# ============================================================================


class Stage1ExclusionReasonAnalyzer:
    """
    Exclusion-reason analysis.

    Responsibilities:
    - Based on the final exclusion mask, decompose excluded records into:
        A. priority reasons (R3_Notes prefixes);
        B. non-priority records with JSON-based fail statistics (rule1–rule4).
    """

    def __init__(
        self,
        df: pd.DataFrame,
        excluded_mask: pd.Series,
        logger: logging.Logger,
        json_counter: Stage1JsonFailCounter,
    ) -> None:
        self.df = df
        # Work only on the excluded subset to avoid unnecessary changes to the full df
        self.excluded_df = df[excluded_mask].copy()
        self.logger = logger
        self.json_counter = json_counter
        self.label = "Stage 1 (Title/Abstract)"

    @staticmethod
    def _match_priority_category(text: str) -> Optional[str]:
        """
        Determine which priority category a text belongs to, based on prefixes.

        :param text: Input string.
        :return: "access" | "payment" | "non_english" | None.
        """
        if not text:
            return None
        lower = text.strip().lower()
        for category, prefixes in PRIORITY_PREFIX_MAP.items():
            for prefix in prefixes:
                if lower.startswith(prefix):
                    return category
        return None

    def compute_reasons(
        self,
    ) -> Tuple[List[Dict[str, Dict[str, int]]], Dict[str, int]]:
        """
        Compute exclusion reasons: priority counts + per-row JSON fail statistics.

        :return: (row_fail_stats, priority_counts).
        :raises DataValidationError: If the 'No.' column is missing.
        """
        if COL_NO not in self.df.columns:
            raise DataValidationError(
                "Stage 1 data is missing 'No.' column; row-level statistics cannot be computed."
            )

        # Ensure Notes columns exist on the excluded subset
        for col in (COL_R1_NOTES, COL_R2_NOTES, COL_R3_NOTES):
            if col not in self.excluded_df.columns:
                self.excluded_df[col] = ""

        self.logger.info(
            f"[{self.label}] final excluded records: {len(self.excluded_df)}"
        )

        r1 = self.excluded_df[COL_R1_DECISION]
        r2 = self.excluded_df[COL_R2_DECISION]
        r3 = self.excluded_df[COL_R3_DECISION]
        r1_notes = self.excluded_df[COL_R1_NOTES]
        r2_notes = self.excluded_df[COL_R2_NOTES]
        r3_notes = self.excluded_df[COL_R3_NOTES]

        # ---------- Part A: priority reasons (R3_Notes prefixes) ---------- #
        priority_counts = {category: 0 for category in PRIORITY_PREFIX_MAP.keys()}
        priority_mask = pd.Series(False, index=self.excluded_df.index)

        for idx in self.excluded_df.index:
            category = self._match_priority_category(str(r3_notes.loc[idx]))
            if category:
                priority_counts[category] += 1
                priority_mask.loc[idx] = True

        priority_counts["total"] = sum(priority_counts.values())
        self.logger.info(
            f"[{self.label}] priority exclusion counts (R3_Notes prefixes): {priority_counts}"
        )

        # Remove priority-reason records from subsequent JSON-based statistics
        remaining_df = self.excluded_df[~priority_mask].copy()
        self.logger.info(
            f"[{self.label}] non-priority excluded records: {len(remaining_df)}"
        )

        # ---------- Part B: JSON-based c1–c4 fail counts (rule1–rule4) ---------- #
        row_stats: List[Dict[str, Dict[str, int]]] = []

        for idx in remaining_df.index:
            no_value = str(remaining_df.at[idx, COL_NO])
            c_fail = {"c1": 0, "c2": 0, "c3": 0, "c4": 0}

            r1_val = r1.loc[idx]
            r2_val = r2.loc[idx]
            r3_val = r3.loc[idx]

            if r1_val == "exclude" and r2_val == "exclude":
                # rule1: use R1_Notes + R2_Notes
                counts_r1 = self.json_counter.count_fail(r1_notes.loc[idx])
                counts_r2 = self.json_counter.count_fail(r2_notes.loc[idx])
                for key in c_fail:
                    c_fail[key] = counts_r1.get(key, 0) + counts_r2.get(key, 0)
            elif r1_val == "unsure" and r2_val == "unsure" and r3_val == "exclude":
                # rule2: use R3_Notes
                c_fail = self.json_counter.count_fail(r3_notes.loc[idx])
            elif r1_val == "" and r2_val == "" and r3_val == "exclude":
                # rule3: use R3_Notes
                c_fail = self.json_counter.count_fail(r3_notes.loc[idx])
            elif r3_val == "exclude":
                # rule4: all other R3 = "exclude" cases, use R3_Notes
                c_fail = self.json_counter.count_fail(r3_notes.loc[idx])
            else:
                # Should not occur under the exclusion mask; kept for robustness
                self.logger.debug(
                    f"[{self.label}] unexpected exclusion pattern (No={no_value}): "
                    f"R1={r1_val}, R2={r2_val}, R3={r3_val}"
                )

            row_stats.append({no_value: c_fail})

        self.logger.debug(
            f"[{self.label}] non-priority row_fail_stats length={len(row_stats)}, "
            f"first 5 entries: {row_stats[:5]}"
        )
        return row_stats, priority_counts


# ============================================================================
# Public entry point: analyze_stage1 (for Runner)
# ============================================================================


def analyze_stage1(
    data_path: Path,
    logger: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """
    Public entry point for Stage 1 exclusion statistics and reason analysis.

    :param data_path: Path to the Stage 1 result file.
    :param logger: Optional logger instance; if None, a default logger is created.
    :return: {
        "summary": {...},
        "priority_counts": {...},
        "row_fail_stats": [...]
    }
    :raises DataValidationError: If the path is invalid or the data structure is inconsistent.
    """
    logger = logger or setup_logger()

    # 1. Load and normalize data
    loader = Stage1DataLoader(data_path=data_path, logger=logger)
    df = loader.load()

    # 2. Build inclusion / exclusion masks
    mask_builder = Stage1DecisionMaskBuilder(df)
    excluded_mask = mask_builder.build_excluded_mask()
    included_mask = mask_builder.build_included_mask()

    # 3. Compute global summary
    summary_calc = Stage1SummaryCalculator(
        df=df,
        included_mask=included_mask,
        excluded_mask=excluded_mask,
        logger=logger,
    )
    summary = summary_calc.compute_summary()

    # 4. JSON fail utility
    json_counter = Stage1JsonFailCounter()

    # 5. Exclusion-reason decomposition
    reason_analyzer = Stage1ExclusionReasonAnalyzer(
        df=df,
        excluded_mask=excluded_mask,
        logger=logger,
        json_counter=json_counter,
    )
    row_fail_stats, priority_counts = reason_analyzer.compute_reasons()

    return {
        "summary": summary,
        "priority_counts": priority_counts,
        "row_fail_stats": row_fail_stats,
    }