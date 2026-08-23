# BCore Dashboard - Managed via Aider on psth1
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="BCore Reliability Dashboard", page_icon="📊", layout="wide")

REQUIRED_SECRETS = ["SHEET_ASSET_REGISTER", "SHEET_WEIBULL_PARAMS", "SHEET_FMEA",
                    "SHEET_PM_SCHEDULE", "SHEET_VALIDATION"]
missing = [k for k in REQUIRED_SECRETS if k not in st.secrets]
if missing:
    st.error(f"secrets.toml is missing keys: {', '.join(missing)}. Add the published CSV URLs.")
    st.stop()

# --- TELEGRAM VIEWER NOTIFICATION ---
def _tg_notify(msg):
    import requests as _rq
    token = st.secrets.get("TELEGRAM_BOT_TOKEN", "MISSING")
    chat_id = st.secrets.get("TELEGRAM_CHAT_ID", "MISSING")
    if token == "MISSING" or chat_id == "MISSING": return
    try:
        _rq.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": msg},
            timeout=60,
        )
    except Exception: pass

_vip_code = st.secrets.get("VIP_CODE", "bcore-owner")
is_vip = st.query_params.get("vip", "") == _vip_code
if not is_vip and not st.session_state.get("tg_sent", False):
    st.session_state["tg_sent"] = True
    from datetime import datetime as _dt
    _tz = "unknown"
    try: _tz = st.context.timezone
    except: pass
    _tg_notify(f"👀 New viewer opened BCore Dashboard\n🕒 {_dt.now().strftime('%Y-%m-%d %H:%M')}\n🌐 {_tz}")

# --- DATA LOADING ---
@st.cache_data(ttl=300)
def read_sheet_csv(url: str, header_keyword: str) -> pd.DataFrame:
    import requests, io
    resp = requests.get(url, timeout=60, headers={'User-Agent': 'Mozilla/5.0'})
    resp.raise_for_status()
    raw = pd.read_csv(io.StringIO(resp.text), header=None)
    header_idx = None
    for i in range(min(20, len(raw))):
        cells = [str(v).strip().lower() for v in raw.iloc[i].tolist()]
        if any(header_keyword.lower() in c for c in cells):
            header_idx = i
            break
    if header_idx is None: raise ValueError(f"Header '{header_keyword}' not found.")
    df = raw.iloc[header_idx + 1:].reset_index(drop=True)
    df.columns = [str(c).strip() for c in raw.iloc[header_idx].tolist()]
    return df.dropna(how="all")

@st.cache_data(ttl=300)
def read_overall_status(url: str) -> str:
    import urllib.request, io
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = pd.read_csv(io.StringIO(response.read().decode('utf-8')), header=None)
    except Exception as e:
        return f"FETCH_ERROR: {str(e)}"
    for i in range(min(20, len(raw))):
        if "STATUS KESELURUHAN" in str(raw.iloc[i, 0]).upper():
            return str(raw.iloc[i, 1])
    return "UNKNOWN"

def to_num(df, cols):
    df = df.copy()
    for c in cols:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

try:
    df_weibull = to_num(read_sheet_csv(st.secrets["SHEET_WEIBULL_PARAMS"], "asset_id"),
                        ["n_events", "shape_beta", "scale_eta", "mttf_days"]).dropna(subset=["asset_id"])
    df_fmea = to_num(read_sheet_csv(st.secrets["SHEET_FMEA"], "fmea_id"),
                     ["severity_S(1-10)", "occurrence_O(1-10)", "detection_D(1-10)",
                      "RPN", "priority_rank"]).dropna(subset=["fmea_id"])
    df_pm = to_num(read_sheet_csv(st.secrets["SHEET_PM_SCHEDULE"], "asset_id"),
                   ["pm_cost_usd", "failure_cost_usd", "t_optimum_days",
                    "cost_minimum_usd_year"]).dropna(subset=["asset_id"])
    overall_status = read_overall_status(st.secrets["SHEET_VALIDATION"])
