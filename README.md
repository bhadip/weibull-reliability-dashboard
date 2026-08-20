# 📊 BCore Reliability Dashboard

**Weibull reliability, FMEA risk & PM optimization — WK2 PHE**

🔗 Live: <https://bcore-dashboard.prasanti.com>

A real-time asset-reliability dashboard for oil & gas production assets.
Maintenance and failure data live in Google Sheets; the dashboard validates it,
visualizes Weibull reliability curves, ranks FMEA risk (RPN), and recommends
cost-optimal preventive-maintenance intervals (T-optimum) — with an automatic
"presentation gate" banner so you never present on broken data.

> ⚠️ **DEMO VERSION** — currently utilizing mock-up data for validation and
> testing purposes.

---

## Features (Phase 1)

- ✅ **Presentation gate** — `SYSTEM HEALTHY / DATA ISSUE` banner computed from a
  validation sheet ("STATUS KESELURUHAN").
- 🛡️ **FMEA Register** — sortable failure-mode table with Severity / Occurrence /
  Detection and RPN progress bars.
- 🛠️ **PM Schedule** — cost-optimum PM intervals balancing PM cost vs failure cost.
- 📈 **Asset Chart Dashboard** — per-asset KPIs (β, η, MTTF, T-opt) plus an
  interactive dual-axis Reliability / Failure-Rate curve with T-opt marker.
- 🔄 **Live data** — Google Sheets is the single source of truth; 5-minute cache
  TTL plus a manual **Refresh Data Now** button.
- ✏️ **One-click data entry** — *Update Data (Google Sheet)* button for editors.
- 👀 **Telegram alerts** — owner is pinged when a new viewer opens the dashboard
  (owner bypass via a secret `?vip=` link).
- 🏷️ **White-labeled** — Streamlit branding hidden; custom BCore footer with
  demo disclaimer.

## Architecture

    ┌───────────────┐  published CSV  ┌──────────────────────┐
    │  Google Sheet │ ──────────────► │  Streamlit app        │
    │  (editors)    │                 │  pandas + plotly      │
    └───────────────┘                 └──────────┬───────────┘
                                                 │
                       ┌─────────────────────────┴────────────────────────┐
                       ▼                                                  ▼
            ┌────────────────────┐                             ┌────────────────────────┐
            │ Streamlit Cloud    │                             │ Docker on psth1        │
            │ (public)           │                             │ Tailscale-only :8501   │
            └─────────┬──────────┘                             │ (private dev/backup)   │
                      │ iframe ?embed=true                     └────────────────────────┘
                      ▼
            ┌────────────────────┐
            │ Cloudflare Pages   │
            │ wrapper + branding │
            │ bcore-dashboard.   │
            │ prasanti.com       │
            └────────────────────┘

## Repository structure

    app.py               # the entire dashboard (single-file app)
    requirements.txt
    Dockerfile           # python:3.12-slim runtime
    docker-compose.yml   # bound to Tailscale IP 100.75.220.84:8501
    run.sh               # local launcher (macOS SSL cert fix)
    bcore-web/
      index.html         # Cloudflare Pages white-label wrapper
    .streamlit/
      config.toml        # minimal toolbar (safe to commit)
      secrets.toml       # ⛔ gitignored — NEVER committed

## Secrets

`.streamlit/secrets.toml` (gitignored; also paste into
Streamlit Cloud → *Settings → Secrets*):

    SHEET_ASSET_REGISTER = "https://docs.google.com/spreadsheets/d/e/.../pub?output=csv"
    SHEET_WEIBULL_PARAMS = "https://docs.google.com/spreadsheets/d/e/.../pub?output=csv"
    SHEET_FMEA           = "https://docs.google.com/spreadsheets/d/e/.../pub?output=csv"
    SHEET_PM_SCHEDULE    = "https://docs.google.com/spreadsheets/d/e/.../pub?output=csv"
    SHEET_VALIDATION     = "https://docs.google.com/spreadsheets/d/e/.../pub?output=csv"
    G_SHEET_EDIT_URL     = "https://docs.google.com/spreadsheets/d/.../edit"
    TELEGRAM_BOT_TOKEN   = "..."
    TELEGRAM_CHAT_ID     = "123456789"
    VIP_CODE             = "bcore-owner"

