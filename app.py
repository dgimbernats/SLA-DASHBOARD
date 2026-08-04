"""Streamlit SLA dashboard."""

from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_io import generate_synthetic_tickets, load_tickets
from src.kpi_engine import apply_filters, backlog_aging, normalize_tickets, summary_kpis, technician_csat
from src.reporting import create_excel_report, create_pdf_report

st.set_page_config(page_title="SLA Dashboard", page_icon="⏱️", layout="wide")


@st.cache_data(show_spinner=False)
def synthetic_data(records: int, seed: int) -> pd.DataFrame:
    return normalize_tickets(generate_synthetic_tickets(records, seed))


@st.cache_data(show_spinner=False)
def uploaded_data(content: bytes, filename: str) -> pd.DataFrame:
    return normalize_tickets(load_tickets(BytesIO(content), filename))


def main() -> None:
    st.title("SLA Dashboard")
    st.caption("ServiceNow-style incident performance across regions")

    source = st.sidebar.radio("Data source", ["Synthetic data", "Upload file"])
    try:
        if source == "Synthetic data":
            records = st.sidebar.number_input("Records", 5_000, 100_000, 5_000, 1_000)
            seed = st.sidebar.number_input("Random seed", 0, 1_000_000, 42)
            data = synthetic_data(int(records), int(seed))
        else:
            upload = st.sidebar.file_uploader("CSV or Excel", type=["csv", "xlsx", "xlsm"])
            if upload is None:
                st.info("Upload a CSV or Excel file to begin.")
                return
            data = uploaded_data(upload.getvalue(), upload.name)
    except ValueError as exc:
        st.error(str(exc))
        return

    st.sidebar.header("Global filters")
    regions = st.sidebar.multiselect("Regions", sorted(data["region"].dropna().unique()))
    priorities = st.sidebar.multiselect("Priorities", sorted(data["priority"].dropna().unique()))
    states = st.sidebar.multiselect("States", sorted(data["state"].dropna().unique()))
    min_date, max_date = data["opened_at"].dt.date.min(), data["opened_at"].dt.date.max()
    date_range = st.sidebar.date_input("Opened date", (min_date, max_date), min_value=min_date, max_value=max_date)
    start, end = (date_range if len(date_range) == 2 else (min_date, max_date))
    filtered = apply_filters(data, regions, priorities, states, start, end)
    if filtered.empty:
        st.warning("No tickets match the selected filters.")
        return

    overview, sla, backlog, technicians, explorer = st.tabs(
        ["Overview", "SLA Analysis", "Backlog", "Technicians", "Data Explorer"]
    )
    with overview:
        _overview(filtered)
    with sla:
        _sla_analysis(filtered)
    with backlog:
        _backlog(filtered)
    with technicians:
        _technicians(filtered)
    with explorer:
        _explorer(filtered)


def _overview(data: pd.DataFrame) -> None:
    metrics = summary_kpis(data)
    columns = st.columns(6)
    values = [
        ("Tickets", f"{metrics['total_tickets']:,}"),
        ("Open backlog", f"{metrics['open_backlog']:,}"),
        ("SLA compliance", f"{metrics['sla_compliance']:.1f}%"),
        ("FCR", f"{metrics['fcr_rate']:.1f}%"),
        ("Reopen rate", f"{metrics['reopen_rate']:.1f}%"),
        ("CSAT", f"{metrics['avg_csat']:.2f}"),
    ]
    for column, (label, value) in zip(columns, values):
        column.metric(label, value)
    daily = data.assign(day=data["opened_at"].dt.date).groupby("day").size().reset_index(name="tickets")
    st.plotly_chart(px.line(daily, x="day", y="tickets", title="Tickets Opened by Day"), use_container_width=True)


def _sla_analysis(data: pd.DataFrame) -> None:
    status = data.groupby(["region", "sla_status"]).size().reset_index(name="tickets")
    st.plotly_chart(
        px.bar(status, x="region", y="tickets", color="sla_status", barmode="stack", title="SLA Status by Region"),
        use_container_width=True,
    )
    priority = data.groupby(["priority", "sla_status"]).size().reset_index(name="tickets")
    st.plotly_chart(
        px.bar(priority, x="priority", y="tickets", color="sla_status", barmode="group", title="SLA Status by Priority"),
        use_container_width=True,
    )


def _backlog(data: pd.DataFrame) -> None:
    aging = backlog_aging(data).rename_axis("age_bucket").reset_index(name="tickets")
    st.plotly_chart(px.bar(aging, x="age_bucket", y="tickets", title="Open Backlog Aging"), use_container_width=True)
    open_tickets = data.loc[~data["is_resolved"]].sort_values("opened_at")
    st.dataframe(open_tickets, use_container_width=True, hide_index=True)


def _technicians(data: pd.DataFrame) -> None:
    tech = technician_csat(data)
    st.plotly_chart(
        px.bar(tech.head(20), x="assigned_to", y="avg_csat", color="responses", title="Technician CSAT"),
        use_container_width=True,
    )
    st.dataframe(tech, use_container_width=True, hide_index=True)


def _explorer(data: pd.DataFrame) -> None:
    st.dataframe(data, use_container_width=True, hide_index=True)
    col1, col2 = st.columns(2)
    col1.download_button(
        "Download Excel report",
        create_excel_report(data),
        "sla_report.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    col2.download_button("Download PDF report", create_pdf_report(data), "sla_report.pdf", "application/pdf")


if __name__ == "__main__":
    main()
