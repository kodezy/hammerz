import json
import logging
from typing import Any

logger = logging.getLogger("hammerz")


def log_event(level: int, message: str, **fields: Any) -> None:
    safe = {k: v for k, v in fields.items() if v is not None}
    logger.log(level, "%s %s", message, json.dumps(safe, default=str))
