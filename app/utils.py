import logging
import os
import json
import random
import string
import time
from collections import defaultdict, deque
from threading import Lock
from datetime import datetime, timedelta
from typing import Any, Optional
import ipaddress
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session
from fastapi import Request, status

from app.models.url import URLModel


BASE62_CHARS = string.ascii_letters + string.digits
BASE = len(BASE62_CHARS)

_rate_buckets: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_rate_lock = Lock()


RATE_WINDOW_SECONDS = int(os.getenv("RATE_WINDOW_SECONDS", "60"))
SHORTEN_RATE_LIMIT = int(os.getenv("SHORTEN_RATE_LIMIT", "30"))
REDIRECT_RATE_LIMIT = int(os.getenv("REDIRECT_RATE_LIMIT", "300"))

_rate_buckets: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_rate_lock = Lock()


def _is_rate_limited(ip: str, bucket: str, limit: int) -> bool:
    now = time.time()
    boundary = now - RATE_WINDOW_SECONDS
    key = (ip, bucket)

    with _rate_lock:
        timestamps = _rate_buckets[key]
        while timestamps and timestamps[0] < boundary:
            timestamps.popleft()
        if len(timestamps) >= limit:
            return True
        timestamps.append(now)
    return False


def service_error(status_code: int, code: str, message: str) -> None:
    """Raise an HTTPException with structured detail for uniform API errors."""
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def _error_payload(request: Request, code: str, message: str) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": getattr(request.state, "request_id", "unknown"),
        }
    }


def _is_private_or_local_hostname(hostname: str | None) -> bool:
    if not hostname:
        return True

    host = hostname.strip().lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True
    if host.endswith(".local"):
        return True

    try:
        ip = ipaddress.ip_address(host)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        )
    except ValueError:
        return False


RATE_WINDOW_SECONDS = int(os.getenv("RATE_WINDOW_SECONDS", "60"))
SHORTEN_RATE_LIMIT = int(os.getenv("SHORTEN_RATE_LIMIT", "30"))
REDIRECT_RATE_LIMIT = int(os.getenv("REDIRECT_RATE_LIMIT", "300"))


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _is_suspicious_user_agent(user_agent: str | None) -> bool:
    if not user_agent:
        return True
    ua = user_agent.lower()
    blocked_markers = ["sqlmap", "nikto", "masscan", "nmap", "curl/"]
    return any(marker in ua for marker in blocked_markers)


def _enforce_client_guard(request: Request) -> None:
    user_agent = request.headers.get("user-agent")
    if _is_suspicious_user_agent(user_agent):
        service_error(
            status_code=status.HTTP_403_FORBIDDEN,
            code="blocked_client",
            message="Request blocked by client protection policy",
        )


def enforce_shorten_guard(request: Request) -> None:
    _enforce_client_guard(request)
    if _is_rate_limited(_client_ip(request), "shorten", SHORTEN_RATE_LIMIT):
        service_error(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="rate_limit_exceeded",
            message="Rate limit exceeded for URL shortening",
        )


def enforce_redirect_guard(request: Request) -> None:
    _enforce_client_guard(request)
    if _is_rate_limited(_client_ip(request), "redirect", REDIRECT_RATE_LIMIT):
        service_error(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="rate_limit_exceeded",
            message="Rate limit exceeded for redirects",
        )


class AppLogger:
    """
    Centralized structured logger for the application.
    Logs to both file and console in JSON format.
    """

    LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
    LOG_FILE = os.path.join(LOG_DIR, "app.log")

    def __init__(self, name: str = "url_shortener"):
        if not os.path.exists(self.LOG_DIR):
            os.makedirs(self.LOG_DIR, exist_ok=True)

        self.logger = logging.getLogger(name)

        if not self.logger.handlers:
            file_handler = logging.FileHandler(self.LOG_FILE)
            stream_handler = logging.StreamHandler()

            formatter =  logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
            ) # pure JSON

            file_handler.setFormatter(formatter)
            stream_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.logger.addHandler(stream_handler)

            self.logger.setLevel(logging.INFO)

    # 🔹 Core structured log method
    def _log(self, level, message, request=None, **kwargs):
        log_data = {
            "message": message,
            **kwargs,
        }

        if request:
            log_data.update(
                {
                    "request_id": getattr(request.state, "request_id", None),
                    "path": str(request.url.path),
                    "method": request.method,
                }
            )

        self.logger.log(level, json.dumps(log_data))

    # 🔹 Log levels
    def info(self, message, request=None, **kwargs):
        self._log(logging.INFO, message, request, **kwargs)

    def warning(self, message, request=None, **kwargs):
        self._log(logging.WARNING, message, request, **kwargs)

    def error(self, message, request=None, **kwargs):
        self._log(logging.ERROR, message, request, **kwargs)

    def debug(self, message, request=None, **kwargs):
        self._log(logging.DEBUG, message, request, **kwargs)

    def exception(self, message, request=None, **kwargs):
        log_data = {
            "message": message,
            **kwargs,
        }

        if request:
            log_data["request_id"] = getattr(request.state, "request_id", None)

        self.logger.exception(json.dumps(log_data))

    def get_logger(self):
        return self


def get_record_by_field(
    db: Session, model: Any, field: str, value: Any
) -> Optional[Any]:
    """
    Generic utility to fetch a record from the database by a given field and value.
    Example: get_record_by_field(db, URLModel, 'long_url', long_url)
    """
    logger = AppLogger()
    try:
        logger.info(
            f"Querying database for {model.__name__} where {field} = {value}"
        )
        return db.query(model).filter(getattr(model, field) == value).first()
    except Exception as e:
        logger.exception(
            f"Error querying database for {model.__name__} where {field} = {value}. Error: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


def get_expiry_date(expiry: Optional[int]) -> Optional[datetime]:
    """
    Utility to calculate the expiry datetime based on the provided expiry duration in seconds.
    If expiry is None, it returns None (indicating no expiration).
    """
    logger = AppLogger()
    if expiry:
        try:
            expiry_dt = datetime.fromisoformat(expiry)
            if expiry_dt < datetime.now():
                logger.warning(
                    f"Provided expiry date {expiry} is in the past. Setting expiry to 30 days from now."
                )
                expiry_dt = datetime.now() + timedelta(days=30)
        except Exception:
            logger.warning(
                f"Invalid expiry format: {expiry}, using default 30 days."
            )
            expiry_dt = datetime.now() + timedelta(days=30)
    else:
        expiry_dt = datetime.now() + timedelta(days=30)
    return expiry_dt


def generate_code(length: int = 7) -> str:
    """
    Generate a random Base62 short code.
    """
    return "".join(random.choices(BASE62_CHARS, k=length))


def generate_unique_code(db: Session, max_retries: int = 5) -> str:
    """
    Generate a unique short_code by checking DB.
    """
    for _ in range(max_retries):
        code = generate_code()
        # Check if the generated code already exists in the database
        exists = (
            db.query(URLModel.id).filter(URLModel.short_code == code).first()
        )
        # If it doesn't exist, return the code
        if not exists:
            return code

    raise Exception("Failed to generate unique short code after retries")
