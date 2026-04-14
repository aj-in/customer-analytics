"""
app.py — Customer Analytics
"""
import sqlite3, warnings, io, os, hashlib
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")

DB_PATH = "reviews.db"
ENRICHED_DB_PATH = "enriched_reviews.db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
N_CLUSTERS_FINE = 14
N_CLUSTERS_PARENT = 6
OUTLIER_PERCENTILE = 15
ADMIN_USER = "admin"
ADMIN_PASS_HASH = hashlib.sha256("admin123".encode()).hexdigest()

NEGATIVE_LABELS = [
    "Dirty Room","Room Smell & Mold","Uncomfortable Bed","Broken AC/Heating",
    "Pest Infestation","Rude Staff","Slow Check-in","Unresponsive Front Desk",
    "Long Phone Wait","Billing Errors","Stale Breakfast","Slow Room Service",
    "Limited Menu","Food Hygiene Issue","Unsafe Neighborhood",
    "Parking Problems","Far From Center","Slow WiFi","Dirty Pool",
    "Broken Elevator","Outdated Gym","Thin Walls","Construction Noise",
    "Overpriced","Hidden Fees","Excessive Resort Fee","Refund Delays",
    "Wrong Room","Lost Reservation","Overbooking","Misleading Photos",
]
POSITIVE_LABELS = [
    "Excellent Room","Spotless Cleaning","Friendly Staff",
    "Outstanding Service","Great Breakfast","Excellent Restaurant",
    "Perfect Location","Beautiful Pool","Great Spa","Fast WiFi",
    "Good Value","Smooth Check-in","Quiet Room","Thoughtful Touches",
    "Great Anniversary Experience","Family Friendly",
]
NEUTRAL_LABELS = ["Mixed Experience","Average Stay"]


# ═══════════════════════════════════════════════════════════════════════════════
#  CSS — Glass UI + Dark Navbar
# ═══════════════════════════════════════════════════════════════════════════════

def inject_css():
    is_admin = st.session_state.get("admin_logged_in", False)
    dark = st.session_state.get("dark_mode", False)
    badge = '<span class="admin-badge">Admin</span>' if is_admin else ""
    muted = "rgba(255,255,255,0.4)" if dark else "rgba(0,0,0,0.45)"

    # Dark mode override CSS (only injected when toggled on)
    dark_override = """
    .stApp { background-color: #0e1117 !important; }
    .stApp, .stApp p, .stApp span, .stApp li, .stApp label,
    .stApp div, .stApp td, .stApp th { color: #e0e0e0 !important; }
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: #ffffff !important; }
    section[data-testid="stSidebar"] { background-color: #161b22 !important; }
    section[data-testid="stSidebar"] *, .stTabs [data-baseweb="tab"] { color: #e0e0e0 !important; }
    details { background: rgba(255,255,255,0.02) !important; border-color: rgba(255,255,255,0.06) !important; }
    """ if dark else ""

    st.markdown(f"""
    <style>
    .custom-nav {{
        position: fixed; top: 0; left: 0; right: 0; z-index: 999999;
        height: 52px; background: #0e1117;
        border-bottom: 1px solid rgba(255,255,255,0.06);
        display: flex; align-items: center; justify-content: space-between; padding: 0 28px;
    }}
    .custom-nav .nav-title {{ color: #fff; font-size: 1.0rem; font-weight: 600; }}
    .custom-nav .admin-badge {{
        background: rgba(46,204,113,0.12); border: 1px solid rgba(46,204,113,0.4);
        color: #2ecc71; padding: 3px 12px; border-radius: 14px; font-size: 0.72rem;
    }}
    .block-container {{ padding-top: 64px !important; }}
    header[data-testid="stHeader"] {{ background: transparent !important; z-index: 0 !important; }}

    [data-testid="stMetric"] {{
        background: rgba(74,144,217,0.06); border: 1px solid rgba(74,144,217,0.15);
        border-radius: 12px; padding: 14px 18px;
    }}
    [data-testid="stMetric"] label {{
        font-size: 0.8rem !important; font-weight: 600 !important;
        text-transform: uppercase !important; letter-spacing: 0.5px !important;
    }}

    .stDownloadButton > button > div > svg {{ display: none !important; }}
    .stDownloadButton > button {{
        border: 1px solid rgba(74,144,217,0.4) !important; color: #4A90D9 !important;
        background: rgba(74,144,217,0.06) !important; border-radius: 8px !important;
    }}
    .stDownloadButton > button:hover {{ background: rgba(74,144,217,0.15) !important; }}

    .ticket-card {{
        background: {"rgba(255,255,255,0.025)" if dark else "rgba(0,0,0,0.02)"};
        border: 1px solid {"rgba(255,255,255,0.07)" if dark else "rgba(0,0,0,0.08)"};
        border-radius: 10px; padding: 14px 18px; margin-bottom: 8px;
    }}
    .ticket-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }}
    .ticket-id {{ background: rgba(74,144,217,0.12); color: #4A90D9; padding: 2px 10px; border-radius: 6px; font-size: 0.78rem; font-weight: 600; }}
    .ticket-time {{ color: #e74c3c; font-size: 0.78rem; font-weight: 500; }}
    .ticket-likes {{ color: {muted}; font-size: 0.78rem; }}
    .ticket-branch {{ color: {muted}; font-size: 0.75rem; }}

    {dark_override}
    </style>
    <div class="custom-nav">
        <span class="nav-title">Customer Analytics</span>
        {badge}
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA
# ═══════════════════════════════════════════════════════════════════════════════

def load_reviews_from_db(db_path):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM google_reviews", conn)
    conn.close()
    df["review_date"] = pd.to_datetime(df["review_date"])
    df["sentiment"] = df["rating"].apply(lambda r: "Positive" if r >= 4 else ("Negative" if r <= 2 else "Neutral"))
    df["week_start"] = df["review_date"].dt.to_period("W").apply(lambda p: p.start_time)
    return df


def save_enriched_db(df, path):
    conn = sqlite3.connect(path)
    s = df.copy()
    for c in s.select_dtypes(include=["datetime64"]).columns:
        s[c] = s[c].astype(str)
    if "week_start" in s.columns:
        s["week_start"] = s["week_start"].astype(str)
    s.to_sql("enriched_reviews", conn, if_exists="replace", index=False)
    conn.close()


def load_admin_config(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM admin_config", conn)
    conn.close()
    return df


def save_admin_config_row(branch, source, api_key, place_id, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT config_id FROM admin_config WHERE branch_name=? AND review_source=?", (branch, source))
    ex = cur.fetchone()
    if ex:
        cur.execute("UPDATE admin_config SET api_key=?, place_id=? WHERE config_id=?", (api_key, place_id, ex[0]))
    else:
        cur.execute("INSERT INTO admin_config (branch_name,review_source,api_key,place_id,is_active) VALUES(?,?,?,?,1)", (branch, source, api_key, place_id))
    conn.commit(); conn.close()


def update_admin_field(cid, field, val, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.execute(f"UPDATE admin_config SET {field}=? WHERE config_id=?", (val, cid))
    conn.commit(); conn.close()


def delete_admin_config(cid, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM admin_config WHERE config_id=?", (cid,))
    conn.commit(); conn.close()


def update_last_refresh(branch, source, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE admin_config SET last_refresh=? WHERE branch_name=? AND review_source=?",
                 (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), branch, source))
    conn.commit(); conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  NLP
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def load_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL)

@st.cache_data
def generate_embeddings(texts: tuple):
    return np.array(load_model().encode(list(texts), show_progress_bar=False, batch_size=64))

def assign_simplified_labels(embeddings, cluster_labels, cluster_ratings):
    model = load_model()
    from sklearn.metrics.pairwise import cosine_similarity
    neg_e = model.encode(NEGATIVE_LABELS, show_progress_bar=False)
    pos_e = model.encode(POSITIVE_LABELS, show_progress_bar=False)
    neu_e = model.encode(NEUTRAL_LABELS, show_progress_bar=False)
    arr = np.array(cluster_labels); mapping = {}; used = set()
    for cid in sorted(set(cluster_labels)):
        cent = embeddings[arr == cid].mean(axis=0).reshape(1, -1)
        ar = cluster_ratings[cid]
        if ar >= 3.8: pool, pe = POSITIVE_LABELS, pos_e
        elif ar <= 2.5: pool, pe = NEGATIVE_LABELS, neg_e
        else: pool, pe = NEUTRAL_LABELS + NEGATIVE_LABELS, np.vstack([neu_e, neg_e])
        sims = cosine_similarity(cent, pe)[0]
        for idx in sims.argsort()[::-1]:
            c = pool[idx]
            if c not in used: mapping[cid] = c; used.add(c); break
        else: mapping[cid] = f"Issue {cid}"
    return mapping

def detect_mixed(texts):
    pos = {"loved","excellent","amazing","beautiful","perfect","wonderful","great","fantastic","best","incredible","outstanding","spotless","heavenly","friendly","comfortable","stunning","recommend","priceless","magical"}
    neg = {"terrible","horrible","worst","dirty","rude","broken","disgusting","slow","cold","noisy","smelly","stained","filthy","overcharged","nightmare","refused","ignored","disappointing","unacceptable","infuriating"}
    out = []
    for t in texts:
        w = set(t.lower().split())
        hp, hn = bool(w & pos), bool(w & neg)
        out.append("Mixed" if hp and hn else ("Positive" if hp else ("Negative" if hn else "Neutral")))
    return out

def run_pipeline(df):
    texts = tuple(df["review_text"].tolist())
    with st.spinner("Generating embeddings..."): embeddings = generate_embeddings(texts)
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
    with st.spinner("Clustering..."):
        km = KMeans(n_clusters=N_CLUSTERS_FINE, random_state=42, n_init=10)
        fl = km.fit_predict(embeddings); df["cluster_id"] = fl
    with st.spinner("Labeling..."):
        lmap = {}
        for cid in sorted(df["cluster_id"].unique()):
            tx = df.loc[df["cluster_id"]==cid, "review_text"].tolist()
            if len(tx) < 2: lmap[cid] = f"Misc {cid}"; continue
            tv = TfidfVectorizer(max_features=200, stop_words="english", ngram_range=(1,2), min_df=1)
            m = tv.fit_transform(tx); n = tv.get_feature_names_out()
            a = np.asarray(m.mean(axis=0)).flatten()
            lmap[cid] = " / ".join(n[i] for i in a.argsort()[-3:][::-1]).title()
        df["issue_subcategory"] = df["cluster_id"].map(lmap)
    with st.spinner("Simplifying..."):
        cr = df.groupby("cluster_id")["rating"].mean().to_dict()
        df["issue_type"] = df["cluster_id"].map(assign_simplified_labels(embeddings, tuple(fl), cr))
    with st.spinner("Parent categories..."):
        uf = np.unique(fl)
        cents = np.array([embeddings[fl==c].mean(axis=0) for c in uf])
        km2 = KMeans(n_clusters=min(N_CLUSTERS_PARENT, len(uf)), random_state=42, n_init=10)
        pof = km2.fit_predict(cents); f2p = dict(zip(uf, pof))
        df["parent_cluster_id"] = [f2p[f] for f in fl]
        pmap = {}
        for pid in sorted(df["parent_cluster_id"].unique()):
            tx = df.loc[df["parent_cluster_id"]==pid, "review_text"].tolist()
            if len(tx) < 2: pmap[pid] = f"Group {pid}"; continue
            tv = TfidfVectorizer(max_features=200, stop_words="english", ngram_range=(1,2), min_df=1)
            m = tv.fit_transform(tx); n = tv.get_feature_names_out()
            a = np.asarray(m.mean(axis=0)).flatten()
            pmap[pid] = " / ".join(n[i] for i in a.argsort()[-3:][::-1]).title()
        df["issue_category"] = df["parent_cluster_id"].map(pmap)
    with st.spinner("Confidence..."):
        from sklearn.metrics.pairwise import cosine_distances
        dists = np.array([cosine_distances([embeddings[i]], [km.cluster_centers_[fl[i]]])[0][0] for i in range(len(embeddings))])
        df["confidence_distance"] = dists
        df["is_uncategorizable"] = dists > np.percentile(dists, 100 - OUTLIER_PERCENTILE)
    df["aspect_sentiment"] = detect_mixed(df["review_text"].tolist())
    df["is_complaint"] = df["rating"] <= 2
    df["is_positive"] = df["rating"] >= 4
    # Compute hours since review
    df["hours_since"] = ((datetime.now() - df["review_date"]).dt.total_seconds() / 3600).round(1)
    save_enriched_db(df, ENRICHED_DB_PATH)
    st.session_state["pipeline_df"] = df
    st.session_state["pipeline_embeddings"] = embeddings
    st.session_state["last_pipeline_run"] = datetime.now()
    return df, embeddings


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def fmt_ago(dt):
    if dt is None: return "Never"
    s = int((datetime.now() - dt).total_seconds())
    if s < 60: return f"{s}s ago"
    m = s // 60
    if m < 60: return f"{m} min ago"
    h, rm = s // 3600, (s % 3600) // 60
    if h < 24: return f"{h} hr {rm} min ago"
    d, rh = s // 86400, (s % 86400) // 3600
    return f"{d} day{'s' if d>1 else ''} {rh} hr ago"

def fmt_hours(h):
    if h < 24: return f"{h:.1f} hrs"
    d = int(h // 24); rh = h % 24
    return f"{d}d {rh:.0f}h"


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    st.set_page_config(page_title="Customer Analytics", page_icon="📊", layout="wide")
    inject_css()

    if "admin_logged_in" not in st.session_state: st.session_state.admin_logged_in = False
    if "last_pipeline_run" not in st.session_state: st.session_state.last_pipeline_run = None
    if "dark_mode" not in st.session_state: st.session_state.dark_mode = False

    import plotly.io as pio
    pio.templates.default = "plotly_dark" if st.session_state.dark_mode else "plotly_white"

    if "pipeline_df" not in st.session_state:
        try: raw = load_reviews_from_db(DB_PATH)
        except Exception as e: st.error(f"Run `python setup_database.py` first.\n\n{e}"); return
        run_pipeline(raw)

    df = st.session_state["pipeline_df"]
    embeddings = st.session_state["pipeline_embeddings"]

    # ── Sidebar ──────────────────────────────────────────────────────────────
    st.sidebar.header("Filters")
    st.sidebar.caption(f"Last refresh: {fmt_ago(st.session_state.get('last_pipeline_run'))}")
    st.sidebar.markdown("---")

    time_preset = st.sidebar.radio("Time", ["All Time","Last 24 Hours","Last 2 Days","Last 7 Days","Last 30 Days"], horizontal=True)
    ts_map = {"Last 24 Hours": 1, "Last 2 Days": 2, "Last 7 Days": 7, "Last 30 Days": 30}
    time_start = datetime.now() - timedelta(days=ts_map[time_preset]) if time_preset in ts_map else None
    dr = None
    if time_preset == "All Time":
        mn, mx = df["review_date"].min().date(), df["review_date"].max().date()
        dr = st.sidebar.date_input("Range", value=(mn, mx), min_value=mn, max_value=mx)

    st.sidebar.markdown("---")
    sent_f = st.sidebar.multiselect("Sentiment", ["Positive","Neutral","Negative"], default=["Positive","Neutral","Negative"])
    rat_f = st.sidebar.slider("Rating", 1, 5, (1, 5))
    br_f = st.sidebar.multiselect("Branch", sorted(df["branch_name"].unique()), default=sorted(df["branch_name"].unique()))
    src_f = st.sidebar.multiselect("Source", sorted(df["review_source"].unique()), default=sorted(df["review_source"].unique()))
    res_f = st.sidebar.radio("Resolution", ["All","Resolved","Unresolved"], index=0)

    # Dark mode toggle at bottom of filters
    st.sidebar.markdown("---")
    dark_toggle = st.sidebar.toggle("Dark Mode", value=st.session_state.dark_mode)
    if dark_toggle != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_toggle
        st.rerun()

    mask = (df["sentiment"].isin(sent_f) & df["rating"].between(rat_f[0], rat_f[1])
            & df["branch_name"].isin(br_f) & df["review_source"].isin(src_f))
    if time_start: mask &= df["review_date"] >= time_start
    elif time_preset == "All Time" and isinstance(dr, tuple) and len(dr) == 2:
        mask &= (df["review_date"].dt.date >= dr[0]) & (df["review_date"].dt.date <= dr[1])
    if res_f == "Resolved": mask &= df["is_resolved"] == "Yes"
    elif res_f == "Unresolved": mask &= df["is_resolved"] == "No"

    filtered = df[mask].copy()

    # ══════════════════════════════════════════════════════════════════════════
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Executive Summary", "🔬 Semantic Search",
        "❓ Uncategorizable", "📋 Complaint Tickets", "📥 Data Export", "🔑 Admin"])

    # ══════════════════════════════════════════════════════════════════════════
    #  TAB 1 — EXECUTIVE SUMMARY
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        comp_count = int(filtered["is_complaint"].sum())
        unres_count = int(((filtered["is_resolved"]=="No") & filtered["is_complaint"]).sum())

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Reviews", len(filtered))
        c2.metric("Avg Rating", f"{filtered['rating'].mean():.1f}" if len(filtered) else "—")
        c3.metric("Complaints", comp_count)
        c4.metric("Unresolved", unres_count)
        c5.metric("Issue Types", filtered["issue_type"].nunique())

        st.markdown("---")

        # ── Donut (full row) ─────────────────────────────────────────────────
        st.subheader("Issue Distribution")
        donut_sent = st.multiselect("Show issues for:", ["Negative","Neutral","Positive"],
                                     default=["Negative","Neutral"], key="donut_filter")
        dd = filtered[filtered["sentiment"].isin(donut_sent)] if donut_sent else filtered
        if not dd.empty:
            cts = dd["issue_type"].value_counts().reset_index()
            cts.columns = ["issue_type", "count"]
            fig = px.pie(cts, values="count", names="issue_type", hole=0.5,
                         color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_traces(textposition="inside", textinfo="percent+label", textfont_size=10,
                              hovertemplate="<b>%{label}</b><br>Total Issues: %{value}<extra></extra>")
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=500,
                              legend=dict(orientation="h", y=-0.12, font=dict(size=9)))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data for selected filters.")

        st.markdown("---")

        # ── Resolution + Branch histogram ────────────────────────────────────
        cl, cr = st.columns(2)
        with cl:
            nn = filtered[filtered["sentiment"].isin(["Negative","Neutral"])]
            if not nn.empty:
                ry = (nn["is_resolved"]=="Yes").sum(); rn = len(nn) - ry
                fig = go.Figure(data=[go.Pie(labels=["Resolved","Unresolved"], values=[ry, rn],
                    hole=0.45, marker_colors=["#2ecc71","#e74c3c"], textinfo="value+percent",
                    hovertemplate="<b>%{label}</b><br>Total: %{value}<extra></extra>")])
                fig.update_layout(title="Complaint Resolution", margin=dict(t=50,b=20), height=380,
                                  legend=dict(orientation="h",y=-0.1))
                st.plotly_chart(fig, use_container_width=True)
        with cr:
            nn2 = filtered[filtered["sentiment"].isin(["Negative","Neutral"])]
            if not nn2.empty:
                hd = nn2.groupby(["branch_name","sentiment"]).size().reset_index()
                hd.columns = ["branch_name","sentiment","count"]
                fig = px.bar(hd, x="branch_name", y="count", color="sentiment", barmode="group",
                             title="Issues by Branch",
                             color_discrete_map={"Negative":"#e74c3c","Neutral":"#f39c12"},
                             labels={"branch_name":"Branch","count":"Total Issues","sentiment":"Type"})
                fig.update_traces(hovertemplate="<b>%{x}</b><br>Total Issues: %{y}<extra></extra>")
                fig.update_layout(margin=dict(t=50,b=20), height=380, legend=dict(orientation="h",y=-0.15))
                st.plotly_chart(fig, use_container_width=True)

        # ── Resolution Time + CSAT ────────────────────────────────────────────
        cl2, cr2 = st.columns(2)
        with cl2:
            resolved = filtered[(filtered["is_complaint"]) & (filtered["is_resolved"]=="Yes")
                                & (filtered["resolved_date"].notna())].copy()
            if not resolved.empty:
                resolved["resolve_hours"] = (
                    (pd.to_datetime(resolved["resolved_date"]) - resolved["review_date"])
                    .dt.total_seconds() / 3600
                ).clip(lower=0)
                avg_time = (resolved.groupby("issue_type")["resolve_hours"]
                            .mean().sort_values(ascending=False).head(5).reset_index())
                avg_time.columns = ["issue_type", "avg_hours"]
                fig = px.bar(avg_time, x="issue_type", y="avg_hours",
                             title="Slowest Issues to Resolve (Avg Hours)",
                             color="avg_hours",
                             color_continuous_scale=["#a8d4f5","#4A90D9","#1a5276"],
                             labels={"issue_type":"Issue","avg_hours":"Avg Hours"})
                fig.update_traces(
                    hovertemplate="<b>%{x}</b><br>Avg Resolution: %{y:.1f} hrs<extra></extra>")
                fig.update_layout(height=320, margin=dict(t=50,b=20),
                                  xaxis_tickangle=-25, showlegend=False,
                                  coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No resolved complaints to analyze resolution time.")
        with cr2:
            if not filtered.empty:
                csat_series = filtered.groupby("week_start").apply(
                    lambda g: (g["rating"] >= 4).sum() / len(g) * 100 if len(g) else 0
                )
                csat_df = csat_series.reset_index()
                csat_df.columns = ["week_start", "csat"]
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=csat_df["week_start"], y=csat_df["csat"],
                    mode="lines+markers+text",
                    text=[f"{v:.0f}%" for v in csat_df["csat"]],
                    textposition="top center", textfont=dict(size=10),
                    line=dict(color="#2ecc71", width=3),
                    hovertemplate="<b>Week: %{x}</b><br>CSAT: %{y:.1f}%<extra></extra>"))
                fig.update_layout(title="CSAT (% reviews >= 4 stars)", height=320,
                                  yaxis_title="CSAT %", margin=dict(t=50,b=20))
                st.plotly_chart(fig, use_container_width=True)

        # ── Positive vs Negative vs Neutral over time ────────────────────────
        if not filtered.empty:
            wk = filtered.groupby(["week_start","sentiment"]).size().reset_index()
            wk.columns = ["week_start","sentiment","count"]
            fig = px.line(wk, x="week_start", y="count", color="sentiment", markers=True,
                          title="Positive vs Negative vs Neutral Reviews Over Time",
                          color_discrete_map={"Positive":"#2ecc71","Negative":"#e74c3c","Neutral":"#f39c12"})
            fig.update_layout(xaxis_title="Week", yaxis_title="Count", height=320,
                              margin=dict(t=50,b=20), legend=dict(orientation="h",y=-0.25))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # ── Top 5 ────────────────────────────────────────────────────────────
        cb, cg = st.columns(2)
        with cb:
            st.subheader("Top 5 Complaints")
            comps = filtered[filtered["is_complaint"]]
            if not comps.empty:
                top = (comps.groupby("issue_type")
                       .agg(count=("review_id","size"), likes=("likes","sum"), sample=("review_text","first"))
                       .sort_values("count", ascending=False).head(5).reset_index())
                for _, r in top.iterrows():
                    with st.expander(f"**{r['issue_type']}** — {r['count']} complaints | {r['likes']} likes"):
                        st.write(f"*\"{r['sample'][:250]}\"*")
                        for rv in comps[comps["issue_type"]==r["issue_type"]]["review_text"].tolist()[1:4]:
                            st.caption(f"— {rv[:150]}...")
        with cg:
            st.subheader("Top 5 Praised")
            pos = filtered[filtered["is_positive"]]
            if not pos.empty:
                top = (pos.groupby("issue_type")
                       .agg(count=("review_id","size"), likes=("likes","sum"), sample=("review_text","first"))
                       .sort_values("count", ascending=False).head(5).reset_index())
                for _, r in top.iterrows():
                    with st.expander(f"**{r['issue_type']}** — {r['count']} praises | {r['likes']} likes"):
                        st.write(f"*\"{r['sample'][:250]}\"*")
                        for rv in pos[pos["issue_type"]==r["issue_type"]]["review_text"].tolist()[1:4]:
                            st.caption(f"— {rv[:150]}...")

    # ══════════════════════════════════════════════════════════════════════════
    #  TAB 2 — SEMANTIC SEARCH
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.subheader("Search by Meaning")
        q = st.text_input("Enter a phrase", placeholder='e.g. "slow refund" or "uncomfortable mattress"')
        if q:
            model = load_model()
            from sklearn.metrics.pairwise import cosine_similarity
            sims = cosine_similarity(model.encode([q]), embeddings)[0]
            for idx in sims.argsort()[-10:][::-1]:
                r = df.iloc[idx]
                st.write(f"**[{sims[idx]*100:.0f}% | {r['rating']} stars | {'Resolved' if r['is_resolved']=='Yes' else 'Open'} | {r['likes']} likes]** {r['review_text'][:250]}")
                st.caption(f"{r['issue_type']} | {r['branch_name']} ({r['review_source']}) | {r['reviewer_name']}")

        st.markdown("---")
        st.subheader("Synonym Demo")
        ca, cb_ = st.columns(2)
        with ca: wa = st.text_input("Phrase A", value="telephone")
        with cb_: wb = st.text_input("Phrase B", value="phone")
        if wa and wb:
            model = load_model()
            from sklearn.metrics.pairwise import cosine_similarity as cs
            e = model.encode([wa, wb])
            st.metric(f"'{wa}' ↔ '{wb}'", f"{cs([e[0]],[e[1]])[0][0]*100:.1f}%")
            demos = [("telephone","phone"),("bed","cot"),("call times are too long","customer service is slow"),
                     ("smelly rooms","bad rooms"),("overpriced","too expensive"),("refund denied","won't give money back")]
            ea, eb_ = model.encode([p[0] for p in demos]), model.encode([p[1] for p in demos])
            st.dataframe(pd.DataFrame([{"Phrase A":a,"Phrase B":b,"Similarity":f"{cs([ea[i]],[eb_[i]])[0][0]*100:.0f}%"}
                                        for i,(a,b) in enumerate(demos)]),
                         use_container_width=True, hide_index=True)

        # Word Vectors illustration
        st.markdown("---")
        st.subheader("How Semantic Clustering Works")
        st.caption("Reviews with similar meaning are grouped together — even when they use completely different words.")
        if os.path.exists("word_vectors.webp"):
            st.image("word_vectors.webp", use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  TAB 3 — UNCATEGORIZABLE
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.subheader("Low-Confidence Reviews")
        uncat = filtered[filtered["is_uncategorizable"]].sort_values("confidence_distance", ascending=False)
        st.metric("Flagged", len(uncat))
        if not uncat.empty:
            itypes = sorted(df["issue_type"].dropna().unique().tolist())
            for _, row in uncat.iterrows():
                rid = row["review_id"]
                conf = max(0, (1 - row["confidence_distance"]) * 100)
                with st.expander(f"[{conf:.0f}% confidence] #{rid} — {row['reviewer_name']} — {row['rating']} stars"):
                    st.write(row["review_text"])
                    st.caption(f"{row['review_date'].strftime('%Y-%m-%d %H:%M')} | {row['likes']} likes | {row['branch_name']}")
                    if row["hotel_response"]: st.info(f"**Response:** {row['hotel_response']}")
                    c1, c2, c3 = st.columns([3, 2, 2])
                    with c1:
                        ci = itypes.index(row["issue_type"]) if row["issue_type"] in itypes else 0
                        nc = st.selectbox("Issue Type", itypes, index=ci, key=f"cat_{rid}")
                    with c2:
                        so = ["Positive","Neutral","Negative","Mixed"]
                        si = so.index(row["aspect_sentiment"]) if row["aspect_sentiment"] in so else 1
                        ns = st.selectbox("Sentiment", so, index=si, key=f"sent_{rid}")
                    with c3:
                        st.write(""); st.write("")
                        if st.button("Submit", key=f"sub_{rid}"): st.session_state[f"cfm_{rid}"] = True
                    if st.session_state.get(f"cfm_{rid}"):
                        st.warning(f"Confirm: **{nc}** / **{ns}** — remove from uncategorizable?")
                        y, n = st.columns(2)
                        with y:
                            if st.button("Confirm", key=f"y_{rid}"):
                                i = df.index[df["review_id"]==rid][0]
                                df.at[i,"issue_type"]=nc; df.at[i,"aspect_sentiment"]=ns; df.at[i,"is_uncategorizable"]=False
                                st.session_state["pipeline_df"]=df; save_enriched_db(df, ENRICHED_DB_PATH)
                                st.session_state.pop(f"cfm_{rid}",None); st.toast(f"#{rid} updated."); st.rerun()
                        with n:
                            if st.button("Cancel", key=f"n_{rid}"):
                                st.session_state.pop(f"cfm_{rid}",None); st.rerun()
        else:
            st.success("All reviews confidently categorized.")

    # ══════════════════════════════════════════════════════════════════════════
    #  TAB 4 — COMPLAINT TICKETS
    # ══════════════════════════════════════════════════════════════════════════
    with tab4:
        st.subheader("Complaint Tickets")

        # Only unresolved negative + neutral
        tickets = filtered[(filtered["sentiment"].isin(["Negative","Neutral"])) & (filtered["is_resolved"]=="No")].copy()
        tickets["hours_since"] = ((datetime.now() - tickets["review_date"]).dt.total_seconds() / 3600).round(1)

        # Sorting controls
        sc1, sc2 = st.columns(2)
        with sc1:
            sort_by = st.selectbox("Sort by", ["Time Open (longest first)","Time Open (newest first)","Likes (highest first)","Likes (lowest first)"])
        with sc2:
            ticket_branch = st.multiselect("Filter Branch", sorted(tickets["branch_name"].unique()),
                                            default=sorted(tickets["branch_name"].unique()), key="ticket_branch")

        tickets = tickets[tickets["branch_name"].isin(ticket_branch)]

        if sort_by == "Time Open (longest first)": tickets = tickets.sort_values("hours_since", ascending=False)
        elif sort_by == "Time Open (newest first)": tickets = tickets.sort_values("hours_since", ascending=True)
        elif sort_by == "Likes (highest first)": tickets = tickets.sort_values("likes", ascending=False)
        elif sort_by == "Likes (lowest first)": tickets = tickets.sort_values("likes", ascending=True)

        st.write(f"**{len(tickets)} open tickets**")

        if not tickets.empty:
            for _, row in tickets.iterrows():
                rid = row["review_id"]
                hrs = row["hours_since"]

                # Ticket card layout
                st.markdown(f"""<div class="ticket-card">
                    <div class="ticket-header">
                        <span class="ticket-id">#{rid}</span>
                        <span class="ticket-time">{fmt_hours(hrs)} open</span>
                        <span class="ticket-likes">{row['likes']} likes</span>
                        <span class="ticket-branch">{row['branch_name']} · {row['review_source']}</span>
                    </div>
                </div>""", unsafe_allow_html=True)

                with st.expander(f"**{row['issue_type']}** — {row['reviewer_name']} — {row['rating']} stars"):
                    st.write(row["review_text"])
                    st.caption(f"Posted: {row['review_date'].strftime('%Y-%m-%d %H:%M')} | "
                               f"Aspect: {row['aspect_sentiment']} | Category: {row['issue_subcategory']}")
                    if row["hotel_response"]:
                        st.info(f"**Our Response:** {row['hotel_response']}")

                    if st.button("Issue Resolved", key=f"resolve_{rid}", type="primary"):
                        i = df.index[df["review_id"]==rid][0]
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        df.at[i, "is_resolved"] = "Yes"
                        df.at[i, "resolved_date"] = now_str
                        df.at[i, "time_resolved"] = now_str
                        st.session_state["pipeline_df"] = df
                        save_enriched_db(df, ENRICHED_DB_PATH)
                        st.toast(f"Ticket #{rid} resolved.")
                        st.rerun()
        else:
            st.success("No open tickets. All complaints resolved!")

    # ══════════════════════════════════════════════════════════════════════════
    #  TAB 5 — DATA EXPORT
    # ══════════════════════════════════════════════════════════════════════════
    with tab5:
        st.subheader("Data Export")
        ecols = ["review_id","reviewer_name","review_text","rating","likes","review_date",
                 "review_source","branch_name","sentiment","aspect_sentiment",
                 "issue_category","issue_subcategory","issue_type","is_resolved",
                 "hotel_response","resolved_date","time_resolved","is_uncategorizable","confidence_distance"]
        edf = filtered[[c for c in ecols if c in filtered.columns]].sort_values("review_date", ascending=False)
        st.info("AI columns: issue_category, issue_subcategory, issue_type, aspect_sentiment, is_uncategorizable")
        st.write(f"**{len(edf)} reviews** match filters.")
        st.dataframe(edf.head(10), use_container_width=True, height=300)
        c1, c2, c3, _ = st.columns([1, 1, 1, 3])
        with c1: st.download_button("Download CSV", edf.to_csv(index=False), "enriched_reviews.csv", "text/csv")
        with c2:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w: edf.to_excel(w, index=False, sheet_name="Reviews")
            st.download_button("Export Excel", buf.getvalue(), "enriched_reviews.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with c3:
            if os.path.exists(ENRICHED_DB_PATH):
                st.download_button("SQLite DB", open(ENRICHED_DB_PATH, "rb").read(), "enriched_reviews.db")

    # ══════════════════════════════════════════════════════════════════════════
    #  TAB 6 — ADMIN
    # ══════════════════════════════════════════════════════════════════════════
    with tab6:
        if not st.session_state.admin_logged_in:
            st.subheader("Admin Login")
            with st.form("login"):
                u = st.text_input("Username"); p = st.text_input("Password", type="password")
                if st.form_submit_button("Login"):
                    if u == ADMIN_USER and hashlib.sha256(p.encode()).hexdigest() == ADMIN_PASS_HASH:
                        st.session_state.admin_logged_in = True; st.rerun()
                    else: st.error("Invalid. Default: admin / admin123")
        else:
            st.subheader("Admin Panel")
            if st.button("Logout"): st.session_state.admin_logged_in = False; st.rerun()
            st.markdown("---")

            st.subheader("Refresh Data")
            st.caption("Uses API quota. Manage carefully.")
            adf = load_admin_config()
            for _, cfg in adf[adf["is_active"]==1].iterrows():
                ld = datetime.strptime(cfg["last_refresh"], "%Y-%m-%d %H:%M:%S") if pd.notna(cfg["last_refresh"]) else None
                ci, cb_ = st.columns([4, 1])
                with ci: st.write(f"**{cfg['branch_name']}** — {cfg['review_source']} | Last: {fmt_ago(ld)}")
                with cb_:
                    if st.button("Refresh", key=f"ref_{cfg['config_id']}"):
                        update_last_refresh(cfg["branch_name"], cfg["review_source"])
                        for k in ["pipeline_df","pipeline_embeddings"]: st.session_state.pop(k, None)
                        st.cache_data.clear(); st.rerun()

            st.markdown("---")
            st.subheader("API Configurations")
            adf = load_admin_config()
            for _, cfg in adf.iterrows():
                cid = cfg["config_id"]
                with st.expander(f"**{cfg['branch_name']}** — {cfg['review_source']}"):
                    nb = st.text_input("Branch", value=cfg["branch_name"], key=f"bn_{cid}")
                    ns = st.selectbox("Source", ["Google","Yelp","TripAdvisor"],
                                      index=["Google","Yelp","TripAdvisor"].index(cfg["review_source"]) if cfg["review_source"] in ["Google","Yelp","TripAdvisor"] else 0,
                                      key=f"src_{cid}")
                    nk = st.text_input("API Key", value=cfg["api_key"] or "", type="password", key=f"key_{cid}")
                    np_ = st.text_input("Place ID", value=cfg["place_id"] or "", key=f"pid_{cid}")
                    sc_, dc_ = st.columns(2)
                    with sc_:
                        if st.button("Save", key=f"save_{cid}"):
                            update_admin_field(cid,"branch_name",nb); update_admin_field(cid,"review_source",ns)
                            update_admin_field(cid,"api_key",nk); update_admin_field(cid,"place_id",np_)
                            st.toast(f"Saved {nb}"); st.rerun()
                    with dc_:
                        if st.button("Remove", key=f"del_{cid}"):
                            delete_admin_config(cid); st.toast("Removed"); st.rerun()

            st.markdown("---")
            st.subheader("Add New")
            with st.form("add_cfg"):
                ab = st.text_input("Branch Name"); asrc = st.selectbox("Source", ["Google","Yelp","TripAdvisor"])
                ak = st.text_input("API Key", type="password"); ap = st.text_input("Place ID")
                if st.form_submit_button("Add"):
                    if ab and ak: save_admin_config_row(ab, asrc, ak, ap); st.success(f"Added {ab}"); st.rerun()
                    else: st.error("Branch and key required.")


if __name__ == "__main__":
    main()
