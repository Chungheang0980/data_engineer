"""
dashboard.py — Streamlit dashboard for the real-time finance pipeline.

Reads directly from the Gold warehouse layer (PostgreSQL).
Five tabs:
  1. Overview   — market-wide price change bar chart + live price table
  2. Asset      — deep-dive metrics + OHLC bar + sector context
  3. Sectors    — sector-level bar charts and comparison table
  4. Rankings   — top / bottom N assets by any indicator
  5. Forecasts  — MLflow-generated price predictions with confidence bands

Usage:
    streamlit run 05_app/dashboard/dashboard.py
    # or from the project root:
    python -m streamlit run 05_app/dashboard/dashboard.py
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_PATH)

# ---------------------------------------------------------------------------
# DB helpers (cached so reconnection only happens when session resets)
# ---------------------------------------------------------------------------

@st.cache_resource
def _get_engine():
    host     = os.environ["DB_HOST"]
    port     = os.environ.get("DB_PORT", "5432")
    dbname   = os.environ["DB_NAME"]
    user     = os.environ["DB_USER"]
    password = os.environ.get("DB_PASSWORD", "")
    url      = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url, pool_pre_ping=True)


PRICE_COLUMNS = [
    "company_name",
    "sector",
    "year",
    "current_price_usd",
    "open_price_usd",
    "day_high_usd",
    "day_low_usd",
    "previous_close_usd",
    "price_change_usd",
    "price_change_pct",
    "trading_volume",
    "intraday_range_pct",
    "price_momentum",
    "sector_avg_price",
    "sector_avg_change_pct",
]

PREDICTION_COLUMNS = [
    "company_name",
    "indicator",
    "model_name",
    "predicted_year",
    "predicted_value",
    "confidence_low",
    "confidence_high",
]


def _empty_prices() -> pd.DataFrame:
    return pd.DataFrame(columns=PRICE_COLUMNS)


def _empty_predictions() -> pd.DataFrame:
    return pd.DataFrame(columns=PREDICTION_COLUMNS)


def _table_exists(conn, table_name: str) -> bool:
    return conn.execute(
        text("SELECT to_regclass(:table_name) IS NOT NULL"),
        {"table_name": table_name},
    ).scalar_one()


@st.cache_data(ttl=60)
def _load_prices() -> pd.DataFrame:
    engine = _get_engine()
    with engine.connect() as conn:
        if not (
            _table_exists(conn, "gold.dim_asset")
            and _table_exists(conn, "gold.fact_prices")
        ):
            return _empty_prices()

        return pd.read_sql(text("""
            SELECT d.company_name,
                   d.sector,
                   f.year,
                   f.current_price_usd,
                   f.open_price_usd,
                   f.day_high_usd,
                   f.day_low_usd,
                   f.previous_close_usd,
                   f.price_change_usd,
                   f.price_change_pct,
                   f.trading_volume,
                   f.intraday_range_pct,
                   f.price_momentum,
                   f.sector_avg_price,
                   f.sector_avg_change_pct
            FROM   gold.fact_prices f
            JOIN   gold.dim_asset   d ON d.asset_id = f.asset_id
            ORDER  BY f.price_change_pct DESC NULLS LAST
        """), conn)


@st.cache_data(ttl=60)
def _load_predictions() -> pd.DataFrame:
    engine = _get_engine()
    with engine.connect() as conn:
        if not (
            _table_exists(conn, "gold.dim_asset")
            and _table_exists(conn, "gold.fact_predictions")
        ):
            return _empty_predictions()

        return pd.read_sql(text("""
            SELECT d.company_name,
                   p.indicator,
                   p.model_name,
                   p.predicted_year,
                   p.predicted_value,
                   p.confidence_low,
                   p.confidence_high
            FROM   gold.fact_predictions p
            JOIN   gold.dim_asset        d ON d.asset_id = p.asset_id
            ORDER  BY p.predicted_year
        """), conn)


# ---------------------------------------------------------------------------
# Helper: colour a cell red/green by sign
# ---------------------------------------------------------------------------

def _colour_pct(val):
    if pd.isna(val):
        return ""
    return "color: green; font-weight: bold" if val > 0 else "color: red; font-weight: bold"


def _latest_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    return (
        df.sort_values(["company_name", "year"])
        .groupby("company_name", as_index=False)
        .tail(1)
        .sort_values("price_change_pct", ascending=False)
        .reset_index(drop=True)
    )


def _inject_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2.5rem;
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e6ebf2;
            border-radius: 8px;
            padding: 12px 14px;
        }
        div[data-testid="stMetricLabel"] p {
            color: #64748b;
            font-size: 0.82rem;
        }
        div[data-testid="stMetricValue"] {
            color: #111827;
            font-weight: 700;
        }
        .market-hero {
            border: 1px solid #e6ebf2;
            border-radius: 8px;
            padding: 16px 18px;
            margin-bottom: 14px;
            background: #ffffff;
        }
        .market-hero h1 {
            font-size: 1.55rem;
            margin: 0 0 4px 0;
            letter-spacing: 0;
        }
        .market-hero p {
            margin: 0;
            color: #475569;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="Finance Pipeline Dashboard",
        page_icon="📈",
        layout="wide",
    )
    _inject_style()

    st.markdown(
        """
        <div class="market-hero">
            <h1>Real-Time Finance Dashboard</h1>
            <p>Simple view of latest prices, sectors, rankings, and ML forecasts.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Load data ────────────────────────────────────────────────────────────
    try:
        df = _load_prices()
    except Exception as exc:
        st.error(f"Cannot connect to the database: {exc}")
        st.info("Run `python main.py` first to populate the warehouse, then reload.")
        return

    if df.empty:
        st.warning("Warehouse is empty. Run `python main.py` to ingest data.")
        return

    pred_df = _load_predictions()
    all_years = sorted(df["year"].dropna().astype(int).unique().tolist())
    all_sectors = sorted(df["sector"].dropna().unique().tolist())

    with st.sidebar:
        st.header("Filters")
        selected_sectors = st.multiselect(
            "Sectors",
            all_sectors,
            default=all_sectors,
        )
        year_range = st.slider(
            "History window",
            min_value=min(all_years),
            max_value=max(all_years),
            value=(min(all_years), max(all_years)),
        )
        search_text = st.text_input("Asset search", placeholder="Apple, NVIDIA, Visa")

    filtered_df = df[
        df["sector"].isin(selected_sectors)
        & df["year"].between(year_range[0], year_range[1])
    ].copy()
    if search_text:
        filtered_df = filtered_df[
            filtered_df["company_name"].str.contains(search_text, case=False, na=False)
        ].copy()

    latest_df = _latest_snapshot(filtered_df)

    if latest_df.empty:
        st.warning("No assets match the current filters.")
        return

    latest_year = int(latest_df["year"].max())
    selected_assets = latest_df["company_name"].tolist()
    pred_df = pred_df[pred_df["company_name"].isin(selected_assets)].copy()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Overview", "Asset", "Sectors", "Rankings", "Forecasts"]
    )

    with tab1:
        st.subheader(f"Overview ({latest_year})")

        gainers = int((latest_df["price_change_pct"] > 0).sum())
        losers = int((latest_df["price_change_pct"] < 0).sum())
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Assets", len(latest_df))
        c2.metric("Avg Price", f"${latest_df['current_price_usd'].mean():.2f}")
        c3.metric("Gainers", gainers)
        c4.metric("Losers", losers)

        fig = px.bar(
            latest_df.sort_values("price_change_pct"),
            x="price_change_pct",
            y="company_name",
            orientation="h",
            color="price_change_pct",
            color_continuous_scale=["#dc2626", "#e2e8f0", "#16a34a"],
            color_continuous_midpoint=0,
            title="Latest Price Change",
            labels={"price_change_pct": "Change %", "company_name": ""},
        )
        fig.update_layout(height=520, coloraxis_showscale=False, margin=dict(l=8, r=8, t=48, b=8))
        st.plotly_chart(fig, width="stretch")

        st.subheader("Live Price Table")
        display_cols = {
            "company_name":      "Company",
            "sector":            "Sector",
            "year":              "Year",
            "current_price_usd": "Price ($)",
            "price_change_pct":  "Change %",
            "day_high_usd":      "High ($)",
            "day_low_usd":       "Low ($)",
            "trading_volume":    "Volume",
            "intraday_range_pct":"Range %",
            "price_momentum":    "Momentum",
        }
        tbl = latest_df[list(display_cols.keys())].rename(columns=display_cols)
        st.dataframe(
            tbl.style
               .map(_colour_pct, subset=["Change %", "Range %"])
               .format({"Price ($)": "${:.2f}", "High ($)": "${:.2f}",
                        "Low ($)": "${:.2f}", "Change %": "{:.2f}%",
                        "Range %": "{:.2f}%", "Volume": "{:,.0f}"}),
            width="stretch",
            height=400,
        )

    with tab2:
        st.subheader("Asset Detail")

        asset = st.selectbox("Select Asset", latest_df["company_name"].tolist(), key="asset_sel")
        row   = latest_df[latest_df["company_name"] == asset].iloc[0]
        history = filtered_df[filtered_df["company_name"] == asset].sort_values("year")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Price",   f"${row['current_price_usd']:.2f}",
                  delta=f"{row['price_change_pct']:.2f}%")
        c2.metric("Day High",        f"${row['day_high_usd']:.2f}")
        c3.metric("Day Low",         f"${row['day_low_usd']:.2f}")
        c4.metric("Volume",          f"{row['trading_volume']:,.0f}")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Open",            f"${row['open_price_usd']:.2f}")
        c6.metric("Prev Close",      f"${row['previous_close_usd']:.2f}")
        c7.metric("Intraday Range",  f"{row['intraday_range_pct']:.2f}%")
        c8.metric("Momentum",        row["price_momentum"] if pd.notna(row["price_momentum"]) else "-")

        fig_history = px.line(
            history,
            x="year",
            y="current_price_usd",
            markers=True,
            title=f"{asset} Price History",
            labels={"year": "Year", "current_price_usd": "Price (USD)"},
        )
        fig_history.update_layout(height=420, margin=dict(l=8, r=8, t=48, b=8))
        st.plotly_chart(fig_history, width="stretch")

        if pd.notna(row.get("sector")):
            st.info(
                f"**Sector:** {row['sector']}  |  "
                f"Sector avg price: **${row['sector_avg_price']:.2f}**  |  "
                f"Sector avg change: **{row['sector_avg_change_pct']:.2f}%**"
            )

    with tab3:
        st.subheader("Sectors")

        sec_df = (
            latest_df.groupby("sector")
            .agg(
                n_assets   = ("company_name",      "count"),
                avg_price  = ("current_price_usd", "mean"),
                avg_change = ("price_change_pct",  "mean"),
                avg_volume = ("trading_volume",     "mean"),
            )
            .reset_index()
            .sort_values("avg_change", ascending=False)
        )

        fig3 = px.bar(
            sec_df,
            x="sector",
            y="avg_change",
            color="avg_change",
            color_continuous_scale=["#dc2626", "#e2e8f0", "#16a34a"],
            color_continuous_midpoint=0,
            title="Average Change by Sector",
            labels={"avg_change": "Avg Change %", "sector": ""},
        )
        fig3.update_layout(height=420, coloraxis_showscale=False, margin=dict(l=8, r=8, t=48, b=8))
        st.plotly_chart(fig3, width="stretch")

        st.dataframe(
            sec_df.rename(columns={
                "sector":     "Sector",
                "n_assets":   "# Assets",
                "avg_price":  "Avg Price ($)",
                "avg_change": "Avg Change %",
                "avg_volume": "Avg Volume",
            }).style
              .map(_colour_pct, subset=["Avg Change %"])
              .format({
                  "Avg Price ($)": "${:.2f}",
                  "Avg Change %":  "{:.2f}%",
                  "Avg Volume":    "{:,.0f}",
            }),
            width="stretch",
        )

    with tab4:
        st.subheader("Rankings")

        col1, col2, col3 = st.columns(3)
        rank_by = col1.selectbox(
            "Rank by",
            ["price_change_pct", "current_price_usd", "trading_volume", "intraday_range_pct"],
            format_func=lambda x: x.replace("_", " ").title(),
        )
        top_n   = col2.slider("Show top N", 3, 20, 10)
        order   = col3.radio("Order", ["Top (highest)", "Bottom (lowest)"])

        ascending = order.startswith("Bottom")
        cols = list(dict.fromkeys(
            ["company_name", "sector", rank_by, "current_price_usd", "price_change_pct"]
        ))
        ranked = (
            latest_df[cols]
            .dropna(subset=[rank_by])
            .sort_values(rank_by, ascending=ascending)
            .head(top_n)
        )

        fig6 = px.bar(
            ranked,
            x=rank_by, y="company_name",
            orientation="h",
            color=rank_by,
            color_continuous_scale=["#dc2626", "#e2e8f0", "#16a34a"] if not ascending
                                   else ["#16a34a", "#e2e8f0", "#dc2626"],
            color_continuous_midpoint=0 if "change" in rank_by else None,
            title=f"{'Top' if not ascending else 'Bottom'} {top_n} by {rank_by.replace('_', ' ').title()}",
            labels={rank_by: rank_by.replace("_", " ").title(), "company_name": ""},
        )
        fig6.update_layout(height=450, coloraxis_showscale=False, margin=dict(l=8, r=8, t=48, b=8))
        st.plotly_chart(fig6, width="stretch")
        st.dataframe(ranked.reset_index(drop=True), width="stretch")

    with tab5:
        st.subheader("Forecasts")

        if pred_df.empty:
            st.info(
                "No predictions available yet.  \n"
                "Predictions appear after **≥3 pipeline runs** have accumulated "
                "historical data in `gold.fact_prices`.  \n"
                "Run `python main.py` repeatedly (or on a schedule) to build history."
            )
        else:
            col1, col2 = st.columns(2)
            sel_asset = col1.selectbox(
                "Asset", pred_df["company_name"].unique().tolist(), key="fc_asset"
            )
            sel_indicator = col2.selectbox(
                "Indicator", pred_df["indicator"].unique().tolist(), key="fc_ind"
            )

            filtered = pred_df[
                (pred_df["company_name"] == sel_asset) &
                (pred_df["indicator"]    == sel_indicator)
            ]

            if filtered.empty:
                st.warning("No predictions for this combination.")
            else:
                # Add current price as anchor point
                current_row = latest_df[latest_df["company_name"] == sel_asset]
                actual_value = None
                if not current_row.empty and sel_indicator == "current_price_usd":
                    actual_value = float(current_row["current_price_usd"].values[0])
                    anchor = pd.DataFrame([{
                        "company_name":    sel_asset,
                        "indicator":       sel_indicator,
                        "model_name":      "actual",
                        "predicted_year":  int(current_row["year"].values[0]),
                        "predicted_value": actual_value,
                        "confidence_low":  actual_value,
                        "confidence_high": actual_value,
                    }])
                    filtered = pd.concat([anchor, filtered], ignore_index=True)

                fig7 = px.line(
                    filtered,
                    x="predicted_year",
                    y="predicted_value",
                    color="model_name",
                    markers=True,
                    title=f"{sel_asset} — {sel_indicator.replace('_', ' ').title()} Forecast",
                    labels={
                        "predicted_year":  "Year",
                        "predicted_value": sel_indicator.replace("_", " ").title(),
                        "model_name":      "Model",
                    },
                )

                fig7.update_layout(height=450, margin=dict(l=8, r=8, t=48, b=8))
                st.plotly_chart(fig7, width="stretch")

                st.dataframe(
                    filtered[["model_name", "predicted_year", "predicted_value",
                               "confidence_low", "confidence_high"]]
                    .rename(columns={
                        "model_name":      "Model",
                        "predicted_year":  "Year",
                        "predicted_value": "Forecast",
                        "confidence_low":  "Low (95%)",
                        "confidence_high": "High (95%)",
                    }),
                    width="stretch",
                )


if __name__ == "__main__":
    main()
