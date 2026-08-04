"""Shared configuration for the SLA dashboard."""

REGION_TIMEZONES = {
    "Mexico": "America/Mexico_City",
    "Americas": "America/New_York",
    "Manila": "Asia/Manila",
    "Warsaw": "Europe/Warsaw",
}

PRIORITY_SLA_HOURS = {"P1": 4, "P2": 8, "P3": 24, "P4": 72}

REQUIRED_COLUMNS = {
    "ticket_id",
    "opened_at",
    "state",
    "priority",
    "region",
    "assigned_to",
    "fcr_flag",
    "reopen_count",
    "csat",
}

RESOLVED_STATES = {"closed", "resolved"}