## Run locally

    python3 -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    ./run.sh                 # or: streamlit run app.py

On macOS, `run.sh` exports `SSL_CERT_FILE` from `certifi` to avoid
`CERTIFICATE_VERIFY_FAILED` when fetching Google's published CSVs.

## Deploy

### 1 — Streamlit Community Cloud (public)

`share.streamlit.io` → New app → repo / branch `main` / file `app.py`,
then paste the secrets under *Advanced settings*.

### 2 — White-label wrapper (Cloudflare Pages)

`bcore-web/index.html` embeds the cloud app with `?embed=true` and overlays the
BCore footer over the platform badge. Upload `bcore-web/` as a static
Workers/Pages project and attach the custom domain
`bcore-dashboard.prasanti.com`.

### 3 — Private instance (Docker, Tailscale-only)

    git clone git@github.com:bhadip/weibull-reliability-dashboard.git
    cd weibull-reliability-dashboard
    mkdir -p .streamlit        # add secrets.toml here (not in git)
    docker compose up -d --build
    # → http://100.75.220.84:8501 (Tailnet only)

## Data contract (Google Sheets)

| Dataset (secret key)   | Key columns |
|------------------------|-------------|
| `SHEET_WEIBULL_PARAMS` | asset_id, asset_name, n_events, shape_beta, scale_eta, mttf_days |
| `SHEET_FMEA`           | fmea_id, asset_id, component, failure_mode, failure_effect, severity_S(1-10), occurrence_O(1-10), detection_D(1-10), RPN, priority_rank |
| `SHEET_PM_SCHEDULE`    | asset_id, pm_cost_usd, failure_cost_usd, t_optimum_days, cost_minimum_usd_year |
| `SHEET_VALIDATION`     | "STATUS KESELURUHAN" → status string ("OK - ...") |

Table headers are auto-detected (first row containing the key column name),
so titles/notes above the tables inside a sheet are tolerated.

## Development workflow

- **Aider** (AI pair programmer) on the host:
  `aider --model openai/qwen-max` (OpenAI-compatible DashScope endpoint).
- The compose volume mount auto-reloads Streamlit on every saved edit.
- `yolo` alias = `git add -A && git commit -m "mobile tweak" && git push`;
  pushing redeploys Streamlit Cloud automatically.

## Roadmap (Phase 2)

### 1 — Access control

Authentication to access the Dashboard via **Google OAuth** (or an alternative
OIDC provider). Today the app is open; Phase 2 gates the UI so only authorized
personnel can view reliability data.

### 2 — Practical AI use cases (Qwen-powered)

- **a. Smart Validation** (`validation_check` sheet) — instead of merely
  flagging "Error", an LLM reads the notes column in `failure_event_log` and
  suggests: *"Asset AST-003 has 3 orphan events. Based on notes, these might
  belong to AST-005. Click here to auto-reassign."*
- **b. FMEA Auto-Drafting** — when a new failure mode is logged, the AI
  pre-fills the Severity, Occurrence, and Detection columns based on
  historical patterns from the existing `fmea_register`, requiring only
  human approval.
- **c. Natural Language Query Bar** — a text box at the top of the dashboard:
  *"Generate a table of all Water Injection Pumps needing PM in the next 30
  days, sorted by highest Risk Cost."* The AI translates the prompt into a
  Pandas filter and displays the result.

### 3 — Data source interface via API

Replace the "Publish to web" CSV fetch with a proper API layer
(Google Sheets API v4 with OAuth, or a thin REST wrapper), enabling
write-back, rate-limit handling, and audit trails.

### 4 — Adaptive display

Responsive layout covering tablets and smartphones — the current wide layout
is optimized for desktop/projector use; Phase 2 introduces stacked components,
collapsible tabs, and touch-friendly controls for field staff using the
dashboard from a phone on the rig.

## Host rules

The private instance co-hosts on `psth1`, a home server where **live MT4
trading has absolute resource priority**. This dashboard is deliberately
lightweight (idle ≈ 200 MB RAM) and bound to the Tailscale interface only.

## Credits

Weibull / PM-optimization methodology: **Prof. Djarot (Pakde)** —
Brawijaya Center of Reliability & Integrity Excellences.

---

© 2026 **BCore** • Brawijaya Center Of Reliability & Integrity Excellences
