# -*- coding: utf-8 -*-
"""
double_blind_exclusion_runner.py

Purpose
-------
This script serves as the central controller for double-blind exclusion statistics.
It is responsible for:

1. Invoking the Stage 1 (Title/Abstract) exclusion statistics module;
2. Invoking the Stage 2 (Full-text) exclusion statistics module;
3. Invoking exclusion_reason_refiner.py to perform a second refinement on the
   results of both stages (adding final_reason and counting rows where c1–c4 are all 0);
4. Writing the final combined results to the main JSON file:

   data/systematic_review/double_blind/double_blind_exclusion_reasons.json

5. Generating an additional summary JSON file that aggregates the usage of
   final_reason codes, to facilitate PRISMA reporting, appendices, and
   manuscript writing:

   data/systematic_review/double_blind/double_blind_exclusion_reason_summary.json
"""

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from apps.systematic_review.utils.logger_manager import LoggerManager
from apps.systematic_review.utils.exceptions import DataValidationError

from apps.systematic_review.double_blind.exclusion.stage1_exclusion_stats import (
    analyze_stage1,
)
from apps.systematic_review.double_blind.exclusion.stage2_exclusion_stats import (
    analyze_stage2,
)
from apps.systematic_review.double_blind.exclusion.exclusion_reason_refiner import (
    refine_exclusion_reasons,
)

# ---------------------------------------------------------------------------
# Type aliases and constants
# ---------------------------------------------------------------------------

#: Per-stage result structure: must contain summary / priority_counts / row_fail_stats
StageResult = Dict[str, Any]

#: Top-level JSON structure: {"stage1": StageResult, "stage2": StageResult}
FullResult = Dict[str, StageResult]

#: Per-stage analysis function type: takes data file path and optional logger, returns StageResult
AnalyzeFunc = Callable[[Path, Optional[logging.Logger]], StageResult]

#: Keys that must be present in each stage result
REQUIRED_RESULT_KEYS: Tuple[str, ...] = (
    "summary",
    "priority_counts",
    "row_fail_stats",
)

#: Relative path (from project root) to data/systematic_review/double_blind
DOUBLE_BLIND_DATA_REL = Path("data") / "systematic_review" / "double_blind"

#: Relative paths to Stage 1 / Stage 2 result files
STAGE1_REL_PATH = Path("stage1_title_abstract") / "R1_R2_R3_analysis_results.xlsx"
STAGE2_REL_PATH = Path("stage2_full_text") / "R1_R2_R3_analysis_results.xlsx"

#: Output JSON filenames (main file + summary file)
OUTPUT_FILENAME_MAIN = "double_blind_exclusion_reasons.json"
OUTPUT_FILENAME_SUMMARY = "double_blind_exclusion_reason_summary.json"

#: Allowed values for final_reason (in fixed order for summary)
FINAL_REASON_KEYS: Tuple[str, ...] = ("c1", "c2", "c3", "c4", "")

#: Stage keys participating in the statistics
STAGE_KEYS: Tuple[str, ...] = ("stage1", "stage2")

#: Standard descriptions of rule1–rule4 (used in main JSON and summary JSON)
EXCLUSION_RULES: Dict[str, str] = {
    "rule1": (
        "R1_Decision = R2_Decision = 'exclude' "
        "(both primary reviewers independently exclude)."
    ),
    "rule2": (
        "R1_Decision = R2_Decision = 'unsure' and R3_Decision = 'exclude' "
        "(both primary reviewers unsure, adjudicator excludes)."
    ),
    "rule3": (
        "R1_Decision = R2_Decision = '' and the adjudicating decision is 'exclude' "
        "(Stage 1: R3_Decision; Stage 2: Final_Decision)."
    ),
    "rule4": (
        "R1_Decision != R2_Decision and R3_Decision = 'exclude' "
        "(primary reviewers disagree, adjudicator excludes)."
    ),
}


def setup_logger(
    name: str = "double_blind_exclusion_runner",
    verbose: bool = True,
) -> logging.Logger:
    """
    Configure and return a logger instance.
    """
    return LoggerManager.setup_logger(
        logger_name=name,
        module_name=__name__,
        verbose=verbose,
    )


