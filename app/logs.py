import json
import logging


class JsonFormatter(logging.Formatter):
    """Write each log entry as one line of JSON."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        entry.update(getattr(record, "fields", {}))
        return json.dumps(entry)


def get_logger() -> logging.Logger:
    logger = logging.getLogger("taskboard")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger