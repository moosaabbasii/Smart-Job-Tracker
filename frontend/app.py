import streamlit as st
import requests
import json
import boto3
from botocore.exceptions import ClientError
from datetime import date, datetime, timedelta

# ── CONFIG ────────────────────────────────────────────────────────────────────
API_BASE        = "https://k9gpcxpt4j.execute-api.us-east-1.amazonaws.com/prod"
STATUSES        = ["Applied", "Phone Screen", "Interview", "Offer", "Rejected"]
COGNITO_REGION  = "us-east-1"
USER_POOL_ID    = "us-east-1_4DV0qLF1M"
CLIENT_ID       = "2k1gkrhmlg5hn90kk2apfeen2a"

cognito = boto3.client("cognito-idp", region_name=COGNITO_REGION)

STATUS_STYLE = {
    "Applied":      {"bg": "#EFF6FF", "color": "#2563EB", "border": "#BFDBFE"},
    "Phone Screen": {"bg": "#FFFBEB", "color": "#D97706", "border": "#FDE68A"},
    "Interview":    {"bg": "#F5F3FF", "color": "#7C3AED", "border": "#DDD6FE"},
    "Offer":        {"bg": "#F0FDF4", "color": "#16A34A", "border": "#BBF7D0"},
    "Rejected":     {"bg": "#FEF2F2", "color": "#DC2626", "border": "#FECACA"},
}

st.set_page_config(
    page_title="Smart Job Tracker",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

*, *::before, *::after { font-family: 'Inter', system-ui, sans-serif !important; }
.stApp { background: #F1F5F9 !important; }
.main .block-container { padding: 36px 44px 80px !important; max-width: 1480px !important; }
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #E2E8F0 !important;
}

/* ── BUTTONS: global reset to ghost ── */
.stButton > button {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    border-radius: 7px !important;
    cursor: pointer !important;
    width: auto !important;
    transition: all 0.12s ease !important;
    line-height: 1.5 !important;
    background: #ffffff !important;
    color: #374151 !important;
    border: 1px solid #E2E8F0 !important;
    padding: 5px 12px !important;
    box-shadow: none !important;
}
.stButton > button:hover {
    background: #F8FAFC !important;
    border-color: #CBD5E1 !important;
    color: #0F172A !important;
}

/* Primary button (type="primary") */
.stButton > button[kind="primary"] {
    background: #2563EB !important;
    color: #ffffff !important;
    border: none !important;
    padding: 9px 20px !important;
    font-size: 0.875rem !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 3px rgba(37,99,235,0.25) !important;
}
.stButton > button[kind="primary"]:hover {
    background: #1D4ED8 !important;
    box-shadow: 0 4px 12px rgba(37,99,235,0.3) !important;
    transform: translateY(-1px) !important;
}

/* Delete button — make it danger-colored inline via a data attr trick */
/* We use a preceding st.markdown with a unique id and :has() CSS */
[data-testid="stMarkdownContainer"]:has(.danger-next) + [data-testid="stButton"] > button {
    color: #DC2626 !important;
    border-color: #FECACA !important;
}
[data-testid="stMarkdownContainer"]:has(.danger-next) + [data-testid="stButton"] > button:hover {
    background: #FEF2F2 !important;
}

/* Form submit */
.stFormSubmitButton > button {
    background: #2563EB !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    padding: 9px 22px !important;
    width: auto !important;
}
.stFormSubmitButton > button:hover { background: #1D4ED8 !important; }

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > textarea {
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important;
    background: #ffffff !important;
    color: #0F172A !important;
    font-size: 0.875rem !important;
    padding: 8px 12px !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > textarea:focus {
    border-color: #2563EB !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
}
.stSelectbox > div > div {
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important;
    background: #ffffff !important;
    color: #0F172A !important;
}
.stDateInput > div > div > input {
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important;
    background: #ffffff !important;
    color: #0F172A !important;
}
.stTextInput label, .stTextArea label,
.stSelectbox label, .stDateInput label {
    color: #374151 !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
}

/* Table row hover — using :has() on the horizontal block that follows the row anchor span */
[data-testid="stMarkdownContainer"]:has(.row-anchor) + [data-testid="stHorizontalBlock"] {
    background: #ffffff;
    border-bottom: 1px solid #F1F5F9;
    padding: 0 4px !important;
    margin: 0 !important;
}
[data-testid="stMarkdownContainer"]:has(.row-anchor) + [data-testid="stHorizontalBlock"]:hover {
    background: #F8FAFC !important;
}
/* Remove gap between row anchor and the row columns */
[data-testid="stMarkdownContainer"]:has(.row-anchor) {
    margin-bottom: -8px !important;
    line-height: 0 !important;
}

/* Reduce vertical gap in column blocks for compact table */
[data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] > div {
    gap: 0 !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #F1F5F9; }
::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ── HELPERS ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def fetch_applications(token):
    try:
        r = requests.get(f"{API_BASE}/applications",
                         headers={"Authorization": f"Bearer {token}"}, timeout=8)
        if r.status_code != 200:
            return []
        data = r.json()
        if isinstance(data, str):
            data = json.loads(data)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "body" in data:
            body = data["body"]
            if isinstance(body, str):
                body = json.loads(body)
            return body if isinstance(body, list) else []
        return []
    except Exception:
        return None

def safe_str(val):
    if not val or str(val).strip().lower() in ("none", "null", ""):
        return ""
    return str(val).strip()

def parse_date(val):
    s = safe_str(val)
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None

def status_badge(status):
    s = STATUS_STYLE.get(status, {"bg": "#F1F5F9", "color": "#64748B", "border": "#E2E8F0"})
    return (
        f'<span style="display:inline-flex;align-items:center;padding:3px 10px;'
        f'border-radius:20px;font-size:0.72rem;font-weight:600;line-height:1.4;'
        f'border:1px solid {s["border"]};background:{s["bg"]};color:{s["color"]};'
        f'white-space:nowrap;margin-top:8px">{status}</span>'
    )


# ── ADD APPLICATION DIALOG ────────────────────────────────────────────────────
@st.dialog("New Application")
def add_modal():
    with st.form("add_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        company      = c1.text_input("Company *", placeholder="e.g. Google")
        role         = c2.text_input("Role *",    placeholder="e.g. SWE Intern")
        c3, c4 = st.columns(2)
        status_inp   = c3.selectbox("Status", STATUSES)
        date_applied = c4.date_input("Date Applied", value=date.today())
        c5, c6 = st.columns(2)
        follow_up    = c5.date_input("Follow-up Date (optional)", value=None)
        notes        = c6.text_input("Notes", placeholder="Recruiter, link…")
        submitted    = st.form_submit_button("Add Application", use_container_width=True)
    if submitted:
        if not company.strip() or not role.strip():
            st.error("Company and Role are required.")
        else:
            try:
                r = requests.post(f"{API_BASE}/applications",
                    headers=auth_headers(),
                    json={
                    "company":        company.strip(),
                    "role":           role.strip(),
                    "status":         status_inp,
                    "date_applied":   str(date_applied),
                    "follow_up_date": str(follow_up) if follow_up else "",
                    "notes":          notes.strip(),
                }, timeout=8)
                if r.status_code == 201:
                    fetch_applications.clear()
                    st.success("Application added!")
                    st.rerun()
                else:
                    st.error(f"Error {r.status_code}")
            except Exception as e:
                st.error(f"Connection error: {e}")


# ── SESSION STATE ─────────────────────────────────────────────────────────────
for key in ("editing", "confirm_delete", "show_actions"):
    if key not in st.session_state:
        st.session_state[key] = {}

for key in ("id_token", "auth_mode", "pending_email"):
    if key not in st.session_state:
        st.session_state[key] = None
if st.session_state.auth_mode is None:
    st.session_state.auth_mode = "login"


# ── AUTH FUNCTIONS ────────────────────────────────────────────────────────────
def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.id_token}"}

def cognito_login(email, password):
    try:
        resp = cognito.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": email, "PASSWORD": password},
            ClientId=CLIENT_ID,
        )
        tokens = resp["AuthenticationResult"]
        return tokens["IdToken"], None
    except ClientError as e:
        return None, e.response["Error"]["Message"]

def cognito_signup(email, password):
    try:
        cognito.sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=[{"Name": "email", "Value": email}],
        )
        return None
    except ClientError as e:
        return e.response["Error"]["Message"]

def cognito_confirm(email, code):
    try:
        cognito.confirm_sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            ConfirmationCode=code.strip(),
        )
        return None
    except ClientError as e:
        return e.response["Error"]["Message"]


# ── AUTH GATE ─────────────────────────────────────────────────────────────────
if not st.session_state.id_token:
    st.markdown("""
    <div style="max-width:420px;margin:80px auto 0">
    <h2 style="font-size:1.4rem;font-weight:700;color:#0F172A;margin-bottom:4px">Smart Job Tracker</h2>
    <p style="font-size:0.85rem;color:#94A3B8;margin-bottom:28px">Sign in to your account</p>
    </div>
    """, unsafe_allow_html=True)

    mode = st.session_state.auth_mode

    with st.container():
        col = st.columns([1, 2, 1])[1]
        with col:
            if mode == "login":
                with st.form("login_form"):
                    email    = st.text_input("Email")
                    password = st.text_input("Password", type="password")
                    submitted = st.form_submit_button("Sign In", use_container_width=True)
                if submitted:
                    token, err = cognito_login(email, password)
                    if err:
                        st.error(err)
                    else:
                        st.session_state.id_token = token
                        st.rerun()
                if st.button("Don't have an account? Sign up", use_container_width=True):
                    st.session_state.auth_mode = "signup"
                    st.rerun()

            elif mode == "signup":
                with st.form("signup_form"):
                    email    = st.text_input("Email")
                    password = st.text_input("Password", type="password")
                    submitted = st.form_submit_button("Create Account", use_container_width=True)
                if submitted:
                    err = cognito_signup(email, password)
                    if err:
                        st.error(err)
                    else:
                        st.session_state.pending_email = email
                        st.session_state.auth_mode = "confirm"
                        st.rerun()
                if st.button("Already have an account? Sign in", use_container_width=True):
                    st.session_state.auth_mode = "login"
                    st.rerun()

            elif mode == "confirm":
                st.info(f"Check your email ({st.session_state.pending_email}) for a verification code.")
                with st.form("confirm_form"):
                    code      = st.text_input("Verification Code")
                    submitted = st.form_submit_button("Verify", use_container_width=True)
                if submitted:
                    err = cognito_confirm(st.session_state.pending_email, code)
                    if err:
                        st.error(err)
                    else:
                        st.success("Account verified! Please sign in.")
                        st.session_state.auth_mode = "login"
                        st.rerun()

    st.stop()


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p style="font-size:0.9rem;font-weight:700;color:#0F172A;padding:8px 0 12px">Filters</p>', unsafe_allow_html=True)
    sb_status = st.selectbox("Status", ["All statuses"] + STATUSES, label_visibility="collapsed")
    sb_search = st.text_input("Search", placeholder="Company or role…", label_visibility="collapsed")


# ── FETCH ─────────────────────────────────────────────────────────────────────
apps = fetch_applications(st.session_state.id_token)
if apps is None:
    st.error("Could not reach the API. Check your Lambda & API Gateway setup.")
    st.stop()


# ── STATS ─────────────────────────────────────────────────────────────────────
today    = date.today()
week_ago = today - timedelta(days=7)

total      = len(apps)
this_week  = sum(1 for a in apps if (parse_date(a.get("date_applied")) or date.min) >= week_ago)
responded  = sum(1 for a in apps if a.get("status") in ("Phone Screen", "Interview", "Offer"))
interviews = sum(1 for a in apps if a.get("status") == "Interview")
offers     = sum(1 for a in apps if a.get("status") == "Offer")
active     = sum(1 for a in apps if a.get("status") not in ("Offer", "Rejected"))
resp_rate  = round(responded / total * 100) if total else 0

followups_all = []
for a in apps:
    fu = parse_date(a.get("follow_up_date"))
    if fu and fu <= today + timedelta(days=7) and a.get("status") not in ("Offer", "Rejected"):
        followups_all.append((a, fu))
followups_all.sort(key=lambda x: x[1])
overdue_items  = [(a, fu) for a, fu in followups_all if fu < today]
today_items    = [(a, fu) for a, fu in followups_all if fu == today]
upcoming_items = [(a, fu) for a, fu in followups_all if today < fu <= today + timedelta(days=7)]
due_count = len(followups_all)


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
h1, h2 = st.columns([5, 1])
h1.markdown(f"""
<div style="padding:0 0 8px">
    <h1 style="font-size:1.55rem;font-weight:700;color:#0F172A;margin:0 0 6px;line-height:1.2">
        Smart Job Tracker
    </h1>
    <p style="font-size:0.8rem;color:#94A3B8;margin:0 0 8px">Track applications and follow-ups</p>
    <div style="display:flex;gap:24px;align-items:center">
        <span style="font-size:0.82rem;color:#64748B">
            Active:&nbsp;<strong style="color:#2563EB">{active}</strong>
        </span>
        <span style="color:#E2E8F0">|</span>
        <span style="font-size:0.82rem;color:#64748B">
            Interviews:&nbsp;<strong style="color:#7C3AED">{interviews}</strong>
        </span>
        <span style="color:#E2E8F0">|</span>
        <span style="font-size:0.82rem;color:#64748B">
            Offers:&nbsp;<strong style="color:#16A34A">{offers}</strong>
        </span>
        <span style="color:#E2E8F0">|</span>
        <span style="font-size:0.82rem;color:#64748B">
            Response Rate:&nbsp;<strong style="color:#0F172A">{resp_rate}%</strong>
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

with h2:
    st.markdown('<div style="padding-top:16px">', unsafe_allow_html=True)
    if st.button("+ New Application", key="open_modal", type="primary"):
        add_modal()
    col_r, col_s = st.columns(2)
    with col_r:
        if st.button("🔄", key="refresh", help="Refresh applications"):
            fetch_applications.clear()
            st.rerun()
    with col_s:
        if st.button("Sign Out", key="logout"):
            st.session_state.id_token = None
            fetch_applications.clear()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# KPI CARDS
# ══════════════════════════════════════════════════════════════════════════════
KPI_MUTED = {
    "#2563EB": "#BFDBFE",
    "#7C3AED": "#DDD6FE",
    "#16A34A": "#BBF7D0",
    "#D97706": "#FDE68A",
    "#DC2626": "#FECACA",
}

def kpi_html(label, value, sub, accent, urgent=False):
    bg       = "#FEF2F2" if (urgent and value > 0) else "#ffffff"
    top_full = "#DC2626" if (urgent and value > 0) else accent
    top      = KPI_MUTED.get(top_full, top_full)   # muted pastel version
    vcolor   = "#DC2626" if (urgent and value > 0) else "#0F172A"
    return (
        f'<div style="background:{bg};border:1px solid #E2E8F0;border-radius:12px;'
        f'padding:20px 22px 18px;border-top:2px solid {top};'
        f'box-shadow:0 1px 4px rgba(0,0,0,0.04)">'
        f'<p style="font-size:0.66rem;font-weight:600;color:#94A3B8;text-transform:uppercase;'
        f'letter-spacing:0.09em;margin:0 0 12px">{label}</p>'
        f'<p style="font-size:2.4rem;font-weight:700;color:{vcolor};line-height:1;margin:0 0 8px;'
        f'letter-spacing:-0.02em">{value}</p>'
        f'<p style="font-size:0.75rem;color:#94A3B8;margin:0">{sub}</p>'
        f'</div>'
    )

k1, k2, k3, k4, k5 = st.columns(5)
k1.markdown(kpi_html("Apps this week",  this_week,    f"{total} total all time",                                  "#2563EB"), unsafe_allow_html=True)
k2.markdown(kpi_html("Response rate",   f"{resp_rate}%", f"{responded} of {total} responded",                    "#7C3AED"), unsafe_allow_html=True)
k3.markdown(kpi_html("Interviews",      interviews,   f"{round(interviews/total*100) if total else 0}% of apps",  "#7C3AED"), unsafe_allow_html=True)
k4.markdown(kpi_html("Offers",          offers,       f"{round(offers/total*100) if total else 0}% offer rate",   "#16A34A"), unsafe_allow_html=True)
k5.markdown(kpi_html("Follow-ups due",  due_count,    f"{len(overdue_items)} overdue · {len(today_items)} today", "#D97706", urgent=True), unsafe_allow_html=True)

st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN GRID
# ══════════════════════════════════════════════════════════════════════════════
col_table, col_side = st.columns([5, 2], gap="large")


# ── RIGHT PANEL ───────────────────────────────────────────────────────────────
with col_side:

    # NEEDS ATTENTION ─────────────────────────────────────────────────────────
    parts = []
    if due_count == 0:
        parts += [
            '<div style="background:#ffffff;border:1px solid #E2E8F0;border-radius:12px;'
            'padding:20px 22px;box-shadow:0 1px 4px rgba(0,0,0,0.05)">',
            '<p style="font-size:0.9rem;font-weight:700;color:#0F172A;margin:0 0 10px">Needs Attention</p>',
            '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">',
            '<span style="font-size:0.82rem;font-weight:600;color:#16A34A">&#10003; All caught up</span>',
            '</div>',
            '<p style="font-size:0.78rem;color:#94A3B8;margin:0">No follow-ups due this week.</p>',
            '</div>',
        ]
    else:
        hdr_bg  = "#FFF9F9" if overdue_items else "#FFFDF4"
        hdr_bdr = "#FECACA" if overdue_items else "#FDE68A"
        bdg_col = "#DC2626" if overdue_items else "#D97706"
        warn    = "&#9888;" if overdue_items else "&#9888;"
        parts += [
            f'<div style="background:{hdr_bg};border:1px solid {hdr_bdr};border-radius:12px;'
            f'padding:20px 22px;box-shadow:0 1px 4px rgba(0,0,0,0.05)">',
            f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">',
            f'<span style="font-size:0.9rem;font-weight:700;color:#0F172A">{warn} Needs Attention</span>',
            f'<span style="font-size:0.72rem;font-weight:700;color:#fff;background:{bdg_col};'
            f'padding:2px 9px;border-radius:20px">{due_count}</span>',
            f'</div>',
            f'<p style="font-size:0.78rem;color:#64748B;margin:0 0 16px">',
            f'{due_count} follow-up{"s" if due_count!=1 else ""} need your action</p>',
        ]

        def attn_item(a, fu, kind):
            styles = {
                "overdue":  ("#FFF0F0", "#DC2626", "#DC2626"),
                "today":    ("#FFFBEB", "#D97706", "#D97706"),
                "upcoming": ("#F0FDF4", "#16A34A", "#16A34A"),
            }
            bg, bdr, tc = styles[kind]
            if kind == "overdue":
                days = (today - fu).days
                lbl = f"{days} day{'s' if days!=1 else ''} overdue"
            elif kind == "today":
                lbl = "Due today"
            else:
                d = (fu - today).days
                lbl = f"In {d} day{'s' if d!=1 else ''} &nbsp;&middot;&nbsp; {fu.strftime('%b %d')}"
            return (
                f'<div style="background:{bg};border-left:3px solid {bdr};border-radius:0 8px 8px 0;'
                f'padding:8px 12px;margin-bottom:7px">'
                f'<p style="font-size:0.84rem;font-weight:600;color:#0F172A;margin:0 0 2px">'
                f'{a.get("company","—")}</p>'
                f'<p style="font-size:0.76rem;color:#64748B;margin:0 0 3px">{a.get("role","—")}</p>'
                f'<p style="font-size:0.72rem;font-weight:700;color:{tc};margin:0">{lbl}</p>'
                f'</div>'
            )

        if overdue_items:
            parts.append('<p style="font-size:0.67rem;font-weight:700;color:#DC2626;text-transform:uppercase;letter-spacing:0.07em;margin:0 0 7px">Overdue</p>')
            parts += [attn_item(a, fu, "overdue") for a, fu in overdue_items]
        if today_items:
            parts.append('<p style="font-size:0.67rem;font-weight:700;color:#D97706;text-transform:uppercase;letter-spacing:0.07em;margin:10px 0 7px">Today</p>')
            parts += [attn_item(a, fu, "today")   for a, fu in today_items]
        if upcoming_items:
            parts.append('<p style="font-size:0.67rem;font-weight:700;color:#16A34A;text-transform:uppercase;letter-spacing:0.07em;margin:10px 0 7px">This Week</p>')
            parts += [attn_item(a, fu, "upcoming") for a, fu in upcoming_items]
        parts.append('</div>')

    st.markdown("".join(parts), unsafe_allow_html=True)
    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

    # PIPELINE ────────────────────────────────────────────────────────────────
    pipe = [
        '<div style="background:#ffffff;border:1px solid #E2E8F0;border-radius:12px;'
        'padding:20px 22px;box-shadow:0 1px 4px rgba(0,0,0,0.05)">',
        '<p style="font-size:0.9rem;font-weight:700;color:#0F172A;margin:0 0 4px">Pipeline</p>',
        '<p style="font-size:0.78rem;color:#94A3B8;margin:0 0 16px">Applications by stage</p>',
    ]
    if total > 0:
        for s in STATUSES:
            cnt  = sum(1 for a in apps if a.get("status") == s)
            pct  = (cnt / total * 100) if cnt else 0
            col  = STATUS_STYLE[s]["color"]
            bg   = STATUS_STYLE[s]["bg"]
            pipe.append(
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">'
                f'<span style="font-size:0.79rem;color:#374151;min-width:92px">{s}</span>'
                f'<div style="flex:1;background:#F1F5F9;border-radius:4px;height:5px;overflow:hidden">'
                f'<div style="width:{pct:.0f}%;background:{col};height:100%;border-radius:4px;'
                f'transition:width 0.4s ease"></div></div>'
                f'<span style="font-size:0.79rem;font-weight:{"600" if cnt else "400"};'
                f'color:{"#374151" if cnt else "#CBD5E1"};min-width:18px;text-align:right">{cnt}</span>'
                f'</div>'
            )
    else:
        pipe.append('<p style="font-size:0.82rem;color:#94A3B8;margin:0">No data yet.</p>')
    pipe.append('</div>')
    st.markdown("".join(pipe), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# LEFT: APPLICATIONS TABLE
# ══════════════════════════════════════════════════════════════════════════════
with col_table:

    # Filter bar
    fi1, fi2, fi3 = st.columns([3, 1.5, 1.5])
    with fi1:
        search = st.text_input("s", placeholder="Search company or role…", label_visibility="collapsed")
    with fi2:
        status_sel = st.selectbox("t", ["All statuses"] + STATUSES, label_visibility="collapsed")
    with fi3:
        sort_by = st.selectbox("o", ["Newest first", "Oldest first", "Company A–Z", "Status"],
                               label_visibility="collapsed")

    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

    # Filter + sort logic
    eff_search = search or sb_search
    if status_sel != "All statuses":
        eff_status = [status_sel]
    elif sb_status != "All statuses":
        eff_status = [sb_status]
    else:
        eff_status = STATUSES

    filtered = [
        a for a in apps
        if a.get("status") in eff_status
        and (not eff_search
             or eff_search.lower() in a.get("company","").lower()
             or eff_search.lower() in a.get("role","").lower())
    ]

    def skey(a):
        return parse_date(a.get("date_applied")) or date(2000,1,1)
    if   sort_by == "Newest first":  filtered.sort(key=skey, reverse=True)
    elif sort_by == "Oldest first":  filtered.sort(key=skey)
    elif sort_by == "Company A–Z":   filtered.sort(key=lambda a: a.get("company","").lower())
    elif sort_by == "Status":        filtered.sort(key=lambda a: STATUSES.index(a.get("status")) if a.get("status") in STATUSES else 99)

    # Table header + column labels (one HTML block)
    st.markdown(f"""
<div style="background:#ffffff;border:1px solid #E2E8F0;border-radius:12px 12px 0 0;
            box-shadow:0 1px 4px rgba(0,0,0,0.05)">
    <div style="display:flex;justify-content:space-between;align-items:center;
                padding:14px 20px;border-bottom:1px solid #E2E8F0">
        <span style="font-size:0.9rem;font-weight:700;color:#0F172A">Applications</span>
        <span style="font-size:0.78rem;color:#94A3B8">
            {len(filtered)} result{"s" if len(filtered)!=1 else ""}
        </span>
    </div>
    <div style="display:grid;grid-template-columns:1.7fr 2.2fr 1.4fr 1fr 1fr 0.4fr;
                gap:8px;padding:9px 20px;background:#F8FAFC;border-bottom:1px solid #E2E8F0">
        <span style="font-size:0.66rem;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:0.08em">Company</span>
        <span style="font-size:0.66rem;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:0.08em">Role</span>
        <span style="font-size:0.66rem;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:0.08em">Status</span>
        <span style="font-size:0.66rem;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:0.08em">Applied</span>
        <span style="font-size:0.66rem;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:0.08em">Follow-up</span>
        <span></span>
    </div>
</div>
""", unsafe_allow_html=True)

    if not filtered:
        st.markdown("""
<div style="background:#ffffff;border:1px solid #E2E8F0;border-top:none;
            border-radius:0 0 12px 12px;text-align:center;padding:50px 20px;
            box-shadow:0 1px 4px rgba(0,0,0,0.05)">
    <p style="font-size:0.9rem;font-weight:600;color:#374151;margin:0 0 5px">No applications found</p>
    <p style="font-size:0.82rem;color:#94A3B8;margin:0">Try adjusting your filters</p>
</div>
""", unsafe_allow_html=True)

    else:
        for idx, app in enumerate(filtered):
            app_id    = app["application_id"]
            company_  = app.get("company", "—")
            role_     = app.get("role", "—")
            status_   = app.get("status", "Applied")
            dt        = safe_str(app.get("date_applied"))
            fu_str    = safe_str(app.get("follow_up_date"))
            notes_    = safe_str(app.get("notes"))
            fu_date   = parse_date(fu_str)
            is_last   = idx == len(filtered) - 1
            is_edit   = st.session_state.editing.get(app_id, False)
            confirm   = st.session_state.confirm_delete.get(app_id, False)
            show_act  = st.session_state.show_actions.get(app_id, False)

            if fu_date:
                if   fu_date <  today:                      fu_c, fu_w = "#DC2626", "700"
                elif fu_date == today:                      fu_c, fu_w = "#D97706", "700"
                elif fu_date <= today + timedelta(days=7):  fu_c, fu_w = "#D97706", "500"
                else:                                       fu_c, fu_w = "#94A3B8", "400"
                fu_disp = "Today" if fu_date == today else fu_date.strftime("%b %d")
            else:
                fu_c, fu_w, fu_disp = "#CBD5E1", "400", "—"

            row_bg = "#F8FAFC" if is_edit else "#ffffff"
            bdr_b  = "1px solid #F1F5F9" if not is_last else "none"
            bdr_r  = "0 0 12px 12px"      if is_last    else "0"

            # Row anchor — CSS :has() targets the NEXT stHorizontalBlock
            st.markdown(f'<span class="row-anchor" id="r{app_id[:8]}"></span>', unsafe_allow_html=True)

            # ── ROW: all 6 columns in one st.columns call ──────────────────
            c1, c2, c3, c4, c5, c6 = st.columns([1.7, 2.2, 1.4, 1, 1, 0.4])

            c1.markdown(
                f'<p style="font-size:0.875rem;font-weight:600;color:#0F172A;margin:5px 0 5px;'
                f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{company_}">'
                f'{company_}</p>',
                unsafe_allow_html=True
            )
            c2.markdown(
                f'<p style="font-size:0.855rem;color:#374151;margin:8px 0;'
                f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{role_}">'
                f'{role_}</p>',
                unsafe_allow_html=True
            )
            c3.markdown(status_badge(status_), unsafe_allow_html=True)
            c4.markdown(
                f'<p style="font-size:0.8rem;color:#94A3B8;margin:5px 0">{dt if dt else "—"}</p>',
                unsafe_allow_html=True
            )
            c5.markdown(
                f'<p style="font-size:0.8rem;color:{fu_c};font-weight:{fu_w};margin:5px 0">'
                f'{fu_disp}</p>',
                unsafe_allow_html=True
            )
            with c6:
                dot_label = "✕" if show_act else "⋮"
                if st.button(dot_label, key=f"dots_{app_id}"):
                    new_val = not show_act
                    st.session_state.show_actions = {app_id: new_val}
                    st.rerun()

            # Bottom border for the row
            st.markdown(
                f'<div style="border-bottom:{bdr_b};border-left:1px solid #E2E8F0;'
                f'border-right:1px solid #E2E8F0;border-radius:{bdr_r};height:1px;'
                f'background:{row_bg};margin-top:-2px"></div>',
                unsafe_allow_html=True
            )

            # ── ACTION ROW ─────────────────────────────────────────────────
            if show_act and not confirm:
                _, a_edit, a_del = st.columns([8.5, 1, 1])
                edit_lbl = "Close" if is_edit else "Edit"
                if a_edit.button(edit_lbl, key=f"edit_{app_id}"):
                    st.session_state.editing[app_id] = not is_edit
                    st.rerun()
                if a_del.button("Delete", key=f"del_{app_id}"):
                    st.session_state.confirm_delete[app_id] = True
                    st.rerun()

            if confirm:
                _, cw, cy, cn = st.columns([4.5, 3, 0.9, 0.9])
                cw.markdown(
                    f'<p style="font-size:0.82rem;color:#DC2626;padding-top:8px;margin:0">'
                    f'Delete <b>{role_}</b> at <b>{company_}</b>?</p>',
                    unsafe_allow_html=True
                )
                if cy.button("Yes", key=f"yes_{app_id}"):
                    try:
                        r3 = requests.delete(f"{API_BASE}/applications/{app_id}",
                                             headers=auth_headers(), timeout=8)
                        if r3.status_code == 200:
                            fetch_applications.clear()
                            st.session_state.confirm_delete[app_id] = False
                            st.session_state.show_actions[app_id]   = False
                            st.rerun()
                        else:
                            st.error(f"Error {r3.status_code}")
                    except Exception as e:
                        st.error(str(e))
                if cn.button("No", key=f"no_{app_id}"):
                    st.session_state.confirm_delete[app_id] = False
                    st.rerun()

            # ── EDIT FORM ──────────────────────────────────────────────────
            if is_edit:
                with st.form(f"upd_{app_id}"):
                    e1, e2, e3 = st.columns(3)
                    new_status = e1.selectbox(
                        "Status", STATUSES,
                        index=STATUSES.index(status_) if status_ in STATUSES else 0,
                        key=f"s_{app_id}"
                    )
                    new_fu    = e2.text_input("Follow-up (YYYY-MM-DD)", value=fu_str, key=f"f_{app_id}")
                    new_notes = e3.text_input("Notes", value=notes_, key=f"n_{app_id}")
                    if st.form_submit_button("Save Changes"):
                        try:
                            r2 = requests.put(
                                f"{API_BASE}/applications/{app_id}",
                                headers=auth_headers(),
                                json={"status": new_status, "notes": new_notes,
                                      "follow_up_date": new_fu},
                                timeout=8
                            )
                            if r2.status_code == 200:
                                fetch_applications.clear()
                                st.session_state.editing[app_id]      = False
                                st.session_state.show_actions[app_id] = False
                                st.success("Saved.")
                                st.rerun()
                            else:
                                st.error(f"Error {r2.status_code}")
                        except Exception as e:
                            st.error(str(e))
