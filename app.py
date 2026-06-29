import os
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FRED_API_KEY")

if not API_KEY:
    API_KEY = st.secrets["FRED_API_KEY"]

st.set_page_config(
    page_title="Macro Intelligence Dashboard",
    layout="wide"
)

INDICATORS = {
    "Real GDP": "GDPC1",
    "Nonfarm Payrolls": "PAYEMS",
    "CPI Inflation": "CPIAUCSL",
    "Core PCE": "PCEPILFE",
    "Fed Funds Rate": "FEDFUNDS",
    "10-Year Treasury": "GS10",
    "Yield Curve": "T10Y2Y",
    "High Yield Spread": "BAMLH0A0HYM2"
}


def get_fred_data(series_id):
    url = "https://api.stlouisfed.org/fred/series/observations"

    params = {
        "series_id": series_id,
        "api_key": API_KEY,
        "file_type": "json"
    }

    response = requests.get(url, params=params)
    data = response.json()["observations"]

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna()

    return df[["date", "value"]]


def calculate_change(df):
    latest = df["value"].iloc[-1]
    previous = df["value"].iloc[-2]

    absolute_change = latest - previous
    pct_change = (absolute_change / previous) * 100

    return latest, previous, absolute_change, pct_change


def arrow(pct_change):
    if pct_change > 0:
        return f"▲ +{pct_change:.2f}%"
    elif pct_change < 0:
        return f"▼ {pct_change:.2f}%"
    else:
        return "→ 0.00%"


def explain_indicator(name, pct_change):
    direction = "up" if pct_change > 0 else "down"

    explanations = {
        "Real GDP": {
            "up": {
                "meaning": "Economic output is expanding.",
                "demand": "Demand side: consumers and businesses are spending more.",
                "supply": "Supply side: firms are producing more goods and services.",
                "impact": "Usually positive for growth, jobs, and corporate earnings."
            },
            "down": {
                "meaning": "Economic output is weakening.",
                "demand": "Demand side: spending and investment may be slowing.",
                "supply": "Supply side: firms may reduce production.",
                "impact": "Raises slowdown or recession concerns."
            }
        },

        "Nonfarm Payrolls": {
            "up": {
                "meaning": "The labour market is adding jobs.",
                "demand": "Demand side: household income and consumption can rise.",
                "supply": "Supply side: more workers support more production.",
                "impact": "Positive for growth, but very strong jobs can keep inflation sticky."
            },
            "down": {
                "meaning": "Job growth is weakening.",
                "demand": "Demand side: consumers may spend less.",
                "supply": "Supply side: businesses may be reducing hiring.",
                "impact": "Raises concern about slower economic activity."
            }
        },

        "CPI Inflation": {
            "up": {
                "meaning": "Inflation pressure is rising.",
                "demand": "Demand side: spending may be too strong relative to supply.",
                "supply": "Supply side: input costs or supply bottlenecks may be pushing prices up.",
                "impact": "The Fed may stay restrictive for longer."
            },
            "down": {
                "meaning": "Inflation pressure is cooling.",
                "demand": "Demand side: spending pressure may be easing.",
                "supply": "Supply side: supply conditions may be improving.",
                "impact": "This can support future rate cuts if the trend continues."
            }
        },

        "Core PCE": {
            "up": {
                "meaning": "Underlying inflation is rising.",
                "demand": "Demand side: services demand may remain strong.",
                "supply": "Supply side: wage and input cost pressures may persist.",
                "impact": "Important because the Fed watches Core PCE closely."
            },
            "down": {
                "meaning": "Underlying inflation is cooling.",
                "demand": "Demand side: price pressure from spending is easing.",
                "supply": "Supply side: cost pressure may be improving.",
                "impact": "This is positive for monetary policy easing."
            }
        },

        "Fed Funds Rate": {
            "up": {
                "meaning": "Monetary policy is becoming tighter.",
                "demand": "Demand side: borrowing, housing, and investment may slow.",
                "supply": "Supply side: firms may delay expansion plans.",
                "impact": "Helps control inflation but can slow growth."
            },
            "down": {
                "meaning": "Monetary policy is becoming easier.",
                "demand": "Demand side: cheaper credit can support spending.",
                "supply": "Supply side: firms may invest and expand more.",
                "impact": "Supports growth but can re-ignite inflation if too aggressive."
            }
        },

        "10-Year Treasury": {
            "up": {
                "meaning": "Long-term rates are rising.",
                "demand": "Demand side: mortgages and loans become more expensive.",
                "supply": "Supply side: business investment may become less attractive.",
                "impact": "Tightens financial conditions."
            },
            "down": {
                "meaning": "Long-term rates are falling.",
                "demand": "Demand side: borrowing becomes easier.",
                "supply": "Supply side: investment conditions improve.",
                "impact": "Can support housing, stocks, and long-term investment."
            }
        },

        "Yield Curve": {
            "up": {
                "meaning": "The yield curve is becoming healthier.",
                "demand": "Demand side: credit conditions may improve.",
                "supply": "Supply side: banks may be more willing to lend.",
                "impact": "Usually supports normal economic activity."
            },
            "down": {
                "meaning": "The yield curve is flattening or worsening.",
                "demand": "Demand side: credit creation may weaken.",
                "supply": "Supply side: bank lending incentives may decline.",
                "impact": "A negative curve is a recession warning."
            }
        },

        "High Yield Spread": {
            "up": {
                "meaning": "Credit risk is rising.",
                "demand": "Demand side: riskier firms may face weaker funding access.",
                "supply": "Supply side: firms may cut investment or hiring.",
                "impact": "A rising spread signals financial stress."
            },
            "down": {
                "meaning": "Credit risk is falling.",
                "demand": "Demand side: investors are more confident.",
                "supply": "Supply side: companies can access funding more easily.",
                "impact": "Supports investment and risk-taking."
            }
        }
    }

    return explanations[name][direction]


