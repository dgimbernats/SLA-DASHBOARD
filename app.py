"""Streamlit SLA dashboard."""

from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_io import generate_synthetic_tickets, load_tickets
from src.kpi_engine import apply_filters, backlog_aging, normalize_tickets, summary_kpis, technician_csat
from src.reporting import create_excel_report, create_pdf_report

st.set_page_config(page_title="SLA Command Center", page_icon="⏱️", layout="wide")

OPS_CSS = """
<style>
:root {
    --ops-bg: #090d10;
    --ops-panel: #11171b;
    --ops-panel-2: #161d22;
    --ops-border: #2b363d;
    --ops-text: #f1f5f7;
    --ops-muted: #93a2ad;
    --ops-amber: #ffb400;
    --ops-teal: #2de1c2;
}
.stApp {
    color: var(--ops-text);
    background-color: var(--ops-bg);
    background-image:
        linear-gradient(rgba(255,255,255,.018) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.018) 1px, transparent 1px);
    background-size: 28px 28px;
}
[data-testid="stHeader"] { background: rgba(9,13,16,.88); }
[data-testid="stSidebar"] {
    background: #0c1114;
    border-right: 1px solid var(--ops-border);
}
.block-container { max-width: 1500px; padding-top: 2rem; }
.ops-header {
    position: relative;
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 2rem;
    align-items: end;
    overflow: hidden;
    margin-bottom: 1rem;
    padding: 1.6rem 1.8rem 1.8rem;
    background: linear-gradient(120deg, #151d22 0%, #0d1215 70%);
    border: 1px solid var(--ops-border);
    box-shadow: 12px 12px 0 rgba(0,0,0,.28);
}
.ops-header::after {
    position: absolute;
    right: 0;
    bottom: 0;
    left: 0;
    height: 6px;
    content: "";
    background: repeating-linear-gradient(135deg, var(--ops-amber) 0 12px, #232c31 12px 24px);
}
.ops-kicker, .ops-status span, .section-label, .sidebar-label, .context-strip {
    font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
    letter-spacing: .12em;
    text-transform: uppercase;
}
.ops-kicker { margin: 0 0 .55rem; color: var(--ops-amber); font-size: .72rem; }
.ops-header h1 {
    margin: 0;
    color: var(--ops-text);
    font-family: "Arial Narrow", "Roboto Condensed", "Segoe UI", sans-serif;
    font-size: clamp(2.25rem, 5vw, 4.7rem);
    font-weight: 800;
    line-height: .95;
    letter-spacing: -.045em;
    text-transform: uppercase;
}
.ops-subtitle { max-width: 62ch; margin: .8rem 0 0; color: var(--ops-muted); }
.ops-status { min-width: 130px; padding: .8rem 1rem; border: 1px solid var(--ops-border); }
.ops-status span { display: block; color: var(--ops-muted); font-size: .65rem; }
.ops-status strong { color: var(--ops-teal); font: 700 1rem ui-monospace, monospace; }
.ops-status strong::before { content: "●"; margin-right: .45rem; }
.sidebar-label {
    display: flex;
    justify-content: space-between;
    margin: .35rem 0 1.1rem;
    padding-bottom: .7rem;
    color: var(--ops-amber);
    border-bottom: 1px solid var(--ops-border);
    font-size: .72rem;
}
.context-strip {
    display: flex;
    flex-wrap: wrap;
    gap: .7rem 1.5rem;
    margin: 0 0 1rem;
    padding: .7rem 1rem;
    color: var(--ops-muted);
    background: #0d1316;
    border: 1px solid var(--ops-border);
    font-size: .68rem;
}
.context-strip b { color: var(--ops-teal); font-weight: 700; }
.section-label { margin: 1.2rem 0 .8rem; color: var(--ops-amber); font-size: .72rem; }
[data-testid="stMetric"] {
    min-height: 120px;
    padding: 1rem;
    background: linear-gradient(145deg, var(--ops-panel-2), var(--ops-panel));
    border: 1px solid var(--ops-border);
    border-left: 3px solid var(--ops-amber);
    border-radius: 2px;
}
[data-testid="stMetricLabel"] { color: var(--ops-muted); text-transform: uppercase; letter-spacing: .06em; }
[data-testid="stMetricValue"] { color: var(--ops-text); font-family: ui-monospace, monospace; }
[data-baseweb="tab-list"] { gap: 0; border-bottom: 1px solid var(--ops-border); }
[data-baseweb="tab-highlight"] { background-color: var(--ops-amber); }
button[data-baseweb="tab"] {
    min-height: 48px;
    padding: 0 1.15rem;
    color: var(--ops-muted);
    border-radius: 0;
}
button[data-baseweb="tab"][aria-selected="true"] { color: var(--ops-amber); background: #141a1e; }
[data-testid="stDataFrame"] { border: 1px solid var(--ops-border); }
.stDownloadButton button, .stButton button {
    width: 100%;
    color: #101417;
    background: var(--ops-amber);
    border: 1px solid var(--ops-amber);
    border-radius: 2px;
    font-weight: 750;
    text-transform: uppercase;
    letter-spacing: .04em;
}
.stDownloadButton button:hover, .stButton button:hover { color: var(--ops-text); background: transparent; }
div[data-testid="stAlert"] { border-radius: 2px; }
*:focus-visible { outline: 2px solid var(--ops-teal) !important; outline-offset: 2px; }
@media (max-width: 800px) {
    .block-container { padding: 1rem; }
    .ops-header { grid-template-columns: 1fr; padding: 1.25rem; }
    .ops-status { width: fit-content; }
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
    [data-testid="column"] { flex: 1 1 100% !important; width: 100% !important; }
    [data-baseweb="tab-list"] { overflow-x: auto; }
    button[data-baseweb="tab"] { padding: 0 .7rem; font-size: .78rem; }
}
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; animation: none !important; }
}
</style>
"""

