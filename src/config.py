"""Shared configuration for the SLA dashboard."""

REGIONS = ("Mexico", "Americas", "Manila", "Warsaw")

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
