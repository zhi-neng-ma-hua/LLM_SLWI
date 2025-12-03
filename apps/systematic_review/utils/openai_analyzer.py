# -*- coding: utf-8 -*-
"""
openai_analyzer.py — 文献自动筛选流水线

支持多批次输入输出，自动分批、自动去重、自动主键管理、自动 Prompt 拼接、OpenAI 多轮判定、结果全流程日志追踪。
所有参数、路径、字段均可配置，支持云端、集群、本地一键部署与 CI/CD 自动化。
适用于高可靠系统综述、批量科研数据集管理、NLP/AI 医学应用等场景。

作者：智能麻花 <zhinengmahua@gmail.com>
日期：2025-05-22
"""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import backoff
import tiktoken
from openai import (
    OpenAI,
)

from llm_slwi.settings import (PRICE_PER_1K_TOKENS)
from apps.systematic_review.utils.exceptions import DataValidationError
from apps.systematic_review.utils.logger_manager import LoggerManager


class Decision(str, Enum):
    """
    文献筛选结果枚举类

    定义在文献筛选（"include/exclude/unsure"）流程中可能出现的 3 种决策状态，
    并提供从原始字符串安全转换到枚举值的方法，确保异常输入时返回 UNSURE 并记录警告日志。
    """

    INCLUDE = "include"
    """包含：该文献满足所有纳入标准，应纳入系统评价。"""

    EXCLUDE = "exclude"
    """排除：该文献不满足至少一项关键纳入标准，应排除。"""

    UNSURE = "unsure"
    """不确定：信息不足以判断是否纳入，或模型返回格式异常时的默认结果。"""

    @classmethod
    def from_raw(cls, raw_label: str) -> "Decision":
        """
        将原始字符串转换为 Decision 枚举实例。

        在实际业务场景中，从模型返回的 JSON 可能含大小写不一致或多余空白，
        本方法会统一进行 strip() 和 lower() 处理，并尝试匹配合法枚举值。
        若无法匹配，则记录 WARNING 级别日志并返回 Decision.UNSURE，以保证上层流程不会因意外标签崩溃。

        :param raw_label: 来自模型或外部输入的原始标签字符串
        :return: 对应的 Decision 枚举；若标签不合法，则为 Decision.UNSURE
        """
        if raw_label is None:
            logging.getLogger(__name__).warning("未提供决策标签(raw_label=None)，返回 Decision.UNSURE")
            return cls.UNSURE

        normalized = raw_label.strip().lower()
        if normalized in cls._value2member_map_:
            return cls(normalized)

        logging.getLogger(__name__).warning(f"无效的决策标签 '{raw_label}'，已默认返回 Decision.UNSURE。")
        return cls.UNSURE


@dataclass
class CLIConfig:
    """
    文献自动筛选与评审批量流水线参数配置核心类


    workers (int): 并发线程数，建议 1-5，兼容云/本地/CI/CD。
    tpm_limit (int): Token Per Minute 限流阈值，防止 API 调用被限。
    """
    workers: int = 1  # 建议 1-5，生产环境限流友好
    tpm_limit: int = 30000  # 每分钟最大 token 限流，过小会导致限流等待

    def __post_init__(self):

        # -校验性能参数
        if not (isinstance(self.workers, int) and self.workers >= 1):
            raise DataValidationError("[配置校验] workers 必须为正整数。")
        if not (isinstance(self.tpm_limit, int) and self.tpm_limit > 0):
            raise DataValidationError("[配置校验] tpm_limit 必须为正整数。")