SLA_COLORS = {"Healthy": "#2de1c2", "Warning": "#ffb400", "Critical": "#ff6b35", "Breached": "#ef4444"}


@st.cache_data(show_spinner=False)
def synthetic_data(records: int, seed: int) -> pd.DataFrame:
    return normalize_tickets(generate_synthetic_tickets(records, seed))


@st.cache_data(show_spinner=False)
def uploaded_data(content: bytes, filename: str) -> pd.DataFrame:
    return normalize_tickets(load_tickets(BytesIO(content), filename))


def _chart(figure):
    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#aab6bf", family="Segoe UI, sans-serif"),
        title_font=dict(color="#f1f5f7", family="Arial Narrow, Segoe UI, sans-serif", size=20),
        margin=dict(l=10, r=10, t=55, b=10),
        hoverlabel=dict(bgcolor="#11171b", bordercolor="#2b363d", font_color="#f1f5f7"),
    )
    figure.update_xaxes(gridcolor="rgba(147,162,173,.12)", linecolor="#2b363d")
    figure.update_yaxes(gridcolor="rgba(147,162,173,.12)", linecolor="#2b363d")
    return figure


def main() -> None:
    st.markdown(OPS_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <header class="ops-header">
          <div>
            <p class="ops-kicker">Global service operations / UTC normalized</p>
            <h1>SLA Command Center</h1>
            <p class="ops-subtitle">Incident performance, breach exposure, and technician signals across four delivery regions.</p>
          </div>
          <div class="ops-status"><span>System state</span><strong>Online</strong></div>
        </header>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        '<div class="sidebar-label"><span>Control inputs</span><span>UTC</span></div>', unsafe_allow_html=True
    )

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
    start, end = date_range if len(date_range) == 2 else (min_date, max_date)
    filtered = apply_filters(data, regions, priorities, states, start, end)
    if filtered.empty:
        st.warning("No tickets match the selected filters.")
        return

    st.markdown(
        f'<div class="context-strip"><span>Active records <b>{len(filtered):,}</b></span>'
        f'<span>Regions <b>{filtered["region"].nunique()}</b></span>'
        f'<span>Window <b>{start:%d %b %Y} — {end:%d %b %Y}</b></span></div>',
        unsafe_allow_html=True,
    )
    overview, sla, backlog, technicians, explorer = st.tabs(
        ["Overview", "SLA Analysis", "Backlog", "Technicians", "Data Explorer"]
    )
    with overview:
        st.markdown('<div class="section-label">01 / Executive pulse</div>', unsafe_allow_html=True)
        _overview(filtered)
    with sla:
        st.markdown('<div class="section-label">02 / Risk distribution</div>', unsafe_allow_html=True)
        _sla_analysis(filtered)
    with backlog:
        st.markdown('<div class="section-label">03 / Backlog control</div>', unsafe_allow_html=True)
        _backlog(filtered)
    with technicians:
        st.markdown('<div class="section-label">04 / Technician signal</div>', unsafe_allow_html=True)
        _technicians(filtered)
    with explorer:
        st.markdown('<div class="section-label">05 / Record export</div>', unsafe_allow_html=True)
        _explorer(filtered)


