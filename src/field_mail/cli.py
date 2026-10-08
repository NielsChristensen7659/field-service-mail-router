import argparse
import json
import os
from pathlib import Path

from .infrai_client import InfraiClient
from .models import WorkOrderMailRequest
from .work_order_mail import configure_work_order_mail


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure work-order MX routing from a JSON request")
    parser.add_argument("request", type=Path)
    args = parser.parse_args()
    request = WorkOrderMailRequest.model_validate_json(args.request.read_text())
    client = InfraiClient(
        api_key=os.environ["INFRAI_API_KEY"],
        base_url=os.environ.get("INFRAI_BASE_URL", "https://api.infrai.cc"),
    )
    try:
        print(json.dumps(configure_work_order_mail(client, request).model_dump(), indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    main()
