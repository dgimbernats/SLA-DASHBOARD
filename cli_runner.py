"""Generate SLA reports without starting Streamlit."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.data_io import generate_synthetic_tickets, load_tickets
from src.kpi_engine import normalize_tickets
from src.reporting import create_excel_report, create_pdf_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SLA dashboard reports")
    parser.add_argument("--input", type=Path, help="CSV or XLSX ticket file")
    parser.add_argument("--output-dir", type=Path, default=Path("reports"))
    parser.add_argument("--format", choices=["excel", "pdf", "both"], default="both")
    parser.add_argument("--records", type=int, default=5_000, help="Synthetic row count")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    raw = load_tickets(args.input) if args.input else generate_synthetic_tickets(args.records, args.seed)
    tickets = normalize_tickets(raw)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    outputs = []
    if args.format in {"excel", "both"}:
        path = args.output_dir / "sla_report.xlsx"
        path.write_bytes(create_excel_report(tickets))
        outputs.append(path)
    if args.format in {"pdf", "both"}:
        path = args.output_dir / "sla_report.pdf"
        path.write_bytes(create_pdf_report(tickets))
        outputs.append(path)
    print("Generated: " + ", ".join(str(path) for path in outputs))


if __name__ == "__main__":
    main()