class DoubleBlindExclusionRunner:
    """
    Orchestrator for double-blind exclusion statistics.

    Responsibilities
    ----------------
    - Resolve project root and the double_blind data directory;
    - Invoke Stage 1 / Stage 2 exclusion analysis functions;
    - Invoke refine_exclusion_reasons for second-level refinement;
    - Write the main JSON and the summary JSON.
    """

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """
        Initialize the runner and resolve the double_blind data directory.

        :param logger: Optional logger instance; if None, a default logger is created.
        :raises DataValidationError: If the double_blind data directory does not exist.
        """
        self.logger = logger or setup_logger()

        # This file is located at apps/systematic_review/double_blind/exclusion/
        # Go up four levels to reach project root, then append data/systematic_review/double_blind
        project_root = Path(__file__).resolve().parents[4]
        self.double_blind_root = project_root / DOUBLE_BLIND_DATA_REL

        if not self.double_blind_root.is_dir():
            raise DataValidationError(
                f"double_blind data directory does not exist: {self.double_blind_root}"
            )

        self.logger.info(f"[PATH] double_blind data root: {self.double_blind_root}")

        # Per-stage data file paths
        self.stage1_data_path = self.double_blind_root / STAGE1_REL_PATH
        self.stage2_data_path = self.double_blind_root / STAGE2_REL_PATH

        # Output JSON paths
        self.output_path_main = self.double_blind_root / OUTPUT_FILENAME_MAIN
        self.output_path_summary = self.double_blind_root / OUTPUT_FILENAME_SUMMARY

    # ------------------------------------------------------------------ #
    # Internal helper methods
    # ------------------------------------------------------------------ #

    def _run_single_stage(
        self,
        stage_label: str,
        data_path: Path,
        analyze_func: AnalyzeFunc,
    ) -> StageResult:
        """
        Run the analysis function for a single stage and perform basic validation + logging.

        :param stage_label: Stage label (e.g. "Stage 1 (Title/Abstract)").
        :param data_path: Excel file path for the current stage.
        :param analyze_func: Stage analysis function (analyze_stage1 / analyze_stage2).
        :return: StageResult with required keys.
        :raises DataValidationError: If the data file does not exist or required keys are missing.
        """
        if not data_path.is_file():
            raise DataValidationError(f"{stage_label} data file not found: {data_path}")

        self.logger.info(f"[{stage_label}] using data file: {data_path}")
        self.logger.info(f"[{stage_label}] starting exclusion analysis")

        result = analyze_func(data_path, logger=self.logger)

        # Structural validation
        for key in REQUIRED_RESULT_KEYS:
            if key not in result:
                raise DataValidationError(
                    f"{stage_label} result is missing required key: '{key}'"
                )

        # Log key statistics; keep detailed examples at DEBUG level
        self.logger.info(f"[{stage_label}] Summary: {result['summary']}")
        self.logger.info(
            f"[{stage_label}] Priority counts: {result['priority_counts']}"
        )
        self.logger.debug(
            f"[{stage_label}] row_fail_stats first 5 entries: "
            f"{result['row_fail_stats'][:5]}"
        )

        return result

    def _write_main_json(self, final_data: FullResult) -> None:
        """
        Write the final detailed results to the main JSON file.

        JSON structure:
        {
          "exclusion_rules": EXCLUSION_RULES,
          "stage1": {...},
          "stage2": {...}
        }
        """
        payload: Dict[str, Any] = {
            "exclusion_rules": EXCLUSION_RULES,
            "stage1": final_data.get("stage1", {}),
            "stage2": final_data.get("stage2", {}),
        }

        try:
            with open(self.output_path_main, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self.logger.info(
                f"[JSON] Double-blind exclusion statistics (with final_reason) "
                f"written to: {self.output_path_main}"
            )
        except Exception as exc:
            self.logger.error(f"[JSON] Failed to write main JSON file: {exc}")
            raise

    def _summarize_stage_final_reasons(
        self,
        stage_key: str,
        stage_data: StageResult,
    ) -> Dict[str, Any]:
        """
        Summarize the distribution of final_reason for a single stage,
        together with summary / priority_counts.

        :param stage_key: "stage1" or "stage2" (used only for logging context).
        :param stage_data: The refined_output[stage_key] structure.
        :return: {
            "summary": {...},
            "priority_counts": {...},
            "final_reason": {
                "<code>": {"count": int, "no_list": [str, ...]}, ...
            }
        }
        """
        summary = stage_data.get("summary", {})
        priority_counts = stage_data.get("priority_counts", {})
        row_fail_stats = stage_data.get("row_fail_stats", [])

        # Initialize final_reason statistics for each allowed code
        reason_stats: Dict[str, Dict[str, Any]] = {
            code: {"count": 0, "no_list": []} for code in FINAL_REASON_KEYS
        }

        if isinstance(row_fail_stats, list):
            for row in row_fail_stats:
                # Each row is expected to be {"<No.>": {"c1":..., "c2":..., "c3":..., "c4":..., "final_reason": ...}}
                if not isinstance(row, dict) or len(row) != 1:
                    continue

                no_str, fail_dict = next(iter(row.items()))
                if not isinstance(fail_dict, dict):
                    continue

                reason_code = str(fail_dict.get("final_reason", ""))
                if reason_code not in reason_stats:
                    # Map unexpected values to the empty-code bucket to avoid KeyError
                    reason_code = ""

                reason_stats[reason_code]["count"] += 1
                reason_stats[reason_code]["no_list"].append(str(no_str))

        return {
            "summary": summary,
            "priority_counts": priority_counts,
            "final_reason": reason_stats,
        }

    def _build_reason_summary(self, final_data: FullResult) -> Dict[str, Any]:
        """
        Build a compact final_reason summary structure from refined_output.

        Top-level structure:
        {
          "reason_codes": {...},
          "exclusion_rules": {...},
          "stage1": {...},
          "stage2": {...}
        }
        """
        # 1. Define reason_codes (each description aligned with C1–C4 failures)
        reason_codes: Dict[str, Dict[str, Any]] = {
            "c1": {
                "id": 1,
                "label": "c1",
                "description": (
                    "Population ineligible: sample is not primarily L2 English learners "
                    "in ESL, EFL or ELL settings, or English is not the main target language."
                ),
            },
            "c2": {
                "id": 2,
                "label": "c2",
                "description": (
                    "Intervention ineligible: no experimental or quasi-experimental "
                    "LLM-based writing intervention is implemented."
                ),
            },
            "c3": {
                "id": 3,
                "label": "c3",
                "description": (
                    "Context ineligible: study does not primarily examine L2 writing "
                    "competence or writing-related outcomes."
                ),
            },
            "c4": {
                "id": 4,
                "label": "c4",
                "description": (
                    "Outcome ineligible: quantitative writing outcomes for the "
                    "LLM-mediated intervention are not reported."
                ),
            },
            "": {
                "id": 0,
                "label": "none",
                "description": (
                    "Excluded for external reasons (access/payment restrictions, "
                    "non-English full text, duplicate records); no C1–C4 code applied."
                ),
            },
        }

        summary_json: Dict[str, Any] = {
            "reason_codes": reason_codes,
            "exclusion_rules": EXCLUSION_RULES,
        }

        # 2. Summarize final_reason distribution for each stage
        for stage_key in STAGE_KEYS:
            stage_value = final_data.get(stage_key, {})
            if not isinstance(stage_value, dict):
                self.logger.warning(
                    f"[SUMMARY] {stage_key} has unexpected type, expected dict, got: {type(stage_value)}"
                )
                continue

            summary_json[stage_key] = self._summarize_stage_final_reasons(
                stage_key=stage_key,
                stage_data=stage_value,
            )

        return summary_json

    def _write_summary_json(
        self,
        summary_data: Dict[str, Any],
    ) -> None:
        """
        Write the final_reason summary structure to the summary JSON file.
        """
        try:
            with open(self.output_path_summary, "w", encoding="utf-8") as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=2)
            self.logger.info(
                f"[JSON] final_reason summary written to: {self.output_path_summary}"
            )
        except Exception as exc:
            self.logger.error(
                f"[JSON] Failed to write summary JSON file: {exc}"
            )
            raise

    # ------------------------------------------------------------------ #
    # Public main workflow
    # ------------------------------------------------------------------ #

    def run(self) -> FullResult:
        """
        Run Stage 1 and Stage 2 exclusion statistics, refine results, and
        write out two JSON files:

        - double_blind_exclusion_reasons.json
        - double_blind_exclusion_reason_summary.json
        """
        # 1. Stage 1
        stage1_result = self._run_single_stage(
            stage_label="Stage 1 (Title/Abstract)",
            data_path=self.stage1_data_path,
            analyze_func=analyze_stage1,
        )

        # 2. Stage 2
        stage2_result = self._run_single_stage(
            stage_label="Stage 2 (Full-text)",
            data_path=self.stage2_data_path,
            analyze_func=analyze_stage2,
        )

        # 3. Assemble raw (unrefined) output
        raw_output: FullResult = {
            "stage1": stage1_result,
            "stage2": stage2_result,
        }

        # 4. Second-level refinement: add final_reason and all_zero_row_count
        self.logger.info(
            "[REFINE] Starting second-level refinement of row_fail_stats "
            "(final_reason / all_zero_row_count)."
        )
        refined_output = refine_exclusion_reasons(
            json_data=raw_output,
            logger=self.logger,
        )

        # 5. Write main JSON
        self._write_main_json(refined_output)

        # 6. Build and write summary JSON
        summary_data = self._build_reason_summary(refined_output)
        self._write_summary_json(summary_data)

        return refined_output


# ---------------------------------------------------------------------------
# Script entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """
    Script entry point: run double-blind exclusion statistics and export both JSON files.
    """
    logger = setup_logger(verbose=True)
    logger.info("[MAIN] Starting double-blind exclusion statistics workflow")

    runner = DoubleBlindExclusionRunner(logger=logger)
    _ = runner.run()

    logger.info("[MAIN] Double-blind exclusion statistics workflow completed")


if __name__ == "__main__":
    main()