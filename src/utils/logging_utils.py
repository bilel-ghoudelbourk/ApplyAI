import logging

from src.config import get_settings


def configure_logging() -> None:
    """Configure a conservative root logger once for CLI and API usage."""
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    log_level = get_settings().logging.level.upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)


def safe_log_text(value: object) -> str:
    """Render logs in ASCII-safe form to avoid Windows console encoding crashes."""
    return str(value).encode("ascii", errors="backslashreplace").decode("ascii")
