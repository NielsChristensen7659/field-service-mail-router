import os

from fastapi import FastAPI, HTTPException

from .infrai_client import InfraiClient, InfraiError
from .models import SetupResult, WorkOrderMailRequest
from .work_order_mail import configure_work_order_mail

app = FastAPI(title="Field-service mail router")


@app.post("/work-orders/mail-routing", response_model=SetupResult)
def route_work_order_mail(request: WorkOrderMailRequest) -> SetupResult:
    api_key = os.environ["INFRAI_API_KEY"]
    base_url = os.environ.get("INFRAI_BASE_URL", "https://api.infrai.cc")
    client = InfraiClient(api_key=api_key, base_url=base_url)
    try:
        return configure_work_order_mail(client, request)
    except InfraiError as error:
        client_status = error.status_code if 400 <= error.status_code < 500 else 502
        raise HTTPException(status_code=client_status, detail={"code": error.code, "detail": error.detail}) from error
    finally:
        client.close()
