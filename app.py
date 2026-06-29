import os
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Macro Intelligence Dashboard",
    layout="wide"
)

API_KEY = os.getenv("FRED_API_KEY")

if not API_KEY:
    API_KEY = st.secrets.get("FRED_API_KEY", None)

if not API_KEY:
    st.error("FRED API key missing. Add it to .env locally or Streamlit Secrets online.")
    st.stop()


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

PORTFOLIO = {
    "AGG": {
        "name": "iShares Core U.S. Aggregate Bond ETF",
        "weight": 0.25,
        "type": "Bond ETF"
    },
    "SPAB": {
        "name": "SPDR Portfolio Aggregate Bond ETF",
        "weight": 0.25,
        "type": "Bond ETF"
    },
    "GDX": {
        "name": "VanEck Gold Miners ETF",
        "weight": 0.25,
        "type": "Gold Miners"
    },
    "SPY": {
        "name": "SPDR S&P 500 ETF",
        "weight": 0.25,
        "type": "Equity ETF"
    }
}


@st.cache_data(ttl=3600)
def get_fred_data(series_id):
    url = "https://api.stlouisfed.org/fred/series/observations"

    params = {
        "series_id": series_id,
        "api_key": API_KEY,
        "file_type": "json"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()["observations"]

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna()

    return df[["date", "value"]]


@st.cache_data(ttl=3600)
def get_etf_prices(tickers):
    data = yf.download(
        tickers,
        period="1y",
        auto_adjust=True,
        progress=False
    )["Close"]

    if isinstance(data, pd.Series):
        data = data.to_frame()

    data = data.dropna()
    return data


def calculate_change(df):
    latest = df["value"].iloc[-1]
    previous = df["value"].iloc[-2]

    absolute_change = latest - previous

    if previous == 0:
        pct_change = 0
    else:
        pct_change = (absolute_change / previous) * 100

    return latest, previous, absolute_change, pct_change


def arrow(pct_change):
    if pct_change > 0:
        return f"▲ +{pct_change:.2f}%"
    elif pct_change < 0:
        return f"▼ {pct_change:.2f}%"
    else:
        return "→ 0.00%"


def get_status(name, value):
    if name == "Real GDP":
        if value > 2:
            return "🟢 Healthy growth"
        elif value < 0:
            return "🔴 Recession risk"
        return "🟡 Slow growth"

    if name == "Nonfarm Payrolls":
        if value > 150000:
            return "🟢 Strong labour market"
        elif value < 0:
            return "🔴 Job losses"
        return "🟡 Slowing jobs"

    if name in ["CPI Inflation", "Core PCE"]:
        if value < 2:
            return "🟢 Comfortable inflation"
        elif value > 5:
            return "🔴 High inflation"
        return "🟡 Elevated inflation"

    if name == "Fed Funds Rate":
        if value < 2:
            return "🟢 Easy policy"
        elif value > 5:
            return "🔴 Restrictive policy"
        return "🟡 Neutral/tight policy"

    if name == "10-Year Treasury":
        if value < 2:
            return "🟢 Low rates"
        elif value > 5:
            return "🔴 Tight financial conditions"
        return "🟡 Moderate rates"

    if name == "Yield Curve":
        if value > 0:
            return "🟢 Normal curve"
        return "🔴 Inversion warning"

    if name == "High Yield Spread":
        if value < 4:
            return "🟢 Credit confidence"
        elif value > 6:
            return "🔴 Credit stress"
        return "🟡 Watch credit risk"

    return "⚪ No status"


def explain_indicator(name, pct_change):
    direction = "up" if pct_change > 0 else "down"

    explanations = {
        "Real GDP": {
            "up": {
                "meaning": "Economic output is expanding.",
                "demand": "Demand side: consumers, businesses, and government may be spending more.",
                "supply": "Supply side: firms are producing more goods and services.",
                "impact": "Positive for growth, employment, and corporate earnings."
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
                "impact": "Good for growth, but very strong jobs can keep inflation sticky."
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
                "meaning": "Headline inflation pressure is rising.",
                "demand": "Demand side: spending may be strong relative to supply.",
                "supply": "Supply side: input costs or bottlenecks may be pushing prices up.",
                "impact": "The Fed may stay restrictive for longer."
            },
            "down": {
                "meaning": "Headline inflation pressure is cooling.",
                "demand": "Demand side: spending pressure may be easing.",
                "supply": "Supply side: supply conditions may be improving.",
                "impact": "Can support future rate cuts if the trend continues."
            }
        },
        "Core PCE": {
            "up": {
                "meaning": "Underlying inflation is rising.",
                "demand": "Demand side: services demand may remain strong.",
                "supply": "Supply side: wage and input cost pressure may persist.",
                "impact": "Important because the Fed watches Core PCE closely."
            },
            "down": {
                "meaning": "Underlying inflation is cooling.",
                "demand": "Demand side: price pressure from spending is easing.",
                "supply": "Supply side: cost pressure may be improving.",
                "impact": "Positive for possible monetary policy easing."
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
                "impact": "Supports growth, but may re-ignite inflation if too aggressive."
            }
        },
        "10-Year Treasury": {
            "up": {
                "meaning": "Long-term rates are rising.",
                "demand": "Demand side: mortgages and loans become more expensive.",
                "supply": "Supply side: business investment becomes less attractive.",
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


def portfolio_impact(indicator, pct_change):
    direction = "increased" if pct_change > 0 else "decreased"

    impacts = {
        "Fed Funds Rate": {
            "increased": {
                "AGG": "Negative: higher policy rates usually pressure bond prices.",
                "SPAB": "Negative: higher rates usually pressure aggregate bonds.",
                "GDX": "Negative/Mixed: higher real rates can hurt gold-related assets.",
                "SPY": "Negative: higher discount rates can pressure equity valuations.",
                "portfolio": "Overall negative. Bonds and equities may both face pressure."
            },
            "decreased": {
                "AGG": "Positive: falling rates usually support bond prices.",
                "SPAB": "Positive: lower rates support aggregate bonds.",
                "GDX": "Positive/Mixed: lower rates can support gold miners.",
                "SPY": "Positive: lower discount rates can support equities.",
                "portfolio": "Generally positive across bonds, equities, and gold miners."
            }
        },
        "CPI Inflation": {
            "increased": {
                "AGG": "Negative: inflation can push yields higher and hurt bonds.",
                "SPAB": "Negative: inflation can pressure aggregate bonds.",
                "GDX": "Positive/Mixed: gold miners may benefit from inflation fears.",
                "SPY": "Negative/Mixed: inflation can pressure margins and valuations.",
                "portfolio": "Mixed, but usually risky for bonds and equities."
            },
            "decreased": {
                "AGG": "Positive: lower inflation can support bonds.",
                "SPAB": "Positive: lower inflation supports bond prices.",
                "GDX": "Negative/Mixed: lower inflation can reduce gold demand.",
                "SPY": "Positive: lower inflation may support rate-cut expectations.",
                "portfolio": "Generally positive, especially for bonds and equities."
            }
        },
        "Core PCE": {
            "increased": {
                "AGG": "Negative: sticky inflation may keep rates high.",
                "SPAB": "Negative: bond prices may face pressure.",
                "GDX": "Mixed: inflation supports gold, but high real rates can hurt.",
                "SPY": "Negative: the Fed may stay restrictive.",
                "portfolio": "Cautious. Sticky inflation can delay rate cuts."
            },
            "decreased": {
                "AGG": "Positive: cooling inflation supports bonds.",
                "SPAB": "Positive: lower inflation supports fixed income.",
                "GDX": "Mixed: lower inflation may weaken gold demand.",
                "SPY": "Positive: easier Fed expectations can support equities.",
                "portfolio": "Generally positive for bonds and equities."
            }
        },
        "10-Year Treasury": {
            "increased": {
                "AGG": "Negative: bond prices fall when yields rise.",
                "SPAB": "Negative: bond prices fall when yields rise.",
                "GDX": "Negative: higher real yields can hurt gold miners.",
                "SPY": "Negative: higher yields pressure equity valuations.",
                "portfolio": "Negative across most exposures."
            },
            "decreased": {
                "AGG": "Positive: bond prices rise when yields fall.",
                "SPAB": "Positive: bond prices rise when yields fall.",
                "GDX": "Positive: lower yields can support gold miners.",
                "SPY": "Positive: lower yields support valuation multiples.",
                "portfolio": "Positive across most of the portfolio."
            }
        },
        "High Yield Spread": {
            "increased": {
                "AGG": "Mixed/Defensive: high-quality bonds may hold up better.",
                "SPAB": "Mixed/Defensive: aggregate bonds may be safer than equities.",
                "GDX": "Negative/Mixed: risk-off conditions can hurt miners.",
                "SPY": "Negative: wider spreads signal credit stress.",
                "portfolio": "Risk-off signal. SPY and GDX are vulnerable."
            },
            "decreased": {
                "AGG": "Mixed: bonds may lag risk assets.",
                "SPAB": "Mixed: safe bonds may lag when risk appetite improves.",
                "GDX": "Positive/Mixed: easier conditions can help miners.",
                "SPY": "Positive: tighter spreads support equities.",
                "portfolio": "Risk-on signal, mainly helping SPY and possibly GDX."
            }
        }
    }

    if indicator not in impacts:
        return None

    return impacts[indicator][direction]


def calculate_portfolio_returns(price_data):
    daily_returns = price_data.pct_change().dropna()

    weights = pd.Series({
        ticker: details["weight"]
        for ticker, details in PORTFOLIO.items()
    })

    portfolio_returns = daily_returns.dot(weights)
    cumulative_returns = (1 + portfolio_returns).cumprod() - 1

    return daily_returns, portfolio_returns, cumulative_returns


st.title("📊 Macro Intelligence Dashboard")
st.caption("FRED API dashboard with macro interpretation and portfolio impact analysis.")

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Choose dashboard",
    [
        "Macro Dashboard",
        "Portfolio Impact Dashboard"
    ]
)

selected_indicator = st.sidebar.selectbox(
    "Choose macro indicator",
    list(INDICATORS.keys())
)

all_data = {}

for name, code in INDICATORS.items():
    all_data[name] = get_fred_data(code)

selected_df = all_data[selected_indicator]
selected_code = INDICATORS[selected_indicator]
latest, previous, absolute_change, pct_change = calculate_change(selected_df)


if page == "Macro Dashboard":

    st.subheader("📌 Macro KPI Cards")

    cols = st.columns(4)

    for i, (name, code) in enumerate(INDICATORS.items()):
        df = all_data[name]
        latest_i, previous_i, absolute_change_i, pct_change_i = calculate_change(df)
        latest_date = df["date"].iloc[-1].strftime("%d %b %Y")
        status = get_status(name, latest_i)

        with cols[i % 4]:
            st.metric(
                label=f"{name} ({code})",
                value=f"{latest_i:,.2f}",
                delta=arrow(pct_change_i)
            )
            st.write(status)
            st.caption(f"Latest date: {latest_date}")

    st.divider()

    st.subheader(f"📈 Interactive Chart: {selected_indicator}")

    fig = px.line(
        selected_df,
        x="date",
        y="value",
        title=f"{selected_indicator} ({selected_code}) over time"
    )

    st.plotly_chart(fig, use_container_width=True)

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
        latest_i, previous_i, absolute_change_i, pct_change_i = calculate_change(df)
        latest_date = df["date"].iloc[-1].strftime("%d %b %Y")
        status = get_status(name, latest_i)
        explanation_i = explain_indicator(name, pct_change_i)

        scorecard_rows.append({
            "Indicator": name,
            "Code": code,
            "Latest": round(latest_i, 2),
            "% Change": round(pct_change_i, 2),
            "Status": status,
            "Demand Side": explanation_i["demand"],
            "Supply Side": explanation_i["supply"],
            "Economic Impact": explanation_i["impact"],
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
    st.caption("Simple rule-based regime reading using the 8 macro indicators.")


if page == "Portfolio Impact Dashboard":

    st.subheader("💼 Portfolio Impact Dashboard")

    st.write("Equal-weighted portfolio: AGG, SPAB, GDX, SPY — 25% each.")

    tickers = list(PORTFOLIO.keys())

    try:
        prices = get_etf_prices(tickers)
        daily_returns, portfolio_returns, cumulative_returns = calculate_portfolio_returns(prices)

        latest_prices = prices.iloc[-1]
        previous_prices = prices.iloc[-2]
        one_day_returns = ((latest_prices / previous_prices) - 1) * 100

        cols = st.columns(4)

        for i, ticker in enumerate(tickers):
            with cols[i]:
                st.metric(
                    label=f"{ticker} | {PORTFOLIO[ticker]['type']}",
                    value=f"${latest_prices[ticker]:.2f}",
                    delta=f"{one_day_returns[ticker]:.2f}%"
                )
                st.caption(PORTFOLIO[ticker]["name"])
                st.write(f"Weight: {PORTFOLIO[ticker]['weight'] * 100:.0f}%")

        st.divider()

        st.subheader("📈 Portfolio Performance")

        portfolio_df = cumulative_returns.reset_index()
        portfolio_df.columns = ["Date", "Portfolio Return"]

        fig_portfolio = px.line(
            portfolio_df,
            x="Date",
            y="Portfolio Return",
            title="1-Year Cumulative Portfolio Return"
        )

        st.plotly_chart(fig_portfolio, use_container_width=True)

        st.divider()

    except Exception as e:
        st.warning("Could not load ETF price data from Yahoo Finance.")
        st.write(e)

    st.subheader(f"🧠 Portfolio Impact from {selected_indicator}")

    st.metric(
        label=f"{selected_indicator} Change",
        value=f"{absolute_change:,.2f}",
        delta=arrow(pct_change)
    )

    impact = portfolio_impact(selected_indicator, pct_change)

    if impact:
        cols = st.columns(4)

        for i, ticker in enumerate(PORTFOLIO.keys()):
            with cols[i]:
                st.markdown(f"### {ticker}")
                st.write(f"**Asset Type:** {PORTFOLIO[ticker]['type']}")
                st.write(f"**Weight:** {PORTFOLIO[ticker]['weight'] * 100:.0f}%")
                st.write(impact[ticker])

        st.info(f"**Overall Portfolio Impact:** {impact['portfolio']}")

    else:
        st.warning(
            "Portfolio impact logic is strongest for Fed Funds, CPI, Core PCE, "
            "10-Year Treasury, and High Yield Spread."
        )

    st.divider()

    st.subheader("📋 Portfolio Allocation")

    allocation_df = pd.DataFrame([
        {
            "Ticker": ticker,
            "ETF Name": details["name"],
            "Asset Type": details["type"],
            "Weight": f"{details['weight'] * 100:.0f}%"
        }
        for ticker, details in PORTFOLIO.items()
    ])

    st.dataframe(allocation_df, use_container_width=True)
