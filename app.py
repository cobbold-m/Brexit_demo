import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Brexit & UK Stock Markets",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .metric-card {
        background: white;
        padding: 1.2rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        text-align: center;
    }
    h1 { color: #1a2744; }
    h2, h3 { color: #1a2744; }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    # Load stock data
    ftse = pd.read_excel("Dataset10.xlsx", header=[0, 1], index_col=0)
    ftse.index = pd.to_datetime(ftse.index)

    # Reshape to long format
    data_long = ftse.stack(level=0, future_stack=True).reset_index()
    data_long.columns = ['Date', 'Ticker', 'Adj Close', 'Volume']

    # Log returns and volume
    data_long = data_long.sort_values(['Ticker', 'Date'])
    data_long['Log_Return'] = data_long.groupby('Ticker')['Adj Close'].transform(
        lambda s: np.log(s) - np.log(s.shift(1))
    )
    data_long['Log_Volume'] = np.log(data_long['Volume'].replace(0, np.nan))
    data_long = data_long.replace([0, np.inf, -np.inf], np.nan).dropna(subset=['Log_Return', 'Log_Volume'])

    # Monthly aggregation
    monthly = (
        data_long.groupby(['Ticker', pd.Grouper(key='Date', freq='ME')])
        .agg({'Log_Return': 'sum', 'Log_Volume': 'mean'})
        .reset_index()
    )
    monthly['Date'] = monthly['Date'].dt.to_period('M').dt.to_timestamp(how='start')

    # EPU data
    epu = pd.read_excel("epu_data.xlsx")
    epu['Date'] = pd.to_datetime(epu[['year', 'month']].assign(day=1))
    epu = epu.drop(columns=['year', 'month'])
    epu = epu[(epu['Date'] >= '2016-06-01') & (epu['Date'] <= '2020-12-01')]

    # Exposure data
    exposure = pd.read_excel("Exposure_Data.xlsx")

    # Merge
    merged = monthly.merge(epu, on='Date', how='left')
    merged = merged.merge(exposure[['Ticker', 'Exposure']], on='Ticker', how='left')
    merged = merged.dropna(subset=['UK_EPU_Index', 'Exposure'])

    return merged, epu

data, epu = load_data()

# Key events
events = {
    '2016-06-23': 'Brexit Referendum',
    '2017-03-01': 'Article 50 Triggered',
    '2019-01-01': 'Withdrawal Agreement Rejected',
    '2020-01-31': 'UK Leaves EU',
    '2020-03-01': 'COVID-19 Shock',
}

# Header
st.title("📊 Brexit & UK Stock Market Analysis")
st.markdown("**How political uncertainty shaped stock returns and trading volume across 200 UK-listed firms (2016–2020)**")
st.markdown("---")

# Metrics
col1, col2, col3, col4 = st.columns(4)
domestic = data[data['Exposure'] == 'Domestic']
intl = data[data['Exposure'] == 'International']
n_firms = data['Ticker'].nunique()
avg_epu = epu['UK_EPU_Index'].mean()
dom_return = domestic['Log_Return'].mean() * 100
intl_return = intl['Log_Return'].mean() * 100

with col1:
    st.metric("Firms Analysed", f"{n_firms}")
with col2:
    st.metric("Avg UK EPU Index", f"{avg_epu:.0f}")
with col3:
    st.metric("Avg Domestic Monthly Return", f"{dom_return:.2f}%")
with col4:
    st.metric("Avg International Monthly Return", f"{intl_return:.2f}%")

st.markdown("---")

# EPU Chart
st.subheader("UK Economic Policy Uncertainty Index (2016–2020)")
st.caption("Higher values = greater political uncertainty. Key Brexit events marked.")

fig_epu = go.Figure()
fig_epu.add_trace(go.Scatter(
    x=epu['Date'], y=epu['UK_EPU_Index'],
    fill='tozeroy', fillcolor='rgba(26,39,68,0.1)',
    line=dict(color='#1a2744', width=2),
    name='UK EPU Index'
))

colors = ['#e63946', '#f4a261', '#2a9d8f', '#e76f51', '#9b2226']
for (date, label), color in zip(events.items(), colors):
    fig_epu.add_vline(x=date, line_dash='dash', line_color=color, line_width=1.5)
    fig_epu.add_annotation(x=date, y=epu['UK_EPU_Index'].max() * 0.95,
        text=label, showarrow=False, textangle=-90,
        font=dict(size=9, color=color), xanchor='left')

fig_epu.update_layout(
    height=350, plot_bgcolor='white', paper_bgcolor='white',
    xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
    yaxis=dict(showgrid=True, gridcolor='#f0f0f0', title='EPU Index'),
    showlegend=False, margin=dict(t=20, b=20)
)
st.plotly_chart(fig_epu, use_container_width=True)

st.markdown("---")

# Returns comparison
st.subheader("Monthly Returns: Domestic vs International Firms")

dom_monthly = domestic.groupby('Date')['Log_Return'].mean().reset_index()
intl_monthly = intl.groupby('Date')['Log_Return'].mean().reset_index()

fig_ret = go.Figure()
fig_ret.add_trace(go.Scatter(
    x=dom_monthly['Date'], y=dom_monthly['Log_Return'] * 100,
    name='Domestic Firms', line=dict(color='#1a2744', width=2)
))
fig_ret.add_trace(go.Scatter(
    x=intl_monthly['Date'], y=intl_monthly['Log_Return'] * 100,
    name='International Firms', line=dict(color='#c9a84c', width=2)
))
for date, label in events.items():
    fig_ret.add_vline(x=date, line_dash='dot', line_color='#ccc', line_width=1)

fig_ret.update_layout(
    height=350, plot_bgcolor='white', paper_bgcolor='white',
    xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
    yaxis=dict(showgrid=True, gridcolor='#f0f0f0', title='Avg Monthly Log Return (%)'),
    legend=dict(orientation='h', y=1.1),
    margin=dict(t=20, b=20)
)
st.plotly_chart(fig_ret, use_container_width=True)

st.markdown("---")

# EPU vs Returns scatter
st.subheader("EPU vs Stock Returns by Firm Exposure")
st.caption("Each point = one firm-month observation. Shows how firms respond differently to uncertainty.")

col_a, col_b = st.columns(2)

with col_a:
    fig_dom = px.scatter(
        domestic.sample(min(2000, len(domestic))),
        x='UK_EPU_Index', y='Log_Return',
        title='Domestic Firms',
        trendline='ols',
        color_discrete_sequence=['#1a2744'],
        labels={'UK_EPU_Index': 'UK EPU Index', 'Log_Return': 'Monthly Log Return'},
        opacity=0.3
    )
    fig_dom.update_layout(height=350, plot_bgcolor='white', paper_bgcolor='white')
    st.plotly_chart(fig_dom, use_container_width=True)

with col_b:
    fig_intl = px.scatter(
        intl.sample(min(2000, len(intl))),
        x='UK_EPU_Index', y='Log_Return',
        title='International Firms',
        trendline='ols',
        color_discrete_sequence=['#c9a84c'],
        labels={'UK_EPU_Index': 'UK EPU Index', 'Log_Return': 'Monthly Log Return'},
        opacity=0.3
    )
    fig_intl.update_layout(height=350, plot_bgcolor='white', paper_bgcolor='white')
    st.plotly_chart(fig_intl, use_container_width=True)

st.markdown("---")

# Trading volume
st.subheader("Trading Volume: Domestic vs International Firms")
st.caption("Higher volume = more trading activity, often driven by uncertainty.")

dom_vol = domestic.groupby('Date')['Log_Volume'].mean().reset_index()
intl_vol = intl.groupby('Date')['Log_Volume'].mean().reset_index()

fig_vol = go.Figure()
fig_vol.add_trace(go.Scatter(
    x=dom_vol['Date'], y=dom_vol['Log_Volume'],
    name='Domestic', line=dict(color='#1a2744', width=2)
))
fig_vol.add_trace(go.Scatter(
    x=intl_vol['Date'], y=intl_vol['Log_Volume'],
    name='International', line=dict(color='#c9a84c', width=2)
))
for date in events:
    fig_vol.add_vline(x=date, line_dash='dot', line_color='#ccc', line_width=1)

fig_vol.update_layout(
    height=320, plot_bgcolor='white', paper_bgcolor='white',
    xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
    yaxis=dict(showgrid=True, gridcolor='#f0f0f0', title='Avg Log Volume'),
    legend=dict(orientation='h', y=1.1),
    margin=dict(t=20, b=20)
)
st.plotly_chart(fig_vol, use_container_width=True)

st.markdown("---")
st.markdown("""
**About this project** · Analysed using Panel OLS regression on 200 FTSE All-Share firms (2016–2020).
Firm exposure classified using subsidiary data from Orbis. EPU Index sourced from policyuncertainty.com.
Built by [Adjoba Mushia Cobbold](https://cobboldmushia.com) · ICM406 Programming for Finance, Henley Business School.
""")
