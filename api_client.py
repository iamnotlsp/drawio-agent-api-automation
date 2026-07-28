import json
import logging
from time import perf_counter

import allure
import requests


logger = logging.getLogger(__name__)

SENSITIVE_KEYWORDS = (
    "authorization",
    "password",
    "token",
    "cookie",
    "secret",
    "api_key",
    "apikey",
)
MAX_LOG_BODY_LENGTH = 2000


def _mask_sensitive(value):
    if isinstance(value, dict):
        return {
            key: (
                "***"
                if any(keyword in str(key).lower() for keyword in SENSITIVE_KEYWORDS)
                else _mask_sensitive(item)
            )
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [_mask_sensitive(item) for item in value]

    return value


def _truncate(value):
    if len(value) <= MAX_LOG_BODY_LENGTH:
        return value

    return f"{value[:MAX_LOG_BODY_LENGTH]}...<truncated>"


def _format_response_body(response):
    try:
        body = json.dumps(
            _mask_sensitive(response.json()),
            ensure_ascii=False,
            default=str
        )
    except ValueError:
        body = response.text

    return _truncate(body.replace("\r", "\\r").replace("\n", "\\n"))


def _attach_json(name, value):
    allure.attach(
        json.dumps(
            _mask_sensitive(value),
            ensure_ascii=False,
            indent=2,
            default=str
        ),
        name=name,
        attachment_type=allure.attachment_type.JSON
    )


class ApiClient:

    def __init__(self, base_url, timeout=5):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

        self.session.headers.update({
            "Accept": "application/json"
        })

    def request(self, method, path, **kwargs):
        with allure.step(
                f"HTTP {method.upper()} {path}"
        ):
            return self._request(method, path, **kwargs)

    def _request(self, method, path, **kwargs):
        timeout = kwargs.pop("timeout", self.timeout)
        url = f"{self.base_url}/{path.lstrip('/')}"

        logger.info(
            "HTTP request method=%s url=%s timeout=%ss",
            method.upper(),
            url,
            timeout
        )
        logger.debug(
            "HTTP request details params=%s json=%s",
            _mask_sensitive(kwargs.get("params")),
            _mask_sensitive(kwargs.get("json"))
        )
        _attach_json(
            f"请求 {method.upper()} {path}",
            {
                "method": method.upper(),
                "url": url,
                "timeoutSeconds": timeout,
                "params": kwargs.get("params"),
                "json": kwargs.get("json")
            }
        )

        started_at = perf_counter()

        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=timeout,
                **kwargs
            )
        except requests.RequestException as exc:
            elapsed_ms = (perf_counter() - started_at) * 1000
            logger.exception(
                "HTTP request failed method=%s url=%s elapsed_ms=%.2f",
                method.upper(),
                url,
                elapsed_ms
            )
            allure.attach(
                str(exc),
                name=f"请求异常 {method.upper()} {path}",
                attachment_type=allure.attachment_type.TEXT
            )
            raise

        elapsed_ms = (perf_counter() - started_at) * 1000
        logger.info(
            "HTTP response method=%s url=%s status=%s elapsed_ms=%.2f body=%s",
            method.upper(),
            url,
            response.status_code,
            elapsed_ms,
            _format_response_body(response)
        )
        try:
            response_body = response.json()
        except ValueError:
            response_body = response.text

        _attach_json(
            f"响应 {method.upper()} {path}",
            {
                "statusCode": response.status_code,
                "elapsedMilliseconds": round(elapsed_ms, 2),
                "body": response_body
            }
        )

        return response

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, json=None, **kwargs):
        return self.request("POST", path, json=json, **kwargs)

    def close(self):
        self.session.close()
