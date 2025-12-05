# -*- coding: utf-8 -*-
"""
logger_manager.py

Centralized logging configuration utilities for the project.

This module provides:
---------------------
1. A ModuleContextFilter that can inject a module-specific context
   (module_name) into log records.
2. A LoggerManager with a single entry point `setup_logger` to:
   - Create a logger with both console and file handlers.
   - Use colored logging on the console via `colorlog`.
   - Write logs to a rotating file (overwritten on each run).
   - Apply a consistent log format with timestamps, log level, logger name,
     line number, and message.

Typical usage:
--------------
    from utils.logger_manager import LoggerManager

    logger = LoggerManager.setup_logger(
        logger_name="scopus_elsevier_batch",
        module_name=__name__,
        verbose=True,
    )

This helps ensure consistent logging behavior across all scripts and
facilitates debugging and auditing.

Author: Aiden Cao <zhinengmahua@gmail.com>
Date: 2025-05-22
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import colorlog


class ModuleContextFilter(logging.Filter):
    """
    Logging context filter: injects a `module_name` attribute into LogRecord
    instances for use in log formatting or downstream handlers.
    """

    def __init__(self, module_name: str):
        super().__init__()
        self.module_name = module_name

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Inject the module_name into the log record.

        :param record: The LogRecord to be enriched.
        :return: True to indicate the record should not be filtered out.
        """
        record.module_name = self.module_name
        return True


class LoggerManager:
    """
    Logger manager: provides a unified logger configuration with
    console and rotating file outputs.

    Usage example:
        from utils.logger_manager import LoggerManager
        logger = LoggerManager.setup_logger(
            logger_name="scopus_elsevier_batch",
            module_name=__name__,
            verbose=True,
        )
    """

    @staticmethod
    def setup_logger(logger_name: str, module_name: str, verbose: bool) -> logging.Logger:
        """
        Configure and return a global logger instance.

        Features:
          - Log to both console and file.
          - Console log level is controlled by the `verbose` flag.
          - File logs use a rotating file handler (overwritten on each run),
            with UTF-8 encoding.
          - Log format includes timestamp, level, logger name, line number,
            and message, suitable for audit and debugging.

        :param logger_name: Logger name, also used in the log file name.
        :param module_name: Module name to be injected into log records via
                            ModuleContextFilter, if needed by formatters.
        :param verbose:     If True, console level is DEBUG; otherwise INFO.
        :return:            Configured logging.Logger instance.
        """
        # Create logs directory and log file path
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{logger_name}.log"

        # Create or retrieve the logger
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)

        # Clear existing handlers and filters to avoid duplication
        logger.handlers.clear()
        logger.filters.clear()

        # Create and add context filter at the logger level
        context_filter = ModuleContextFilter(module_name)
        logger.addFilter(context_filter)

        # Base log format: includes logger name and line number
        fmt = "%(asctime)s | %(levelname)-5s | %(name)s:%(lineno)d | %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(fmt, datefmt)

        # Console handler with colored output
        console_level = logging.DEBUG if verbose else logging.INFO
        ch = colorlog.StreamHandler(sys.stdout)
        ch.setLevel(console_level)

        # Color mapping for different log levels
        log_colors = {
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        }
        color_fmt = "%(log_color)s" + fmt  # prepend log_color to the base format
        ch.setFormatter(colorlog.ColoredFormatter(color_fmt, datefmt, log_colors=log_colors))
        logger.addHandler(ch)

        # File handler (rotating file; here we overwrite on each run)
        fh = RotatingFileHandler(
            filename=str(log_file),
            mode="w",  # overwrite previous log on each start
            encoding="utf-8",
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        logger.debug(
            f"Logging system initialized | name={logger_name} | "
            f"console_level={logging.getLevelName(console_level)} | "
            f"log_file={log_file}"
        )

        return logger