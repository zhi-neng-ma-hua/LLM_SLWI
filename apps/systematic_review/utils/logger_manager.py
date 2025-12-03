import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import colorlog


class ModuleContextFilter(logging.Filter):
    """
    日志记录上下文过滤器：为 LogRecord 注入 module_name 属性。
    """

    def __init__(self, module_name: str):
        super().__init__()
        self.module_name = module_name

    def filter(self, record: logging.LogRecord) -> bool:
        # 注入 module_name 到 record
        record.module_name = self.module_name
        return True


class LoggerManager:
    """
    日志管理器：提供统一的日志配置方法，支持控制台和滚动文件输出。

    用法示例:
        from utils.logger_manager import LoggerManager
        logger = LoggerManager.setup_logger(name="scopus_elsevier_batch", verbose=True)
    """

    @staticmethod
    def setup_logger(logger_name: str, module_name: str, verbose: bool) -> logging.Logger:
        """
        配置并返回全局日志记录器。

        功能：
          - 同时向控制台和文件输出日志；
          - 控制台日志级别根据 verbose 参数动态设置；
          - 文件日志使用滚动写入，按大小切割，保留历史日志；
          - 日志格式包含时间、级别与消息，满足企业级审计需求。

        :param logger_name: 日志器名称，用于区分不同脚本及日志文件名。
        :param module_name: 注入到日志输出的模块名，用于格式化显示 "module_name:lineno"。
        :param verbose: 是否启用 DEBUG 级别日志，否则使用 INFO 级别。
        :return: 已配置的 logging.Logger 实例。
        """
        # 创建日志目录和文件
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{logger_name}.log"

        # 创建或获取 Logger
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        # 清除已有 Handlers & Filters，避免重复
        logger.handlers.clear()
        logger.filters.clear()

        # 创建并添加 Filter（logger 级别）
        context_filter = ModuleContextFilter(module_name)
        logger.addFilter(context_filter)

        # 日志格式，使用 module_name 而非 record.name
        fmt = "%(asctime)s | %(levelname)-5s | %(name)s:%(lineno)d | %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(fmt, datefmt)

        # 控制台输出 Handler
        console_level = logging.DEBUG if verbose else logging.INFO
        ch = colorlog.StreamHandler(sys.stdout)
        ch.setLevel(console_level)
        # colorlog 提供了现成的 ColoredFormatter
        log_colors = {
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        }
        color_fmt = "%(log_color)s" + fmt  # 在原 fmt 前加上 log_color
        ch.setFormatter(colorlog.ColoredFormatter(color_fmt, datefmt, log_colors=log_colors))
        logger.addHandler(ch)

        # 文件输出 Handler（滚动文件）
        fh = RotatingFileHandler(
            filename=str(log_file),
            mode="w",  # 每次启动覆盖旧日志
            encoding="utf-8"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        logger.debug(
            f"日志系统初始化完成 | name={logger_name} | 控制台级别={logging.getLevelName(console_level)} | 文件路径={log_file}"
        )

        return logger
