"""Pure ticket normalization, filtering, and KPI calculations."""

import re
from collections.abc import Iterable

import numpy as np
import pandas as pd

from src.config import PRIORITY_SLA_HOURS, REGION_TIMEZONES, REQUIRED_COLUMNS, RESOLVED_STATES

ALIASES = {
    "number": "ticket_id",
    "sys_id": "ticket_id",
    "opened": "opened_at",
    "resolved": "resolved_at",
    "assignee": "assigned_to",
}


def _column_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _to_bool(series: pd.Series) -> pd.Series:
    true_values = {"true", "1", "yes", "y"}
    false_values = {"false", "0", "no", "n", ""}
    values = series.astype("string").str.strip().str.lower()
    invalid = values.dropna()[~values.dropna().isin(true_values | false_values)]
    if not invalid.empty:
        raise ValueError(f"Invalid boolean value: {invalid.iloc[0]}")
    return values.isin(true_values)


def normalize_tickets(data: pd.DataFrame, now: pd.Timestamp | None = None) -> pd.DataFrame:
    """Validate and normalize uploaded or generated tickets into one UTC schema."""
    if data.empty:
        raise ValueError("Ticket data is empty")

    frame = data.copy()
    frame.columns = [ALIASES.get(_column_name(column), _column_name(column)) for column in frame.columns]
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    frame["opened_at"] = pd.to_datetime(frame["opened_at"], errors="coerce", utc=True)
    if frame["opened_at"].isna().any():
        raise ValueError("opened_at contains invalid timestamps")
    if "resolved_at" not in frame:
        frame["resolved_at"] = pd.NaT
    frame["resolved_at"] = pd.to_datetime(frame["resolved_at"], errors="coerce", utc=True)

    frame["priority"] = frame["priority"].astype("string").str.upper().str.strip()
    invalid_priorities = sorted(set(frame["priority"].dropna()) - set(PRIORITY_SLA_HOURS))
    if invalid_priorities:
        raise ValueError(f"Unknown priorities: {', '.join(invalid_priorities)}")
    frame["sla_target_hours"] = pd.to_numeric(
        frame.get("sla_target_hours", frame["priority"].map(PRIORITY_SLA_HOURS)), errors="coerce"
    ).fillna(frame["priority"].map(PRIORITY_SLA_HOURS))
    if (frame["sla_target_hours"] <= 0).any():
        raise ValueError("sla_target_hours must be positive")

    frame["region"] = frame["region"].astype("string").str.strip()
    invalid_regions = sorted(set(frame["region"].dropna()) - set(REGION_TIMEZONES))
    if invalid_regions:
        raise ValueError(f"Unknown regions: {', '.join(invalid_regions)}")
    frame["region_timezone"] = frame["region"].map(REGION_TIMEZONES)
    frame["fcr_flag"] = _to_bool(frame["fcr_flag"])
    frame["reopen_count"] = pd.to_numeric(frame["reopen_count"], errors="coerce").fillna(0).clip(lower=0).astype(int)
    frame["csat"] = pd.to_numeric(frame["csat"], errors="coerce")
    if frame["csat"].dropna().lt(1).any() or frame["csat"].dropna().gt(5).any():
        raise ValueError("csat must be between 1 and 5")

    current = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    current = current.tz_localize("UTC") if current.tzinfo is None else current.tz_convert("UTC")
    frame["is_resolved"] = frame["state"].astype("string").str.lower().isin(RESOLVED_STATES)
    elapsed_end = frame["resolved_at"].where(frame["is_resolved"] & frame["resolved_at"].notna(), current)
    frame["sla_elapsed_hours"] = ((elapsed_end - frame["opened_at"]).dt.total_seconds() / 3600).clip(lower=0)
    ratio = frame["sla_elapsed_hours"] / frame["sla_target_hours"]
    frame["sla_status"] = np.select(
        [ratio < 0.75, ratio < 1, ~frame["is_resolved"]],
        ["Healthy", "Warning", "Critical"],
        default="Breached",
    )
    return frame


def apply_filters(
    data: pd.DataFrame,
    regions: Iterable[str] | None = None,
    priorities: Iterable[str] | None = None,
    states: Iterable[str] | None = None,
    opened_from: object | None = None,
    opened_to: object | None = None,
) -> pd.DataFrame:
    """Apply the dashboard's shared filters without mutating input data."""
    mask = pd.Series(True, index=data.index)
    for column, selected in (("region", regions), ("priority", priorities), ("state", states)):
        if selected:
            mask &= data[column].isin(selected)
    if opened_from is not None:
        mask &= data["opened_at"] >= pd.Timestamp(opened_from, tz="UTC")
    if opened_to is not None:
        end = pd.Timestamp(opened_to, tz="UTC") + pd.Timedelta(days=1)
        mask &= data["opened_at"] < end
    return data.loc[mask].copy()


def sla_compliance_rate(data: pd.DataFrame) -> float:
    resolved = data[data["is_resolved"]]
    return _percentage((resolved["sla_elapsed_hours"] <= resolved["sla_target_hours"]).sum(), len(resolved))


def fcr_rate(data: pd.DataFrame) -> float:
    resolved = data[data["is_resolved"]]
    return _percentage(resolved["fcr_flag"].sum(), len(resolved))


def reopen_rate(data: pd.DataFrame) -> float:
    return _percentage(data["reopen_count"].gt(0).sum(), len(data))


def backlog_aging(data: pd.DataFrame, now: pd.Timestamp | None = None) -> pd.Series:
    current = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    current = current.tz_localize("UTC") if current.tzinfo is None else current.tz_convert("UTC")
    age_days = (current - data.loc[~data["is_resolved"], "opened_at"]).dt.total_seconds() / 86_400
    buckets = pd.cut(age_days, [-1, 3, 7, 14, np.inf], labels=["0-3 days", "4-7 days", "8-14 days", "15+ days"])
    return buckets.value_counts(sort=False).reindex(buckets.cat.categories, fill_value=0).astype(int)


def technician_csat(data: pd.DataFrame) -> pd.DataFrame:
    return (
        data.dropna(subset=["csat"])
        .groupby("assigned_to", as_index=False)
        .agg(avg_csat=("csat", "mean"), responses=("csat", "size"))
        .sort_values(["avg_csat", "responses"], ascending=[False, False])
    )


def summary_kpis(data: pd.DataFrame) -> dict[str, float | int]:
    return {
        "total_tickets": len(data),
        "open_backlog": int((~data["is_resolved"]).sum()),
        "sla_compliance": sla_compliance_rate(data),
        "fcr_rate": fcr_rate(data),
        "reopen_rate": reopen_rate(data),
        "avg_csat": round(float(data["csat"].mean()), 2) if data["csat"].notna().any() else 0.0,
    }


def _percentage(numerator: int | float, denominator: int) -> float:
    return round(float(numerator) / denominator * 100, 2) if denominator else 0.0
