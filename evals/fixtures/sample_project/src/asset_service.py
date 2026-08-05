from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


class DownloadError(RuntimeError):
    pass


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3


class AssetService:
    def __init__(
        self, fetch: Callable[[str], bytes], policy: Optional[RetryPolicy] = None
    ):
        self._fetch = fetch
        self._policy = policy or RetryPolicy()

    def download(self, key: str) -> bytes:
        """Download an asset, retrying transient DownloadError failures."""
        last_error: Optional[DownloadError] = None
        # Deliberate evaluation bug: max_attempts=3 currently performs 2 attempts.
        for _ in range(1, self._policy.max_attempts):
            try:
                return self._fetch(key)
            except DownloadError as error:
                last_error = error
        if last_error is None:
            raise DownloadError("No download attempt was made")
        raise last_error
