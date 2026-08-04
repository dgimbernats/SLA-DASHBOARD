from io import BytesIO

import pandas as pd
import pytest
from openpyxl import load_workbook

from src.data_io import generate_synthetic_tickets
from src.kpi_engine import backlog_aging, fcr_rate, normalize_tickets, reopen_rate, sla_compliance_rate
from src.reporting import create_excel_report, create_pdf_report


NOW = pd.Timestamp("2026-01-20 12:00:00", tz="UTC")


def sample_tickets() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticket_id": ["INC1", "INC2", "INC3", "INC4"],
            "opened_at": [NOW - pd.Timedelta(hours=2), NOW - pd.Timedelta(hours=10), NOW - pd.Timedelta(days=5), NOW - pd.Timedelta(days=20)],
            "resolved_at": [NOW - pd.Timedelta(hours=1), NOW - pd.Timedelta(hours=1), None, None],
            "state": ["Resolved", "Closed", "In Progress", "New"],
            "priority": ["P1", "P1", "P3", "P4"],
            "region": ["Mexico", "Americas", "Manila", "Warsaw"],
            "assigned_to": ["Ana", "Ana", "Bo", "Cy"],
            "fcr_flag": [True, False, False, False],
            "reopen_count": [0, 1, 0, 0],
            "csat": [5, 3, None, None],
        }
    )


def test_kpis_follow_documented_denominators():
    tickets = normalize_tickets(sample_tickets(), NOW)
    assert sla_compliance_rate(tickets) == 50.0
    assert fcr_rate(tickets) == 50.0
    assert reopen_rate(tickets) == 25.0


def test_sla_status_uses_open_or_resolved_state_at_threshold():
    tickets = normalize_tickets(sample_tickets(), NOW)
    assert tickets["sla_status"].tolist() == ["Healthy", "Breached", "Critical", "Critical"]


def test_backlog_aging_excludes_resolved_tickets():
    tickets = normalize_tickets(sample_tickets(), NOW)
    assert backlog_aging(tickets, NOW).to_dict() == {
        "0-3 days": 0,
        "4-7 days": 1,
        "8-14 days": 0,
        "15+ days": 1,
    }


def test_normalization_rejects_missing_schema():
    with pytest.raises(ValueError, match="Missing required columns"):
        normalize_tickets(pd.DataFrame({"ticket_id": ["INC1"]}), NOW)


def test_default_generator_creates_5000_normalizable_tickets():
    assert len(normalize_tickets(generate_synthetic_tickets(), NOW)) == 5_000


def test_reports_are_valid_and_escape_spreadsheet_formulas():
    raw = sample_tickets()
    raw.loc[0, "assigned_to"] = "=HYPERLINK(\"https://example.com\")"
    tickets = normalize_tickets(raw, NOW)
    excel = create_excel_report(tickets)
    pdf = create_pdf_report(tickets)
    workbook = load_workbook(BytesIO(excel), read_only=True)
    sheet = workbook["Tickets"]
    rows = sheet.values
    assignee_column = list(next(rows)).index("assigned_to")
    first_ticket = next(rows)

    assert excel.startswith(b"PK")
    assert pdf.startswith(b"%PDF")
    assert first_ticket[assignee_column].startswith("'=")
