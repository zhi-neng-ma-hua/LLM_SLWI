# -*- coding: utf-8 -*-
"""
exclusion_reason_refiner.py

Purpose
-------
Perform a second-round refinement of double_blind_exclusion_reasons.json.

1. Work on an existing JSON structure:
   data/systematic_review/double_blind/double_blind_exclusion_reasons.json

2. For stage1 / stage2 row_fail_stats, process each row:
   - Count how many rows have c1–c4 all equal to 0;
   - For each row, select a "final exclusion reason code" and append it:
       * If all c1–c4 are 0, set final_reason = "" (empty string);
       * Otherwise, final_reason is the key among c1–c4 with the largest value
         (if there is a tie, select the first in the fixed order
          c1 → c2 → c3 → c4).

3. Return the updated JSON structure, including the statistics and refined
   row_fail_stats, to be written back by double_blind_exclusion_runner.py
   or other upstream modules.

Public interfaces
-----------------
refine_exclusion_reasons(json_data, logger=None) -> refined_json
refine_exclusion_reasons_from_file(json_path, logger=None) -> refined_json

The input json_data matches the structure written by
double_blind_exclusion_runner.py:

{
  "stage1": {
    "summary": {...},
    "priority_counts": {...},
    "row_fail_stats": [...]
  },
  "stage2": {
    "summary": {...},
    "priority_counts": {...},
    "row_fail_stats": [...]
  }
}

The returned structure extends this by adding:
- In each stageX["row_fail_stats"] entry (the value dict), a new field:
    "final_reason": "c1" | "c2" | "c3" | "c4" | ""
- stageX["all_zero_row_count"]: int

Author: Aiden Cao <zhinengmahua@gmail.com>
Date  : 2025-12-06
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from apps.systematic_review.utils.logger_manager import LoggerManager
from apps.systematic_review.utils.exceptions import DataValidationError

# JSON structure type aliases
StageData = Dict[str, Any]
ExclusionReasonsJson = Dict[str, StageData]

#: Fixed fail-key order (used for max selection and tie-breaking)
FAIL_KEYS: Tuple[str, ...] = ("c1", "c2", "c3", "c4")

#: Expected stage keys in the JSON structure
STAGE_KEYS: Tuple[str, ...] = ("stage1", "stage2")


def setup_logger(
    name: str = "exclusion_reason_refiner",
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
# Minimal class wrapper: ExclusionReasonRefiner
# ============================================================================


class ExclusionReasonRefiner:
    """
    Post-processor for exclusion reasons.

    Responsibilities:
    - For a given JSON structure, append final_reason to each row in
      stage1 / stage2 row_fail_stats;
    - Count, for each stage, the number of rows where c1–c4 are all zero
      (all_zero_row_count);
    - Does not handle file I/O; only operates on in-memory JSON dicts.
    """

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or setup_logger()

    # -------------------- Row-level final_reason selection -------------------- #

    @staticmethod
    def _choose_final_reason(fail_counts: Dict[str, Any]) -> Tuple[str, bool]:
        """
        Choose the final exclusion reason code based on c1–c4 fail counts.

        Rules:
        - If all c1–c4 are 0: return ("", True), indicating "no JSON-based fail reason";
        - Otherwise:
            1) Only consider the four keys c1, c2, c3, c4;
            2) If there is a tie, select the first in the fixed order
               c1 → c2 → c3 → c4.

        :param fail_counts: e.g., {"c1": 0, "c2": 1, "c3": 0, "c4": 2}
        :return: (final_reason, all_zero_flag)
        """
        values = [int(fail_counts.get(k, 0)) for k in FAIL_KEYS]
        max_val = max(values)
        if max_val == 0:
            return "", True

        for key in FAIL_KEYS:
            if int(fail_counts.get(key, 0)) == max_val:
                return key, False

        # Should not happen under normal circumstances; return empty as a safeguard
        return "", True

    # -------------------- Per-stage row_fail_stats processing -------------------- #

    def _process_stage_row_fail_stats(
        self,
        stage_label: str,
        stage_data: StageData,
    ) -> StageData:
        """
        Refine row_fail_stats for a single stage.

        Steps:
        1. Count rows where c1–c4 are all zero;
        2. Append a "final_reason" field to each row:
           - "" means all c1–c4 are zero;
           - otherwise one of {"c1","c2","c3","c4"}.

        :param stage_label: Stage label (e.g. "stage1" / "stage2").
        :param stage_data: Dict for this stage in the JSON structure.
        :return: Updated stage_data (modified in place and returned).
        """
        row_fail_stats: List[Dict[str, Dict[str, Any]]] = stage_data.get(
            "row_fail_stats", []
        )
        if not isinstance(row_fail_stats, list):
            self.logger.warning(
                f"[{stage_label}] row_fail_stats is not a list; skipping refinement."
            )
            return stage_data

        all_zero_count = 0

        for idx, row in enumerate(row_fail_stats):
            # Each row is expected to be {"<No.>": {"c1": x, "c2": y, "c3": z, "c4": w}}
            if not isinstance(row, dict) or len(row) != 1:
                self.logger.debug(
                    f"[{stage_label}] row_fail_stats[{idx}] has unexpected structure; "
                    f"expected single-key dict: {row}"
                )
                continue

            no_str, fail_dict = next(iter(row.items()))
            if not isinstance(fail_dict, dict):
                self.logger.debug(
                    f"[{stage_label}] row_fail_stats[{idx}] value is not dict: {fail_dict}"
                )
                continue

            final_reason, is_all_zero = self._choose_final_reason(fail_dict)
            if is_all_zero:
                all_zero_count += 1

            # Append final_reason on top of the existing fail counts
            fail_dict["final_reason"] = final_reason
            row[no_str] = fail_dict  # in-place update to preserve structure

        stage_data["all_zero_row_count"] = all_zero_count

        self.logger.info(
            f"[{stage_label}] rows with all-zero c1–c4 in row_fail_stats: {all_zero_count}"
        )
        return stage_data

    # -------------------- Global refine logic -------------------- #

    def refine(self, json_data: ExclusionReasonsJson) -> ExclusionReasonsJson:
        """
        Perform second-level refinement for the full double_blind_exclusion_reasons JSON.

        For each of stage1 / stage2:
        - Count rows in row_fail_stats where c1–c4 are all zero, store as all_zero_row_count;
        - Append "final_reason" to each row in row_fail_stats.

        :param json_data: Original JSON structure (not yet written to file).
        :return: JSON structure enriched with final_reason and all_zero_row_count.
        """
        if not isinstance(json_data, dict):
            raise DataValidationError(
                f"JSON root must be a dict, got: {type(json_data)}"
            )

        refined: ExclusionReasonsJson = {}
        for stage_key in STAGE_KEYS:
            stage_value = json_data.get(stage_key)
            if stage_value is None:
                self.logger.warning(f"[{stage_key}] not found in JSON; skipping.")
                refined[stage_key] = {}
                continue

            if not isinstance(stage_value, dict):
                raise DataValidationError(
                    f"{stage_key} must map to a dict, got: {type(stage_value)}"
                )

            refined_stage = self._process_stage_row_fail_stats(
                stage_label=stage_key,
                stage_data=stage_value,
            )
            refined[stage_key] = refined_stage

        return refined


# ============================================================================
# Public function interfaces (for Runner or other modules)
# ============================================================================


def refine_exclusion_reasons(
    json_data: ExclusionReasonsJson,
    logger: Optional[logging.Logger] = None,
) -> ExclusionReasonsJson:
    """
    Refine an in-memory double_blind_exclusion_reasons JSON structure.

    :param json_data: Original JSON dict (not yet written to file).
    :param logger: Optional logger instance; if None, a default logger is created.
    :return: JSON structure with final_reason and all_zero_row_count added.
    """
    refiner = ExclusionReasonRefiner(logger=logger)
    return refiner.refine(json_data=json_data)


def refine_exclusion_reasons_from_file(
    json_path: Path,
    logger: Optional[logging.Logger] = None,
) -> ExclusionReasonsJson:
    """
    Load double_blind_exclusion_reasons.json from the given path, refine it,
    and return the updated structure.

    Note:
    - This function does not write back to disk; it only returns the refined data.
    - If you need to overwrite the file, call json.dump(...) at the call site.

    :param json_path: Path to the JSON file.
    :param logger: Optional logger instance; if None, a default logger is created.
    :return: JSON structure with final_reason and all_zero_row_count added.
    :raises DataValidationError: If the file does not exist or the JSON structure is invalid.
    """
    logger = logger or setup_logger()

    if not json_path.is_file():
        raise DataValidationError(f"JSON file not found: {json_path}")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        raise DataValidationError(
            f"Failed to read JSON file: {json_path}, error: {exc}"
        )

    if not isinstance(data, dict):
        raise DataValidationError(
            f"JSON root must be a dict, got: {type(data)}"
        )

    refiner = ExclusionReasonRefiner(logger=logger)
    return refiner.refine(json_data=data)