except Exception as e:
    st.error(f"Failed to load data from Google Sheets: {e}")
    st.stop()

# --- HEADER ---
st.title("📊 BCore Reliability Dashboard")
st.caption("Weibull reliability, FMEA risk & PM optimization — WK2 PHE • auto-refresh 5 min")

if "OK" in overall_status.upper():
    st.success(f"SYSTEM HEALTHY — {overall_status}", icon="✅")
else:
    st.error(f"DATA ISSUE — {overall_status}. Check the Google Sheet before presenting.", icon="🚨")

if st.button("🔄 Refresh Data Now"):
    st.cache_data.clear()
    st.rerun()

edit_url = st.secrets.get("G_SHEET_EDIT_URL", "#")
if edit_url != "#":
    st.link_button("✏️ Update Data (Google Sheet)", edit_url)

# --- TABS ---
tab_fmea, tab_pm, tab_chart = st.tabs(["🛡️ FMEA Register", "🛠️ PM Schedule", "📈 Asset Chart Dashboard"])

with tab_fmea:
    st.subheader("Failure Mode & Effects Analysis")
    st.dataframe(df_fmea, hide_index=True, use_container_width=True,
                 column_config={"RPN": st.column_config.ProgressColumn("RPN", min_value=0, max_value=500, format="%.0f")})

with tab_pm:
    st.subheader("Preventive Maintenance Optimization")
    st.dataframe(df_pm, hide_index=True, use_container_width=True,
                 column_config={
                     "t_optimum_days": st.column_config.NumberColumn("T-optimum (days)", format="%.1f"),
                     "cost_minimum_usd_year": st.column_config.NumberColumn("Cost Min (USD/yr)", format="%.0f")})

with tab_chart:
    st.subheader("Weibull Reliability & Failure Rate Curves")
    names = df_weibull.set_index("asset_id")["asset_name"]
    selected = st.selectbox("Select Asset ID:", names.index.tolist(),
                            format_func=lambda a: f"{a} — {names[a]}")
    row = df_weibull[df_weibull["asset_id"] == selected].iloc[0]
    beta, eta, mttf = float(row["shape_beta"]), float(row["scale_eta"]), float(row["mttf_days"])
    pm = df_pm[df_pm["asset_id"] == selected]
    t_opt = float(pm["t_optimum_days"].iloc[0]) if len(pm) and pd.notna(pm["t_optimum_days"].iloc[0]) else None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Shape (β)", f"{beta:.4f}")
    c2.metric("Scale (η)", f"{eta:.2f} days")
    c3.metric("MTTF", f"{mttf:.2f} days")
    c4.metric("T-optimum PM", f"{t_opt:.2f} days" if t_opt else "—")

    t = np.linspace(0, 450, 451)
    with np.errstate(divide="ignore", invalid="ignore"):
        rel = np.exp(-((t / eta) ** beta)) * 100.0
        fr = (beta / eta) * ((t / eta) ** (beta - 1.0))
    fr = np.nan_to_num(fr, nan=0.0, posinf=0.0)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=rel, name="Reliability (%)", line=dict(color="#1f77b4", width=2.5)))
    fig.add_trace(go.Scatter(x=t, y=fr, name="Failure Rate", yaxis="y2", line=dict(color="#d62728", width=2, dash="dash")))
    if t_opt:
        fig.add_vline(x=t_opt, line_width=1.5, line_dash="dot", line_color="#2ca02c",
                      annotation_text=f"T-opt {t_opt:.0f}d", annotation_position="top left")
    fig.update_layout(
        height=540, hovermode="x unified",
        xaxis=dict(title="Time (days)", range=[0, 450]),
        yaxis=dict(title="Reliability (%)", range=[0, 105]),
        yaxis2=dict(title="Failure Rate", overlaying="y", side="right"),
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.6)"))
    st.plotly_chart(fig, use_container_width=True)
