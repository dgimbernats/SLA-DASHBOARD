# SLA Dashboard

A portable Streamlit dashboard for exploring ServiceNow-style incident SLAs across Mexico, the Americas, Manila, and Warsaw. It ships with a reproducible 5,000-ticket generator, CSV/XLSX ingestion, reusable KPI calculations, interactive Plotly charts, and Excel/PDF exports.

The pinned dependencies target Python 3.11 or 3.12.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app defaults to synthetic data. Uploaded files must contain: `ticket_id`, `opened_at`, `state`, `priority`, `region`, `assigned_to`, `fcr_flag`, `reopen_count`, and `csat`. Optional fields include `resolved_at` and `sla_target_hours`.

## Headless reports

```bash
python cli_runner.py --records 5000 --format both --output-dir reports
python cli_runner.py --input tickets.xlsx --format excel
```

## Tests

```bash
pytest
```

## KPI definitions

- **SLA compliance:** resolved tickets completed within their SLA target / all resolved tickets.
- **FCR:** resolved tickets with `fcr_flag=True` / all resolved tickets.
- **Backlog aging:** unresolved tickets grouped into 0–3, 4–7, 8–14, and 15+ day buckets.
- **Reopen rate:** tickets with at least one reopen / all tickets.
- **Technician CSAT:** average non-null CSAT per technician.

All elapsed-time calculations use absolute UTC under a 24/7 SLA clock. Region-specific IANA time zones are retained for display and future business-hours support.
