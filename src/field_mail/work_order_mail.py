from typing import Any

from .infrai_client import InfraiClient, InfraiError
from .models import DispatchStatus, SetupResult, WorkOrderMailRequest


def decide_mail_setup(request: WorkOrderMailRequest) -> tuple[bool, str]:
    if request.dispatch_status != DispatchStatus.COMPLETED:
        return False, "dispatch must be completed before customer mail is routed"
    if not request.photos:
        return False, "at least one work-order photo is required for customer follow-up"
    return True, "photo evidence is ready for technician follow-up"


def _domain_names(data: Any) -> list[str]:
    items = data if isinstance(data, list) else data.get("domains", []) if isinstance(data, dict) else []
    return [str(item["domain"]) for item in items if isinstance(item, dict) and "domain" in item]


def configure_work_order_mail(client: InfraiClient, request: WorkOrderMailRequest) -> SetupResult:
    should_configure, detail = decide_mail_setup(request)
    if not should_configure:
        return SetupResult(work_order_id=request.work_order_id, state="waiting", detail=detail)

    try:
        zone = client.get_zone(request.domain)
    except InfraiError as error:
        if error.status_code != 404:
            raise
        zone = {}

    if not zone.get("zone_id"):
        zone = client.add_zone(request.domain, f"{request.work_order_id}:zone")

    zone_id = str(zone["zone_id"])
    for exchange in request.exchanges:
        client.upsert_mx(
            zone_id=zone_id,
            name="@",
            content=exchange.host,
            priority=exchange.priority,
            request_key=f"{request.work_order_id}:mx:{exchange.priority}:{exchange.host}",
        )

    sending_domains = _domain_names(client.list_sending_domains())
    return SetupResult(
        work_order_id=request.work_order_id,
        state="follow_up_ready",
        detail=detail,
        zone_id=zone_id,
        configured_sending_domains=sending_domains,
    )
