from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class JsonHttpClient:
    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
    ) -> Any:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(url, data=data, method=method, headers=headers)

        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310
                raw_response = response.read().decode("utf-8")
        except HTTPError as ex:
            error_body = ex.read().decode("utf-8")
            raise RuntimeError(f"HTTP {ex.code} from {url}: {error_body}") from ex
        except URLError as ex:
            raise RuntimeError(f"Unable to reach {url}: {ex.reason}") from ex

        return json.loads(raw_response) if raw_response else {}
