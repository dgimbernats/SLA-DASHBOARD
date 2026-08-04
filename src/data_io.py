"""Synthetic data generation and uploaded-file loading."""

from pathlib import Path
from typing import BinaryIO

import numpy as np
import pandas as pd
from src.config import PRIORITY_SLA_HOURS, REGIONS


def generate_synthetic_tickets(n_records: int = 5_000, seed: int = 42) -> pd.DataFrame:
    """Create a deterministic, ServiceNow-like ticket dataset."""
    if n_records < 1:
        raise ValueError("n_records must be positive")

    rng = np.random.default_rng(seed)
    now = pd.Timestamp.now(tz="UTC").floor("s")
    opened_at = pd.to_datetime(
        now - pd.to_timedelta(rng.integers(1, 180 * 24 * 60, n_records), unit="m"),
        utc=True,
    )

    is_resolved = rng.random(n_records) < 0.78
    resolved_hours = np.maximum(0.25, rng.lognormal(mean=2.3, sigma=1.0, size=n_records))
    resolved_at = pd.Series(opened_at + pd.to_timedelta(resolved_hours, unit="h"))
    resolved_at[~is_resolved] = pd.NaT

    priorities = rng.choice(["P1", "P2", "P3", "P4"], n_records, p=[0.05, 0.20, 0.45, 0.30])
    regions = rng.choice(REGIONS, n_records, p=[0.30, 0.30, 0.25, 0.15])
    open_states = rng.choice(["New", "In Progress", "On Hold"], n_records)
    closed_states = rng.choice(["Resolved", "Closed"], n_records, p=[0.8, 0.2])
    states = np.where(is_resolved, closed_states, open_states)
    technicians = [f"Technician {number:02d}" for number in range(1, 25)]
    csat = np.where(is_resolved & (rng.random(n_records) < 0.72), rng.integers(1, 6, n_records), np.nan)

    return pd.DataFrame(
        {
            "ticket_id": [f"INC{1_000_000 + i:07d}" for i in range(n_records)],
            "opened_at": opened_at,
            "resolved_at": resolved_at,
            "state": states,
            "priority": priorities,
            "region": regions,
            "assigned_to": rng.choice(technicians, n_records),
            "fcr_flag": is_resolved & (rng.random(n_records) < 0.63),
            "reopen_count": rng.choice([0, 1, 2, 3], n_records, p=[0.84, 0.12, 0.03, 0.01]),
            "csat": csat,
            "sla_target_hours": [PRIORITY_SLA_HOURS[priority] for priority in priorities],
        }
    )


def load_tickets(source: str | Path | BinaryIO, filename: str | None = None) -> pd.DataFrame:
    """Load ticket data from CSV or Excel paths and file-like uploads."""
    name = filename or getattr(source, "name", None) or str(source)
    suffix = Path(name).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(source)
    if suffix in {".xlsx", ".xlsm"}:
        return pd.read_excel(source, engine="openpyxl")
    raise ValueError("Only CSV and Excel (.xlsx/.xlsm) files are supported")