def get_status(name, value):
    if name == "Real GDP":
        return "🟢 Healthy growth" if value > 2 else "🔴 Recession risk" if value < 0 else "🟡 Slow growth"

    if name == "Nonfarm Payrolls":
        return "🟢 Strong labour market" if value > 150000 else "🔴 Job losses" if value < 0 else "🟡 Slowing jobs"

    if name in ["CPI Inflation", "Core PCE"]:
        return "🟢 Comfortable inflation" if value < 2 else "🔴 High inflation" if value > 5 else "🟡 Elevated inflation"

    if name == "Fed Funds Rate":
        return "🟢 Easy policy" if value < 2 else "🔴 Restrictive policy" if value > 5 else "🟡 Neutral/tight policy"

    if name == "10-Year Treasury":
        return "🟢 Low rates" if value < 2 else "🔴 Tight financial conditions" if value > 5 else "🟡 Moderate rates"

    if name == "Yield Curve":
        return "🟢 Normal curve" if value > 0 else "🔴 Inversion warning"

    if name == "High Yield Spread":
        return "🟢 Credit confidence" if value < 4 else "🔴 Credit stress" if value > 6 else "🟡 Watch credit risk"

    return "⚪ No status"


st.title("📊 Macro Intelligence Dashboard")
st.caption("FRED API dashboard with change, interpretation, demand-side impact, and supply-side impact.")

st.sidebar.title("Choose Indicator")
selected_indicator = st.sidebar.selectbox("Indicator", list(INDICATORS.keys()))

all_data = {}

for name, code in INDICATORS.items():
    all_data[name] = get_fred_data(code)

st.subheader("📌 Macro KPI Cards")

cols = st.columns(4)

for i, (name, code) in enumerate(INDICATORS.items()):
    df = all_data[name]
    latest, previous, absolute_change, pct_change = calculate_change(df)
    latest_date = df["date"].iloc[-1].strftime("%d %b %Y")
    status = get_status(name, latest)

    with cols[i % 4]:
        st.metric(
            label=f"{name} ({code})",
            value=f"{latest:,.2f}",
            delta=arrow(pct_change)
        )
        st.write(status)
        st.caption(f"Latest date: {latest_date}")

st.divider()

st.subheader(f"📈 Interactive Chart: {selected_indicator}")

selected_df = all_data[selected_indicator]
selected_code = INDICATORS[selected_indicator]

fig = px.line(
    selected_df,
    x="date",
    y="value",
    title=f"{selected_indicator} ({selected_code}) over time"
)

st.plotly_chart(fig, use_container_width=True)

latest, previous, absolute_change, pct_change = calculate_change(selected_df)
explanation = explain_indicator(selected_indicator, pct_change)

st.subheader("🧠 Economic Interpretation")

col1, col2 = st.columns(2)

with col1:
    st.metric("Latest Value", f"{latest:,.2f}")
    st.metric("Previous Value", f"{previous:,.2f}")
    st.metric("Change", f"{absolute_change:,.2f}", arrow(pct_change))

with col2:
    st.write(f"**Meaning:** {explanation['meaning']}")
    st.write(f"**Demand Impact:** {explanation['demand']}")
    st.write(f"**Supply Impact:** {explanation['supply']}")
    st.write(f"**Economic Impact:** {explanation['impact']}")

st.divider()

st.subheader("📋 Business Cycle Scorecard")

scorecard_rows = []

for name, code in INDICATORS.items():
    df = all_data[name]
    latest, previous, absolute_change, pct_change = calculate_change(df)
    latest_date = df["date"].iloc[-1].strftime("%d %b %Y")
    status = get_status(name, latest)
    explanation = explain_indicator(name, pct_change)

    scorecard_rows.append({
        "Indicator": name,
        "Code": code,
        "Latest": round(latest, 2),
        "% Change": round(pct_change, 2),
        "Status": status,
        "Demand Side": explanation["demand"],
        "Supply Side": explanation["supply"],
        "Economic Impact": explanation["impact"],
        "Date": latest_date
    })

scorecard = pd.DataFrame(scorecard_rows)

st.dataframe(scorecard, use_container_width=True)

st.divider()

st.subheader("🧠 Overall Economic Regime")

bad_signals = scorecard["Status"].str.contains("🔴").sum()
warning_signals = scorecard["Status"].str.contains("🟡").sum()

if bad_signals >= 3:
    regime = "🔴 Recession / Stress"
elif bad_signals >= 1 or warning_signals >= 4:
    regime = "🟠 Slowdown / Late Cycle"
elif warning_signals >= 2:
    regime = "🟡 Mid-cycle Caution"
else:
    regime = "🟢 Expansion"

st.header(regime)

st.caption("This is a simple rule-based regime reading using the 8 macro indicators.")
