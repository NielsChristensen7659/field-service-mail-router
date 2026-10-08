from field_mail.models import WorkOrderMailRequest
from field_mail.work_order_mail import configure_work_order_mail


class RecordingClient:
    def __init__(self) -> None:
        self.mx_calls: list[tuple[str, str, int]] = []
        self.add_calls: list[tuple[str, str]] = []

    def get_zone(self, domain: str) -> dict[str, str]:
        assert domain == "mail.example.com"
        return {"zone_id": "zone-42"}

    def upsert_mx(self, zone_id: str, name: str, content: str, priority: int, request_key: str) -> dict:
        assert name == "@"
        assert request_key.startswith("WO-1842:mx:")
        self.mx_calls.append((zone_id, content, priority))
        return {"record_id": f"mx-{priority}"}

    def add_zone(self, domain: str, request_key: str) -> dict[str, str]:
        self.add_calls.append((domain, request_key))
        return {"zone_id": "zone-added"}

    def list_sending_domains(self) -> dict[str, list[dict[str, str]]]:
        return {"domains": [{"domain": "updates.example.com"}]}


def request_with(status: str, photos: list[dict]) -> WorkOrderMailRequest:
    return WorkOrderMailRequest.model_validate(
        {
            "work_order_id": "WO-1842",
            "domain": "mail.example.com",
            "dispatch_status": status,
            "photos": photos,
            "technician_follow_up": "Send completion gallery",
            "exchanges": [
                {"host": "mx1.provider.example", "priority": 10},
                {"host": "mx2.provider.example", "priority": 20},
            ],
        }
    )


def test_completed_job_with_photo_configures_prioritized_mx() -> None:
    client = RecordingClient()
    request = request_with(
        "completed",
        [{"asset_id": "panel", "caption": "Installed", "url": "https://media.example/panel.jpg"}],
    )

    result = configure_work_order_mail(client, request)  # type: ignore[arg-type]

    assert result.state == "follow_up_ready"
    assert client.mx_calls == [
        ("zone-42", "mx1.provider.example", 10),
        ("zone-42", "mx2.provider.example", 20),
    ]
    assert result.configured_sending_domains == ["updates.example.com"]


def test_on_site_job_waits_without_touching_dns() -> None:
    client = RecordingClient()

    result = configure_work_order_mail(client, request_with("on_site", []))  # type: ignore[arg-type]

    assert result.state == "waiting"
    assert client.mx_calls == []


def test_empty_zone_id_adds_domain_before_upserting_records() -> None:
    client = RecordingClient()
    client.get_zone = lambda domain: {"zone_id": ""}  # type: ignore[method-assign]

    result = configure_work_order_mail(
        client,
        request_with(
            "completed",
            [{"asset_id": "panel", "caption": "Installed", "url": "https://media.example/panel.jpg"}],
        ),
    )  # type: ignore[arg-type]

    assert client.add_calls == [("mail.example.com", "WO-1842:zone")]
    assert result.zone_id == "zone-added"
    assert [call[0] for call in client.mx_calls] == ["zone-added", "zone-added"]
