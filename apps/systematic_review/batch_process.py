import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import pandas as pd

from apps.systematic_review.utils.openai_analyzer import OpenAIClient
from llm_slwi.settings import (OPENAI_API_KEY, DEFAULT_MODELS, SYSTEM_PROMPT)
from utils.exceptions import BatchProcessingError, DataValidationError
from utils.logger_manager import LoggerManager


def get_logger(name: str = "paper_batch_processing", verbose: bool = True) -> logging.Logger:
    """
    标准日志器统一获取出口

    :param name: 日志器名称
    :param verbose: 是否 DEBUG 详细日志模式
    :return: logging.Logger 对象
    :raises Exception: 任意异常将被抛出
    """
    try:
        return LoggerManager.setup_logger(
            logger_name=name,
            module_name=__name__,
            verbose=verbose
        )
    except Exception as ex:
        raise RuntimeError(f"CLIConfig logger 初始化失败：{ex}") from ex


@dataclass
class CLIConfig:
    """批量文献分析任务的参数配置类"""

    # 设置项目根目录和数据目录
    project_root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[2])  # 获取项目根目录
    data_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parents[2] / "data/systematic_review/raw")  # 数据目录

    # 配置输入文件和分析结果目录
    input_file: Path = field(default_factory=lambda: Path("merged_and_deduplicated_data.xlsx"))  # Excel 输入文件
    llm_analysis_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parents[2] / "data/systematic_review/llm_results")  # LLM 分析结果目录

    skip_existing: bool = True  # 是否跳过已存在的分析结果
    verbose: bool = True  # 日志详细级别
    enable_llm_analysis: bool = True  # 是否执行 LLM/OpenAI 分析阶段
    workers: int = 1  # 并发线程数（建议 1-5，兼容本地/云端/CI/CD）
    tpm_limit: int = 80000  # LLM Token Per Minute 限流阈值，防止 API 被限流
    batch_size: int = 20  # 批处理大小

    def __post_init__(self):
        """
        参数初始化后自动执行类型、权限、目录有效性等多重校验。

        :raises DataValidationError: 参数类型错误、路径不存在或无写权限时抛出。
        """
        # 校验输入文件是否存在
        if not self.input_file.is_file():
            self.input_file = self.data_dir / self.input_file  # 基于 data_dir 设置 input_file 路径
        if not self.input_file.is_file():
            raise DataValidationError(f"输入文件 {self.input_file} 不存在")

        # 校验输出目录是否可写
        if not self.llm_analysis_dir.exists():
            try:
                self.llm_analysis_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise DataValidationError(f"无法创建分析结果目录：{self.llm_analysis_dir}") from e


