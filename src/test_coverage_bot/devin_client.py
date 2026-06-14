from __future__ import annotations

from typing import Any

from .config import Config
from .http_client import JsonHttpClient


class DevinClient:
    def __init__(self, http_client: JsonHttpClient) -> None:
        self.http_client = http_client

    def create_session(self, config: Config, prompt: str) -> dict[str, Any]:
        body: dict[str, Any] = {"prompt": prompt}
        if config.devin_create_as_user_id:
            body["create_as_user_id"] = config.devin_create_as_user_id

        if config.dry_run:
            return {"dry_run": True, "request_body": body}

        if not config.devin_api_key or not config.devin_org_id:
            raise RuntimeError("DEVIN_API_KEY and DEVIN_ORG_ID are required for live runs")

        url = (
            f"{config.devin_api_base_url.rstrip('/')}"
            f"/organizations/{config.devin_org_id}/sessions"
        )
        return self.http_client.request(
            "POST",
            url,
            {"Authorization": f"Bearer {config.devin_api_key}", "Content-Type": "application/json"},
            body,
        )

    def session_reference(self, response: dict[str, Any]) -> str:
        return str(
            response.get("url")
            or response.get("session_url")
            or response.get("session_id")
            or response.get("id")
            or "dry-run"
        )