def _overview(data: pd.DataFrame) -> None:
    metrics = summary_kpis(data)
    values = [
        ("Tickets", f"{metrics['total_tickets']:,}"),
        ("Open backlog", f"{metrics['open_backlog']:,}"),
        ("SLA compliance", f"{metrics['sla_compliance']:.1f}%"),
        ("FCR", f"{metrics['fcr_rate']:.1f}%"),
        ("Reopen rate", f"{metrics['reopen_rate']:.1f}%"),
        ("CSAT", f"{metrics['avg_csat']:.2f}"),
    ]
    for row in (values[:3], values[3:]):
        for column, (label, value) in zip(st.columns(3), row):
            column.metric(label, value)
    daily = data.assign(day=data["opened_at"].dt.date).groupby("day").size().reset_index(name="tickets")
    figure = px.line(daily, x="day", y="tickets", title="Tickets Opened by Day", color_discrete_sequence=["#ffb400"])
    figure.update_traces(line_width=2.5)
    st.plotly_chart(_chart(figure), use_container_width=True)


def _sla_analysis(data: pd.DataFrame) -> None:
    status = data.groupby(["region", "sla_status"]).size().reset_index(name="tickets")
    st.plotly_chart(
        _chart(
            px.bar(
                status,
                x="region",
                y="tickets",
                color="sla_status",
                color_discrete_map=SLA_COLORS,
                barmode="stack",
                title="SLA Status by Region",
            )
        ),
        use_container_width=True,
    )
    priority = data.groupby(["priority", "sla_status"]).size().reset_index(name="tickets")
    st.plotly_chart(
        _chart(
            px.bar(
                priority,
                x="priority",
                y="tickets",
                color="sla_status",
                color_discrete_map=SLA_COLORS,
                barmode="group",
                title="SLA Status by Priority",
            )
        ),
        use_container_width=True,
    )


def _backlog(data: pd.DataFrame) -> None:
    aging = backlog_aging(data).rename_axis("age_bucket").reset_index(name="tickets")
    st.plotly_chart(
        _chart(px.bar(aging, x="age_bucket", y="tickets", title="Open Backlog Aging", color_discrete_sequence=["#ffb400"])),
        use_container_width=True,
    )
    open_tickets = data.loc[~data["is_resolved"]].sort_values("opened_at")
    st.dataframe(open_tickets, use_container_width=True, hide_index=True)


def _technicians(data: pd.DataFrame) -> None:
    tech = technician_csat(data)
    st.plotly_chart(
        _chart(
            px.bar(
                tech.head(20),
                x="assigned_to",
                y="avg_csat",
                color="responses",
                color_continuous_scale=["#173431", "#2de1c2"],
                title="Technician CSAT",
            )
        ),
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