class LLMBatchAnalyzer:
    """ 批量文献分析器 """

    def __init__(self, config: CLIConfig, logger: Optional[logging.Logger] = None):
        """
        初始化 LLMBatchAnalyzer。

        :param config: 全局配置对象
        :param logger: 日志对象
        """
        self.config = config
        self.input_file = config.input_file
        self.result_dir = config.llm_analysis_dir
        self.logger = logger or get_logger("llm_batch_analyzer", verbose=config.verbose)
        self.openai_client = self.init_openai_client()
        self.ensure_result_dir()

    def ensure_result_dir(self):
        """
        确保输出目录存在，如不存在则自动创建。

        :raises DataValidationError: 目录无法创建或不可写时抛出
        """
        try:
            self.result_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.critical(f"[输出目录创建失败] {self.result_dir}: {e}")
            raise DataValidationError(f"无法创建分析结果目录：{self.result_dir}") from e

    def init_openai_client(self) -> OpenAIClient:
        """
         初始化 OpenAIClient 分析主控对象。

        :return: OpenAIClient 实例
        :raises DataValidationError: 初始化失败
        """
        try:
            openai_client = OpenAIClient(
                api_key=OPENAI_API_KEY,
                model_map=DEFAULT_MODELS,
                system_prompt=SYSTEM_PROMPT,
                max_workers=self.config.workers,
                tpm_limit=self.config.tpm_limit,
                logger=self.logger,
                stream=False
            )
            self.logger.debug("[流水线初始化] OpenAIClient 初始化成功")
            return openai_client
        except Exception as e:
            self.logger.critical(f"[LLM 分析流水线初始化失败] {e}", exc_info=True)
            raise DataValidationError("无法初始化 OpenAIClient") from e

    def read_excel_file(self) -> pd.DataFrame:
        """
        读取 Excel 文件，并返回 DataFrame。

        :return: DataFrame 包含 "Article Title" 和 "Abstract" 列
        """
        df = pd.read_excel(self.input_file)
        # df = df[:5]
        return df

    def analyze_batch(self, batch_prompts: List[str], batch_titles: List[str], batch_years: List[str], batch_idx: int) -> Path:
        """
        分析单个批次，调用 LLM 并保存为临时 CSV 文件。

        :param batch_prompts: 当前批次的 prompt 文本列表
        :param batch_titles: 当前批次的文件标题列表
        :param batch_years: 当前批次的发表年份列表
        :param batch_idx: 当前批次编号（从 1 开始）
        :return: 本批次结果的临时 CSV 路径
        """
        results = self.call_llm(batch_prompts)
        rows = []
        for title, year, (decision, notes) in zip(batch_titles, batch_years, results):
            # 将结果转换为适合存储的格式
            rows.append({
                "Title": title,
                "Year": year,
                "Decision": decision,
                "Notes": notes
            })
        return self.save_batch_csv(rows, batch_idx)

    def save_batch_csv(self, rows: list, batch_idx: int) -> Path:
        """
        保存单批分析结果为临时 CSV。

        :param rows: 本批次分析结果行数据
        :param batch_idx: 批次编号
        :return: 保存的 CSV 路径
        """
        batch_file = self.result_dir / f"R2_analysis_batch_{batch_idx:03d}.csv"
        df = pd.DataFrame(rows)
        df.to_csv(batch_file, index=False, encoding="utf-8-sig")
        self.logger.info(f"[分批保存] 第 {batch_idx} 批结果已保存为：{batch_file}")
        return batch_file

    def call_llm(self, prompts: List[str]) -> List[tuple]:
        """
        批量调用 LLM/OpenAI 模型接口分析文本。

        :param prompts: 文本内容列表
        :return: LLM 返回的分析结果 [(decision, notes), ...]
        """
        if not prompts:
            self.logger.error("[LLM 调用] 输入为空，无法批量分析。")
            return []
        try:
            results = self.openai_client.review_batch(prompts)
            self.logger.info(f"[LLM 调用] 批量分析完成，返回 {len(results)} 条。")
            return results
        except Exception as e:
            self.logger.critical(f"[OpenAI 批量分析异常] {e}", exc_info=True)
            return [("unsure", "批量分析中断，部分未处理")] * len(prompts)

    def analyze(self):
        """
        批量分析主流程：从 Excel 文件中读取数据，调用 LLM 分析并保存结果。

        1. 读取 Excel 文件内容。
        2. 批量处理标题和摘要，每批调用 OpenAI 进行分析。
        3. 所有批次完成后统一合并为主表 CSV。
        """
        try:
            self.logger.info(f"[启动] Excel → LLM 批量分析，文件={self.input_file}，批大小={self.config.batch_size}")
            start_time = time.time()

            # 步骤 1：读取 Excel 文件内容
            df = self.read_excel_file()
            if df.empty:
                self.logger.error("[启动终止] Excel 文件为空，流程退出。")
                return

            # 步骤 2：提取标题和摘要，并创建批处理
            titles = df["Article Title"].tolist()
            years = df["Publication Year"].tolist()
            abstracts = df["Abstract"].tolist()
            prompts = [f"Title: {title}\n\nAbstract: {abstract}" for title, abstract in zip(titles, abstracts)]

            batch_size = self.config.batch_size
            total = len(prompts)
            batch_csv_paths = []
            self.logger.info(f"[任务准备] 共 {total} 条文本，将分批分析，每批 {batch_size} 条。")

            # 步骤 3：分批处理，独立保存
            for batch_idx, i in enumerate(range(0, total, batch_size), 1):
                batch_prompts = prompts[i: i + batch_size]
                batch_titles = titles[i: i + batch_size]
                batch_years = years[i: i + batch_size]
                self.logger.info(
                    f"========== [批次启动] 批次 {batch_idx:03d}: {i}~{min(i + batch_size, total) - 1} =========="
                )
                batch_csv = self.analyze_batch(batch_prompts, batch_titles, batch_years, batch_idx)
                batch_csv_paths.append(batch_csv)

            # 步骤 4：合并所有批次结果
            self.logger.info("[合并阶段] 开始合并所有批次结果……")
            self.merge_all_batches(batch_csv_paths)

            total_time = time.time() - start_time
            self.logger.info(
                f"[完成] 批量分析与合并全部结束，耗时 {total_time:.2f} 秒，"
                f"最终结果已写入 {self.result_dir}/llm_analysis_results.csv"
            )
        except Exception as exc:
            self.logger.critical(f"[批量分析] 主流程致命异常 {exc}", exc_info=True)
            raise BatchProcessingError(f"主流程致命异常: {exc}") from exc

    def merge_all_batches(self, batch_csv_paths: list):
        """
        合并所有批次 CSV 文件为最终结果主表。

        :param batch_csv_paths: 所有批次结果文件路径
        """
        if not batch_csv_paths:
            self.logger.warning("[合并跳过] 未发现任何批次结果文件。")
            return

        dfs = []
        for file_path in batch_csv_paths:
            df = pd.read_csv(file_path, encoding="utf-8-sig")

            # 对每一行的 'Notes' 列进行标准化 JSON 序列化，并添加缩进格式
            if "Notes" in df.columns:
                df["Notes"] = df["Notes"].apply(
                    lambda x: json.dumps(json.loads(x), ensure_ascii=False, indent=4)
                    if isinstance(x, str) else json.dumps(x, ensure_ascii=False, indent=4)
                )

            dfs.append(df)

        # 合并所有 DataFrame
        total_df = pd.concat(dfs, ignore_index=True)

        # 保存最终的结果
        final_csv = self.result_dir / "llm_analysis_results.csv"
        total_df.to_csv(final_csv, index=False, encoding="utf-8-sig")
        self.logger.info(f"[合并完成] 所有批次已合并为：{final_csv} | 总条目数：{len(total_df)}")


def main():
    """
    批量文献筛选分析主入口。读取 Excel 文件，遍历每一行调用 OpenAI 进行筛选。
    """
    start_time = time.time()

    try:
        config = CLIConfig()
    except DataValidationError as err:
        print(f"[参数异常] {err}")
        sys.exit(1)

    logger = get_logger(verbose=config.verbose)

    # 3. Excel → LLM/OpenAI 批量智能分析流程
    if config.enable_llm_analysis:
        try:
            logger.info("[阶段 2] 启动 Excel → LLM 批量智能分析任务…")
            analyzer = LLMBatchAnalyzer(config, logger=get_logger("llm_batch_analyzer", verbose=config.verbose))
            analyzer.analyze()
            elapsed = time.time() - start_time
            logger.info(f"[阶段 2 完成] LLM 批量分析已结束 | 累计耗时 {elapsed:.2f} 秒")
        except Exception as e:
            logger.critical(f"[阶段 2 异常] LLM 分析致命异常：{e}", exc_info=True)
            sys.exit(3)
    else:
        logger.info("[阶段 2] LLM 批量分析任务已被配置关闭，跳过执行。")

    logger.info("[主流程完成] 全部批处理与分析任务执行完毕。")


if __name__ == "__main__":
    main()