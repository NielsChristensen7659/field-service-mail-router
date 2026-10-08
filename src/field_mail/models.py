from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class DispatchStatus(StrEnum):
    ASSIGNED = "assigned"
    ON_SITE = "on_site"
    COMPLETED = "completed"


class WorkOrderPhoto(BaseModel):
    asset_id: str = Field(min_length=1)
    caption: str = Field(min_length=1)
    url: HttpUrl


class MailExchange(BaseModel):
    host: str = Field(min_length=1)
    priority: int = Field(ge=0, le=65535)


class WorkOrderMailRequest(BaseModel):
    work_order_id: str = Field(min_length=1)
    domain: str = Field(min_length=3)
    dispatch_status: DispatchStatus
    photos: list[WorkOrderPhoto]
    technician_follow_up: str = Field(min_length=1)
    exchanges: list[MailExchange] = Field(min_length=1)


class SetupResult(BaseModel):
    work_order_id: str
    state: str
    detail: str
    zone_id: str | None = None
    configured_sending_domains: list[str] = Field(default_factory=list)
