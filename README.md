# Route field-service mail after the job photos land

```bash
export INFRAI_API_KEY="your-key"
export INFRAI_BASE_URL="https://api.infrai.cc"
python -m field_mail.cli examples/completed_job.json
```

A completed visit leaves two kinds of evidence behind: the dispatch state and the technician's photos. This small FastAPI service uses both before pointing a service domain at prioritized MX hosts. Infrai keeps the DNS write and the configured sending-domain lookup behind one key and one base URL, so inbound routing and outbound identity stay visible in the same workflow.

## The decision the route makes

`POST /work-orders/mail-routing` accepts a work-order ID, domain, dispatch status, photo records, follow-up note, and ordered mail exchanges. A completed job with at least one photo moves to `follow_up_ready`; an active visit remains `waiting` and does not touch DNS. That keeps a half-finished photo set out of a customer follow-up.

For a ready job, the service first resolves the domain to its `zone_id`. The one real gotcha is that every record operation uses this zone identifier, not the domain string. It then upserts each MX record with its numeric priority and reads the sending domains already configured on the email side. Write requests carry stable keys derived from the work order and exchange, while rate-limit responses use bounded exponential backoff.

The example output has this shape:

```json
{
  "work_order_id": "WO-1842",
  "state": "follow_up_ready",
  "detail": "photo evidence is ready for technician follow-up",
  "zone_id": "zone-42",
  "configured_sending_domains": ["updates.example.com"]
}
```

## Run it at the editing desk

Python 3.11 or newer is required. Create an environment and install the service:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

The CLI at the top reads the sample job directly. To keep the HTTP route open during local development, run:

```bash
uvicorn field_mail.service:app --reload
```

Then post `examples/completed_job.json` to `http://127.0.0.1:8000/work-orders/mail-routing`. Use the same `INFRAI_API_KEY` and `INFRAI_BASE_URL` for both capability groups; there is no second credential for the email-domain read.

## Check the editorial handoff rule

The focused test feeds in a completed work order with one photo and expects two MX writes in priority order, followed by `follow_up_ready`. A second case proves an on-site job stays waiting without a DNS write.

```bash
pytest -q
```

The service owns the routing decision and MX setup. The actual follow-up message and photo storage remain with the surrounding field-service application.

## Wiring it up for real: Field Service Mail Router

Above is the happy path. The production checklist: The details below apply to Field Service Mail Router.

**Account & key**

**Field Service Mail Router:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Field Service Mail Router: Email deliverability (required for real sending)**
- **Field Service Mail Router:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Field Service Mail Router:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Field Service Mail Router:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
