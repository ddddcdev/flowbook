"""
Logging configuration for flowbook.

Controlled via environment variables:
- FLOWBOOK_LOG_LEVEL: DEBUG, INFO, WARNING, ERROR (default: INFO)
- FLOWBOOK_LOG_FORMAT: json, text (default: json)
- FLOWBOOK_LOG_FILE: file path (default: unset, stdout only)
- FLOWBOOK_LOG_LOGGER_NAME: logger name prefix in output (default: flowbook).
  Set to empty string to hide flowbook branding in client environments.
- FLOWBOOK_LOG_COLOR: 1/true/on to enable ANSI color (default: off).
  Applies to stdout; file output is never colored.
- FLOWBOOK_LOG_JSON_INDENT: 1/true/on to pretty-print JSON (default: off).
  For development readability; use compact (off) for production/log aggregation.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime


def _resolve_logger_name(record_name: str, prefix: str) -> str:
    """Replace 'flowbook' prefix in logger name with configured prefix."""
    if record_name.startswith("flowbook."):
        suffix = record_name[len("flowbook.") :]
        return f"{prefix}.{suffix}" if prefix else suffix
    return record_name


class JsonFormatter(logging.Formatter):
    """Format log records as JSON. Includes extra fields for structured logging."""

    def __init__(
        self,
        logger_name_prefix: str = "flowbook",
        indent: int | None = None,
    ) -> None:
        super().__init__()
        self._logger_name_prefix = logger_name_prefix
        self._indent = indent

    def format(self, record: logging.LogRecord) -> str:
        log_dict: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": _resolve_logger_name(record.name, self._logger_name_prefix),
            "message": record.getMessage(),
        }
        # Include standard record fields that might be useful
        if record.exc_info:
            log_dict["exc_info"] = self.formatException(record.exc_info)
        # Include extra fields (run_id, entity_key, artifact_path, step, status, etc.)
        # Exclude internal logging fields for cleaner JSON
        skip = {
            "message",
            "asctime",
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "pathname",
            "module",
            "lineno",
            "funcName",
            "levelname",
            "levelno",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "taskName",
            "stack_info",
            "exc_info",
            "exc_text",
        }
        for key, value in record.__dict__.items():
            if key not in skip:
                log_dict[key] = value
        return json.dumps(log_dict, ensure_ascii=False, indent=self._indent)


class TextFormatter(logging.Formatter):
    """Traditional text format with optional logger name replacement."""

    def __init__(self, logger_name_prefix: str = "flowbook") -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)s %(logger_display)s - %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
        self._logger_name_prefix = logger_name_prefix

    def format(self, record: logging.LogRecord) -> str:
        record.logger_display = _resolve_logger_name(record.name, self._logger_name_prefix)
        base = super().format(record)
        extras = []
        skip = {
            "message",
            "asctime",
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "logger_display",
        }
        for key, value in record.__dict__.items():
            if key not in skip and value is not None:
                extras.append(f"{key}={value}")
        if extras:
            base += " " + " ".join(extras)
        return base


class _ColoredStreamHandler(logging.StreamHandler):
    """StreamHandler that prepends ANSI color by level when FLOWBOOK_LOG_COLOR is set.
    Uses rich.Console when available (handles uvicorn reload subprocess); else raw ANSI.
    """

    _RESET = "\033[0m"
    _LEVEL_COLORS = {
        logging.DEBUG: "\033[2m",  # dim
        logging.INFO: "\033[32m",  # green
        logging.WARNING: "\033[33m",  # yellow
        logging.ERROR: "\033[31m",  # red
    }
    _RICH_STYLES = {
        logging.DEBUG: "dim",
        logging.INFO: "green",
        logging.WARNING: "yellow",
        logging.ERROR: "red",
    }

    def __init__(self, stream=None, use_color: bool = False) -> None:
        super().__init__(stream)
        self._use_color = use_color
        self._rich_console = None
        if use_color:
            try:
                from rich.console import Console

                self._rich_console = Console(
                    file=stream or sys.stdout,
                    force_terminal=True,
                    no_color=False,
                )
            except ImportError:
                pass

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            if self._use_color:
                if self._rich_console is not None:
                    style = self._RICH_STYLES.get(record.levelno, "")
                    self._rich_console.print(
                        f"[{record.levelname}] {msg}",
                        style=style,
                        markup=False,
                        highlight=False,
                    )
                    return
                color = self._LEVEL_COLORS.get(record.levelno, self._RESET)
                msg = f"{color}[{record.levelname}]{self._RESET} {msg}"
            self.stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


class _FlowbookFilter(logging.Filter):
    """Only allow flowbook.* loggers to pass. Drops third-party noise (e.g. python_multipart)."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.name.startswith("flowbook")


def configure_logging() -> None:
    """
    Configure logging from environment variables.
    Call once at application startup (e.g. FastAPI lifespan).
    Only flowbook.* loggers are output; third-party libs (python_multipart, etc.) are filtered out.
    """
    level_str = os.environ.get("FLOWBOOK_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)

    fmt_str = os.environ.get("FLOWBOOK_LOG_FORMAT", "json").lower()
    logger_name = os.environ.get("FLOWBOOK_LOG_LOGGER_NAME", "flowbook")
    file_path = os.environ.get("FLOWBOOK_LOG_FILE")
    color_str = os.environ.get("FLOWBOOK_LOG_COLOR", "").lower()
    use_color = color_str in ("1", "true", "on")
    indent_str = os.environ.get("FLOWBOOK_LOG_JSON_INDENT", "").lower()
    json_indent = 2 if indent_str in ("1", "true", "on") else None

    if fmt_str == "json":
        formatter: logging.Formatter = JsonFormatter(
            logger_name_prefix=logger_name,
            indent=json_indent,
        )
    else:
        formatter = TextFormatter(logger_name_prefix=logger_name)

    flowbook_logger = logging.getLogger("flowbook")
    flowbook_logger.setLevel(level)
    flowbook_logger.propagate = False
    # Clear existing handlers to avoid duplicates on repeated configure
    for h in flowbook_logger.handlers[:]:
        flowbook_logger.removeHandler(h)

    stream_handler = _ColoredStreamHandler(sys.stdout, use_color=use_color)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(_FlowbookFilter())
    flowbook_logger.addHandler(stream_handler)

    if file_path:
        try:
            file_handler = logging.FileHandler(file_path, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            file_handler.addFilter(_FlowbookFilter())
            flowbook_logger.addHandler(file_handler)
        except OSError:
            flowbook_logger.warning("Could not open log file %s, logging to stdout only", file_path)


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the given name. Use flowbook.* for consistency."""
    return logging.getLogger(name)