class OpenAIClient:
    """
    OpenAI GPT 访问封装类

    本类负责与 OpenAI API 的交互，提供以下核心功能：
      1. TPM（Tokens-Per-Minute）限流：确保请求速率不超过配额，避免 API 报限。
      2. Backoff 重试：针对常见的 RateLimit、网络/服务器错误，自动进行指数退避重试。
      3. 费用统计：根据返回的 token 使用量，计算累计费用，便于成本监控与汇报。
      4. 并发安全：在多线程环境（ThreadPoolExecutor）下依旧生效的限流与计费逻辑。
      5. JSON 结果解析：对模型返回的 JSON 进行严格校验，确保 decision 字段合法。

    参数：
      api_key      : OpenAI API 密钥（字符串，不应硬编码在源码中，应从安全存储或环境变量中读取）。
      model_map    : 三阶段模型字典，例如 {"stage1": "gpt-4.1-mini", "stage2": "gpt-4.1", "stage3": "gpt-4o"}。
      system_prompt: 系统提示词（字符串），在每次调用时作为 role="system" 消息传入。
      temperature  : 调用 GPT 时的采样温度 (0.0 – 1.0)，默认为 0.0 保证确定性输出。
      max_workers  : 并发线程数；若 <= 1 则串行执行
      max_retries  : 在发生 RateLimit 或网络错误时，允许的最大重试次数，默认为 8 次。
      tpm_limit    : Token-Per-Minute 上限（整数，单位：tokens/分钟），None 表示不进行限流。
      logger       : logging.Logger 实例，用于输出日志；若为 None，则使用默认 LoggerManager 生成的 Logger。
      stream       : 是否使用流式返回模式（bool，默认为 False）。流式返回时不统计 usage。

    使用示例：
        client = OpenAIClient(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_map=DEFAULT_MODELS,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.0,
            max_workers=1,
            max_retries=5,
            tpm_limit=80000,
            logger=logger,
            stream=False
        )
        decision, notes = client.review_single("论文标题\n\n摘要文本")
    """

    def __init__(
            self,
            api_key: str,
            model_map: Dict[str, str],
            system_prompt: str,
            temperature: float = 0.0,
            max_workers: int = 1,
            max_retries: int = 8,
            tpm_limit: Optional[int] = None,
            logger: Optional[logging.Logger] = None,
            stream: bool = False,
    ):
        # OpenAI 客户端与基础配置
        self.client = OpenAI(api_key=api_key)
        self.model_map = model_map
        self.system_prompt = system_prompt.strip()
        self.temperature = temperature
        self.max_retries = max_retries
        self.max_workers = max_workers
        self.tpm_limit = tpm_limit
        self.stream = stream

        # Logger 初始化：若外部未提供，则使用 LoggerManager 创建
        self.logger = logger or LoggerManager.setup_logger(
            logger_name="openai_client",
            module_name=__name__,
            verbose=False
        )

        # 限流与计费状态
        # _call_timestamps 存储最近 60 秒内已发送的 (timestamp, token_count)
        self.call_timestamps: List[Tuple[float, int]] = []
        self.total_tokens: int = 0  # 累计已使用 token 数
        self.total_cost: float = 0.0  # 累计费用 (USD)

        # 编码器缓存：避免重复创建 tiktoken.Encoding
        self.encoding_cache: Dict[str, tiktoken.Encoding] = {}

    def review_single(self, text: str) -> Tuple[Decision, str]:
        """
        对单条文本执行 "三阶段" 筛选：依次调用 stage1、stage2、stage3 模型。
        若某阶段直接返回 include 或 exclude，则提前停止；否则在第三阶段结束后返回 unsure。

        :param text: 已拼接好的 prompt 文本，由标题、摘要等字段以 "\n\n" 分隔得到
        :return: (Decision, notes)：
                 - Decision：枚举值 include / exclude / unsure
                 - notes：辅助说明，通常为模型返回的 notes 字段，或说明异常原因
        """
        # for stage in ["stage1", "stage2", "stage3"]:
        for stage in ["stage3"]:
            model_name = self.model_map.get(stage)
            if not model_name:
                # 模型未在配置中找到，记录错误并返回 UNSURE
                self.logger.error(f"模型映射缺失：stage='{stage}' 未配置具体模型名称")
                return Decision.UNSURE, "模型配置缺失"

            decision, notes = self.call_with_retries(text, model_name)
            if decision != Decision.UNSURE or stage == "stage3":
                return decision, notes

        # 理论上不会到达此处，但做兜底处理
        return Decision.UNSURE, "未知逻辑错误"

    def review_batch(self, texts: List[str]) -> List[Tuple[Decision, str]]:
        """
        批量并行调用 review_single，实现多线程并发处理。

        :param texts: 待处理的 prompt 文本列表
        :return: 与 texts 等长的 (Decision, notes) 结果列表，顺序与输入一致
        """
        if self.max_workers <= 1:
            # 串行执行
            return [self.review_single(t) for t in texts]

        results: List[Tuple[Decision, str]] = [(Decision.UNSURE, "")] * len(texts)
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_index = {
                executor.submit(self.review_single, txt): idx
                for idx, txt in enumerate(texts)
            }
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    # 捕获子线程意外异常，记录日志后返回 UNSURE
                    self.logger.error(f"并发调用第 {idx} 条时发生异常：{e}", exc_info=True)
                    results[idx] = (Decision.UNSURE, "并发处理异常")
        return results

    def rate_limit(self, tokens_requested: int):
        """
        TPM (Tokens-Per-Minute) 限流实现：若过去 60 秒内累计请求的 token 数 + 当前请求的 token 数
        超过 self._tpm_limit，则阻塞等待直到可以发送。

        :param tokens_requested: 本次请求预计消耗的 token 数（仅 prompt 部分，不含 completion）
        """
        if not self.tpm_limit: return

        now = time.time()
        # 1. 清理 60 秒前的历史记录
        self.call_timestamps = [(ts, tok) for (ts, tok) in self.call_timestamps if now - ts < 60.0]
        used_last_minute = sum(tok for (_, tok) in self.call_timestamps)

        if used_last_minute + tokens_requested > self.tpm_limit:
            # 2. 算还需等待多久
            earliest_ts = min(ts for (ts, _) in self.call_timestamps)
            wait_seconds = 60.0 - (now - earliest_ts) + 0.05  # 加 50ms 缓冲
            self.logger.debug(
                f"触发 TPM 限流：过去 60s 已使用 {used_last_minute} tokens，本次需 {tokens_requested} tokens，"
                f"等待 {wait_seconds:.2f}s 后再发送请求")
            time.sleep(wait_seconds)

        # 3. 记录这次调用
        self.call_timestamps.append((now, tokens_requested))

    def calculate_cost(self, model: str, used_tokens: int) -> float:
        """
        根据使用的 token 数与模型对应单价，计算本次调用的费用（单位 USD），
        并将其累加到 self.total_cost。

        :param model: 模型名称，用于从 PRICE_PER_1K_TOKENS 中获取价格
        :param used_tokens: 本次调用消耗的 token 数（prompt + completion）
        :return: 本次调用的费用（美元）
        """
        unit_price = PRICE_PER_1K_TOKENS.get(model, 0.005)
        cost = unit_price * (used_tokens / 1000.0)
        self.total_cost += cost
        return cost

    def get_token_encoder(self, model: str) -> tiktoken.Encoding:
        """
        获取与指定模型对应的 tiktoken.Encoding，用于计算 token 数。
        支持主流 OpenAI model，如找不到则回退到 cl100k_base。

        :param model: 模型名称，例如 "gpt-4.1-mini"
        :return: 对应的 tiktoken.Encoding 实例
        """
        if model in self.encoding_cache:
            return self.encoding_cache[model]

        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")

        self.encoding_cache[model] = enc
        return enc

    def call_with_retries(self, text: str, model: str) -> Tuple[Decision, str]:
        """
        对单次模型调用添加 backoff 重试策略，捕获常见的 RateLimitError、APIError、连接中断等，
        在重试达到 max_retries 前自动进行指数退避，最终返回 (decision, notes)。

        :param text: prompt 文本
        :param model: 模型名称
        :return: (Decision, notes)
        """

        @backoff.on_exception(
            backoff.expo,
            Exception,
            base=2,
            factor=1.8,
            jitter=backoff.full_jitter,
            max_tries=self.max_retries,
        )
        def inner_call() -> Tuple[Decision, str]:
            return self.invoke_model(text=text, model=model)

        try:
            return inner_call()
        except Exception as e:
            # 若重试仍然失败，记录 ERROR 并返回 UNSURE
            self.logger.error(f"模型 '{model}' 最终调用失败，异常信息：{e}", exc_info=True)
            return Decision.UNSURE, "模型调用失败"

    def invoke_model(self, text: str, model: str) -> Tuple[Decision, str]:
        """
        真正向 OpenAI API 发起请求，并完成以下步骤：
          1. 计算 prompt（system_prompt + text）共计需要的 token 数，用于限流。
          2. 进行 TPM 限流。
          3. 调用 OpenAI chat.completions.create，支持流式与非流式。
          4. 统计返回 usage（prompt_tokens + completion_tokens），更新 total_tokens 与 total_cost。
          5. 解析 response 中 content（JSON 字符串），提取 decision 与 notes 并校验。

        :param text: 用户输入的 prompt 文本
        :param model: 模型名称
        :return: (Decision, notes)
        :raises APIConnectionError, APIError, InternalServerError, RateLimitError, Timeout:
                 当调用发生可重试异常时，由上层 backoff 机制捕获并重试。
        """
        # 1. 计算 prompt 所需 tokens
        encoder = self.get_token_encoder(model)
        system_tokens = len(encoder.encode(self.system_prompt))
        text_tokens = len(encoder.encode(text))
        total_prompt_tokens = system_tokens + text_tokens

        # 2. TPM 限流
        self.rate_limit(total_prompt_tokens)

        # 3. 发起 API 请求
        try:
            response = self.client.chat.completions.create(
                model=model,
                temperature=self.temperature,
                stream=self.stream,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": text},
                ],
            )
        except Exception as e:
            # 捕获所有调用时异常，记录 DEBUG 级日志，并向上抛出以便触发重试
            self.logger.debug(f"调用 OpenAI 接口抛出异常 (model={model})：{e}", exc_info=True)
            raise

        # 4. 解析返回内容
        if self.stream:
            # 流式模式：累积 chunk 中的 delta.content
            content_accumulator = ""
            for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    content_accumulator += delta.content
            text_response = content_accumulator
            usage = getattr(response, "usage", None)  # 流式模式下 usage 可能为 None
        else:
            # 非流式模式：直接取第一个 choice 的 message.content
            text_response = response.choices[0].message.content
            usage = response.usage

        # 5. 更新 token 计数与费用统计（若 usage 可用）
        if usage:
            used_tokens = usage.prompt_tokens + usage.completion_tokens
            self.total_tokens += used_tokens
            cost = self.calculate_cost(model, used_tokens)
            self.logger.debug(
                f"模型='{model}' 本次使用 tokens={used_tokens}，累计 tokens={self.total_tokens}，"
                f"本次费用=${cost:.6f}，累计费用=${self.total_cost:.6f}"
            )

        # 6. 将模型返回的 JSON 字符串解析为 Python 对象
        try:
            parsed = json.loads(text_response)
            raw_decision = parsed.get("decision", "")
            notes = parsed.get("notes", {})
        except (json.JSONDecodeError, ValueError) as e:
            # 若解析失败，记录 WARNING 并直接返回 UNSURE
            self.logger.warning(f"模型返回内容无法解析为 JSON (model={model})：{e}")
            return Decision.UNSURE, "返回格式非 JSON"

        # 7. 规范化并校验 decision 字段
        decision_label = raw_decision.strip().lower()
        if decision_label not in Decision._value2member_map_:
            self.logger.warning(f"模型 '{model}' 返回非法 decision 值：'{raw_decision}'")
            return Decision.UNSURE, "返回 decision 非法"

        return Decision(decision_label), json.dumps(notes)
