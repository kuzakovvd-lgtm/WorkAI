"""Google Sheets client abstraction and implementation."""

from __future__ import annotations

import base64
import importlib
import json
import random
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol, cast

from WorkAI.common import get_logger
from WorkAI.config import GoogleSheetsSettings
from WorkAI.ingest.models import ValueRange

if TYPE_CHECKING:
    from google.oauth2 import service_account


class SheetsClient(Protocol):
    """Protocol to make ingestion testable without Google API."""

    def batch_get_values(
        self,
        spreadsheet_id: str,
        ranges: list[str],
        *,
        value_render_option: str,
        date_time_render_option: str,
    ) -> list[ValueRange]:
        """Fetch values for ranges using one batch request."""


class GoogleApiSheetsClient(SheetsClient):
    """Google Sheets API v4 client implementation."""

    def __init__(
        self,
        service: Any,
        *,
        max_retries: int,
        backoff_base_sec: float,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._service = service
        self._max_retries = max_retries
        self._backoff_base_sec = backoff_base_sec
        self._sleep_fn = sleep_fn
        self._log = get_logger(__name__)

    @classmethod
    def from_settings(cls, settings: GoogleSheetsSettings) -> GoogleApiSheetsClient:
        """Build Google API client from settings."""
        import httplib2  # type: ignore[import-untyped]
        from google_auth_httplib2 import AuthorizedHttp  # type: ignore[import-untyped]
        from googleapiclient.discovery import build  # type: ignore[import-untyped]

        scope = (
            "https://www.googleapis.com/auth/spreadsheets.readonly"
            if settings.read_only
            else "https://www.googleapis.com/auth/spreadsheets"
        )

        credentials = _build_credentials(settings, scope)
        authed_http = AuthorizedHttp(
            credentials=credentials,
            http=httplib2.Http(timeout=settings.request_timeout_sec),
        )

        service = build(
            "sheets",
            "v4",
            http=authed_http,
            cache_discovery=False,
        )

        return cls(
            service,
            max_retries=settings.max_retries,
            backoff_base_sec=settings.backoff_base_sec,
        )

    def batch_get_values(
        self,
        spreadsheet_id: str,
        ranges: list[str],
        *,
        value_render_option: str,
        date_time_render_option: str,
    ) -> list[ValueRange]:
        """Fetch values via spreadsheets.values.batchGet with retry/backoff."""

        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = (
                    self._service.spreadsheets()
                    .values()
                    .batchGet(
                        spreadsheetId=spreadsheet_id,
                        ranges=ranges,
                        valueRenderOption=value_render_option,
                        dateTimeRenderOption=date_time_render_option,
                    )
                    .execute()
                )

                payload = response.get("valueRanges", [])
                value_ranges = [
                    ValueRange(
                        range=str(item.get("range", "")),
                        values=_coerce_values(item.get("values", [])),
                    )
                    for item in payload
                ]
                self._log.info(
                    "gsheets_request_ok",
                    spreadsheet_id=spreadsheet_id,
                    ranges=len(ranges),
                    value_ranges=len(value_ranges),
                    attempt=attempt + 1,
                )
                return value_ranges
            except Exception as exc:
                last_error = exc
                if not _is_retryable(exc) or attempt == self._max_retries:
                    self._log.error(
                        "gsheets_request_failed",
                        spreadsheet_id=spreadsheet_id,
                        ranges=len(ranges),
                        attempt=attempt + 1,
                        error=str(exc),
                    )
                    raise

                sleep_sec = self._backoff_base_sec * (2**attempt) + random.uniform(0.0, 0.1)
                self._log.warning(
                    "gsheets_request_retry",
                    spreadsheet_id=spreadsheet_id,
                    attempt=attempt + 1,
                    max_retries=self._max_retries,
                    sleep_sec=round(sleep_sec, 3),
                    error=str(exc),
                )
                self._sleep_fn(sleep_sec)

        if last_error is not None:
            raise last_error
        raise RuntimeError("Unexpected retry loop exit")


def _build_credentials(
    settings: GoogleSheetsSettings,
    scope: str,
) -> service_account.Credentials:
    from google.oauth2 import service_account

    if settings.service_account_file is not None and settings.service_account_file.strip() != "":
        credentials = service_account.Credentials.from_service_account_file(  # type: ignore[no-untyped-call]
            settings.service_account_file.strip(),
            scopes=[scope],
        )
        return cast(service_account.Credentials, credentials)

    if settings.service_account_json_b64 is not None and settings.service_account_json_b64.strip() != "":
        raw_bytes = base64.b64decode(settings.service_account_json_b64)
        service_account_info = json.loads(raw_bytes.decode("utf-8"))
        credentials = service_account.Credentials.from_service_account_info(  # type: ignore[no-untyped-call]
            service_account_info,
            scopes=[scope],
        )
        return cast(service_account.Credentials, credentials)

    raise ValueError("Google service account credentials are not configured")


def _coerce_values(raw_values: object) -> list[list[Any]]:
    if not isinstance(raw_values, list):
        return []

    rows: list[list[Any]] = []
    for row in raw_values:
        if isinstance(row, list):
            rows.append(row)
        else:
            rows.append([row])
    return rows


def _is_retryable(exc: Exception) -> bool:
    try:
        import httplib2
    except Exception:
        httplib2 = None

    try:
        googleapi_errors = importlib.import_module("googleapiclient.errors")
    except Exception:
        googleapi_errors = None

    google_http_error = (
        None if googleapi_errors is None else getattr(googleapi_errors, "HttpError", None)
    )

    if google_http_error is not None and isinstance(exc, google_http_error):
        status = int(getattr(exc.resp, "status", 0))
        return status == 429 or 500 <= status < 600

    retryable_errors: tuple[type[BaseException], ...] = (ConnectionError, TimeoutError, OSError)
    if httplib2 is not None:
        retryable_errors += (httplib2.HttpLib2Error,)
    return isinstance(exc, retryable_errors)
