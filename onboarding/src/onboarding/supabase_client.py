"""Minimal Supabase REST (PostgREST) client. Returns lists of dicts, not
DataFrames -- no pandas dependency in this package. Requires the
SERVICE role key, not anon."""

from __future__ import annotations

import os

import requests

PAGE_SIZE = 1000


class SupabaseRestClient:
    def __init__(self, url: str, service_key: str, timeout_s: float = 30.0):
        self._base = url.rstrip("/") + "/rest/v1"
        self._headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}
        self._timeout_s = timeout_s

    def fetch_table(self, table: str, filters: dict[str, str] | None = None,
                     select: str = "*") -> list[dict]:
        params: dict[str, str] = {"select": select}
        if filters:
            params.update(filters)

        rows: list[dict] = []
        offset = 0
        while True:
            resp = requests.get(f"{self._base}/{table}", params={**params, "limit": PAGE_SIZE, "offset": offset},
                                 headers=self._headers, timeout=self._timeout_s)
            resp.raise_for_status()
            page = resp.json() if resp.content else []
            rows.extend(page)
            if len(page) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
        return rows

    def update_row(self, table: str, filters: dict[str, str], row: dict) -> None:
        resp = requests.patch(f"{self._base}/{table}", params=filters, json=row,
                               headers={**self._headers, "Prefer": "return=minimal"}, timeout=self._timeout_s)
        resp.raise_for_status()


def client_from_env() -> SupabaseRestClient | None:
    """None (never raises) if VEHNWAY_SUPABASE_URL/VEHNWAY_SUPABASE_SERVICE_KEY aren't set."""
    url = os.environ.get("VEHNWAY_SUPABASE_URL")
    key = os.environ.get("VEHNWAY_SUPABASE_SERVICE_KEY")
    if not url or not key:
        return None
    return SupabaseRestClient(url, key)
