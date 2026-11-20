"""HTTP session dengan retry untuk sumber data eksternal."""

from __future__ import annotations

from collections.abc import Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_STATUS_FORCELIST: tuple[int, ...] = (429, 500, 502, 503, 504)


def build_session(
    user_agent: str | None = None,
    headers: dict[str, str] | None = None,
    retries: int = 3,
    backoff_factor: float = 1.0,
    status_forcelist: Iterable[int] = DEFAULT_STATUS_FORCELIST,
) -> requests.Session:
    """Buat session dengan retry eksponensial untuk error sementara."""
    session = requests.Session()

    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=tuple(status_forcelist),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )

    adapter = HTTPAdapter(max_retries=retry)

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    if user_agent:
        session.headers["User-Agent"] = user_agent

    if headers:
        session.headers.update(headers)

    return session
