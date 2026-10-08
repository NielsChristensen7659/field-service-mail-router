import time
from collections.abc import Mapping
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: object, status_code: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiClient:
    def __init__(self, api_key: str, base_url: str, transport: httpx.BaseTransport | None = None) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
        json: Mapping[str, object] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        for attempt in range(4):
            response = self._client.request(method=method, url=path, params=params, json=json, headers=headers)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a response that was not JSON")

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                time.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            response.raise_for_status()
            return envelope.get("data")
        raise RuntimeError("Retry budget exhausted")

    def get_zone(self, domain: str) -> dict[str, Any]:
        return self._request("GET", "/v1/dns/domain/get", params={"domain": domain})

    def add_zone(self, domain: str, request_key: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/dns/domain/add",
            json={"domain": domain},
            idempotency_key=request_key,
        )

    def upsert_mx(
        self, zone_id: str, name: str, content: str, priority: int, request_key: str
    ) -> dict[str, Any]:
        return self._request(
            "PUT",
            "/v1/dns/record/upsert",
            json={
                "zone_id": zone_id,
                "record_type": "MX",
                "name": name,
                "content": content,
                "priority": priority,
                "ttl": 3600,
            },
            idempotency_key=request_key,
        )

    def list_sending_domains(self) -> Any:
        return self._request("GET", "/v1/email/domain/list")
