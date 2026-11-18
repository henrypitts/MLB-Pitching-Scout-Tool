
from pybaseball import statcast_pitcher
import plotly.graph_objects as go
import plotly.express as px
from io import StringIO
from html import escape
import streamlit as st
import pandas as pd
import requests
import numpy as np

# =====================================
# PAGE CONFIGURATION
# =====================================
st.set_page_config(
    page_title="Pitcher Scouting Report",
    page_icon="⚾",
    layout="wide"
)

CREAM = "#FAF3E7"
MAROON = "#651F32"
BURNT_ORANGE = "#BD602D"
INK = "#35262A"

st.markdown("""
<style>
  .stApp { background: #FAF3E7; color: #35262A; }
  [data-testid="stHeader"] { background: rgba(250,243,231,.92); }
  [data-testid="stSidebar"] { background: #F1E5D4; }
  h1, h2, h3, h4 { color: #651F32 !important; letter-spacing: -.025em; }
  h1 { font-weight: 800 !important; }
  [data-testid="stMetric"] { background: #FFFDF8; border: 1px solid #E4D5C4;
    border-top: 3px solid #BD602D; border-radius: 12px; padding: 14px 18px; }
  [data-testid="stMetricValue"] { color: #651F32; }
  [data-testid="stMetricLabel"] { color: #705963; }
  /* Target Streamlit's actual tab buttons (class names vary by release). */
  [data-testid="stTabs"] [role="tablist"],
  .stTabs [role="tablist"],
  [data-baseweb="tab-list"] {
    gap: 10px !important; border: 0 !important;
    border-bottom: 0 !important; box-shadow: none !important;
  }
  [data-testid="stTabs"] button[role="tab"],
  .stTabs button[role="tab"],
  button[data-baseweb="tab"] {
    background: #F2E5D5 !important;
    border: 1px solid #DCC5AF !important;
    border-radius: 999px !important;
    color: #651F32 !important;
    padding: 11px 23px !important;
    font-weight: 650 !important;
    box-shadow: none !important;
  }
  [data-testid="stTabs"] button[role="tab"][aria-selected="true"],
  .stTabs button[role="tab"][aria-selected="true"],
  button[data-baseweb="tab"][aria-selected="true"] {
    background: #651F32 !important;
    color: #FFF8ED !important;
    border-color: #651F32 !important;
  }
  [data-testid="stTabs"] [data-baseweb="tab-highlight"],
  [data-testid="stTabs"] [data-baseweb="tab-border"],
  .stTabs [data-baseweb="tab-highlight"],
  .stTabs [data-baseweb="tab-border"],
  [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {
    display: none !important; height: 0 !important; background: transparent !important;
  }
  .bio-stat { background: #FFFDF8; border: 1px solid #E4D5C4; border-radius: 12px;
    padding: 12px 17px; min-height: 80px; }
  .bio-stat-label { color: #826D68; font-size: .76rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: .08em; }
  .bio-stat-value { color: #651F32; font-size: 1.16rem; font-weight: 750;
    line-height: 1.5; font-variant-numeric: tabular-nums; }
  div.stButton > button[kind="primary"] { background: #651F32; border-color: #651F32; }
  div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
    background: #FFFDF8; border-color: #D6BCA5; }
  [data-testid="stDataFrame"] { border: 1px solid #DFCAB7; border-radius: 12px;
    overflow: hidden; background: #FFFDF8; }
  [data-testid="stDataFrame"] [role="columnheader"] {
    background: #651F32 !important; color: #FFF8ED !important; }
  [data-testid="stExpander"] { border-radius: 12px; }
  .report-kicker { color: #BD602D; text-transform: uppercase; letter-spacing: .16em;
    font-weight: 750; font-size: .79rem; margin-bottom: .2rem; }
  .report-banner { padding: 19px 24px; background: linear-gradient(115deg,#651F32,#873C3E);
    border-radius: 15px; color: #FFF4E5; margin-bottom: 22px; }
  .report-banner strong { font-size: 1.13rem; }
  .report-banner span { color: #EFC3A2; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="report-kicker">MLB / SCOUTING INTELLIGENCE</div>', unsafe_allow_html=True)
st.title("Pitcher Scouting Report")
st.markdown(
    '<div class="report-banner"><strong>2026 Pitching Evaluation</strong>'
    ' &nbsp; <span>•</span> &nbsp; Arsenal, performance & game-planning insights</div>',
    unsafe_allow_html=True,
)


def style_plotly(fig):
    """Match Plotly figures to the report's cream, maroon and orange palette."""
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#FFFDF8",
        plot_bgcolor="#FFFDF8",
        font=dict(color=INK, family="Arial, sans-serif"),
        title_font=dict(color=MAROON),
        legend=dict(bgcolor="rgba(255,253,248,0.8)"),
    )
    fig.update_xaxes(gridcolor="#E9DED2", linecolor="#CDB9AA", tickfont=dict(color=INK))
    fig.update_yaxes(gridcolor="#E9DED2", linecolor="#CDB9AA", tickfont=dict(color=INK))
    return fig


def theme_table(df):
    """Apply soft cream zebra striping and maroon text in Streamlit data grids."""
    try:
        return df.style.apply(
            lambda row: [
                f"background-color: {'#FFFDF8' if row.name % 2 == 0 else '#F4E8DA'}; "
                "color: #502C36;"
            ] * len(row),
            axis=1,
        )
    except ImportError:
        # Styling requires optional Jinja2; retain a functional grid without it.
        return df

BASE_URL = "https://statsapi.mlb.com/api/v1"
SEASON = 2026


def classify_arm_slot(angle):
    """Dashboard-defined arm-slot bands; degrees follow Statcast convention."""
    if pd.isna(angle):
        return "Unavailable"
    if angle >= 50:
        return "Over the Top"
    if angle >= 30:
        return "3/4"
    if angle >= 0:
        return "Sidearm"
    return "Submarine"


def classify_velocity(pitch_df, min_usage=0.05):
    """Use the fastest qualifying fastball type's season-average velocity."""
    required = {"pitch_type", "release_speed"}
    if pitch_df.empty or not required.issubset(pitch_df.columns):
        return None

    data = pitch_df.dropna(subset=["pitch_type"]).copy()
    if data.empty:
        return None

    data["release_speed"] = pd.to_numeric(data["release_speed"], errors="coerce")
    total = len(data)
    fastballs = data[data["pitch_type"].isin(["FF", "SI", "FC"])].copy()
    if fastballs.empty:
        return None

    summary = fastballs.groupby("pitch_type").agg(
        Count=("pitch_type", "size"),
        ValidVelocity=("release_speed", "count"),
        Velocity=("release_speed", "mean")
    )
    summary = summary[
        (summary["Count"] / total >= min_usage)
        & (summary["ValidVelocity"] > 0)
    ].dropna(subset=["Velocity"])
    if summary.empty:
        return None

    pitch = summary["Velocity"].idxmax()
    velocity = float(summary.loc[pitch, "Velocity"])
    label = (
        "Elite Velocity" if velocity >= 98 else
        "Above Average Velocity" if velocity >= 95 else
        "Average Velocity" if velocity >= 93 else
        "Below Average Velocity"
    )
    return {"label": label, "velocity": velocity, "pitch": pitch,
            "usage": float(summary.loc[pitch, "Count"] / total * 100)}


@st.cache_data(ttl=86400)
def get_contact_profile_league(season):
    """Join Baseball Savant pitcher leaderboards by MLB player ID."""
    base = "https://baseballsavant.mlb.com/leaderboard"
    headers = {"User-Agent": "Mozilla/5.0"}
    custom_response = requests.get(
        f"{base}/custom",
        params={"type": "pitcher", "year": season, "min": 0,
                "selections": "pa,k_percent,hard_hit_percent,barrel_batted_rate",
                "csv": "true"},
        headers=headers, timeout=30
    )
    custom_response.raise_for_status()
    custom = pd.read_csv(StringIO(custom_response.text))

    batted_response = requests.get(
        f"{base}/batted-ball",
        params={"type": "pitcher", "year": season, "min": 0, "csv": "true"},
        headers=headers, timeout=30
    )
    batted_response.raise_for_status()
    batted = pd.read_csv(StringIO(batted_response.text))

    custom.columns = custom.columns.str.strip().str.lstrip("\ufeff")
    batted.columns = batted.columns.str.strip().str.lstrip("\ufeff")
    needed_custom = {"player_id", "pa", "k_percent", "hard_hit_percent"}
    needed_batted = {"id", "bbe", "gb_rate", "fb_rate"}
    if not needed_custom.issubset(custom.columns) or not needed_batted.issubset(batted.columns):
        raise ValueError("Baseball Savant contact-profile leaderboard schema changed.")

    custom = custom.rename(columns={"pa": "BF", "k_percent": "K_pct",
                                    "hard_hit_percent": "HH_pct"})
    batted = batted.rename(columns={"id": "player_id", "bbe": "BBE",
                                    "gb_rate": "GB_rate", "fb_rate": "FB_rate"})
    league = custom.merge(
        batted[["player_id", "BBE", "GB_rate", "FB_rate"]],
        on="player_id", how="left"
    )
    for col in ["player_id", "BF", "BBE", "K_pct", "HH_pct", "GB_rate", "FB_rate"]:
        league[col] = pd.to_numeric(league[col], errors="coerce")
    # Savant custom percentages are 0-100; batted-ball rates are 0-1.
    league["GB_pct"] = league["GB_rate"] * 100
    league["FB_pct"] = league["FB_rate"] * 100
    return league


def classify_contact_flairs(player_id, league, min_bf=100, min_bbe=40):
    """Overlapping 2026 contact flairs using eligible-league percentiles."""
    qualified = league[(league["BF"] >= min_bf) & (league["BBE"] >= min_bbe)].copy()
    metrics = ["K_pct", "GB_pct", "FB_pct", "HH_pct"]
    qualified = qualified.dropna(subset=metrics)
    if qualified.empty:
        return None

    matched = qualified[qualified["player_id"] == int(player_id)]
    if matched.empty:
        return None
    player = matched.iloc[0]
    cutoffs = {
        "K": qualified["K_pct"].quantile(0.75),
        "GB": qualified["GB_pct"].quantile(0.75),
        "FB": qualified["FB_pct"].quantile(0.75),
        "HH": qualified["HH_pct"].quantile(0.25),
    }
    flairs = []
    if player["K_pct"] >= cutoffs["K"]:
        flairs.append("Strikeout")
    if player["GB_pct"] >= cutoffs["GB"]:
        flairs.append("Groundball")
    if player["FB_pct"] >= cutoffs["FB"]:
        flairs.append("Flyball")
    if player["HH_pct"] <= cutoffs["HH"]:
        flairs.append("Weak Contact")
    if not flairs:
        flairs = ["Balanced"]
    return {"flairs": flairs, "player": player, "cutoffs": cutoffs,
            "league_count": len(qualified)}


FASTBALL_TYPES = ("FF", "SI", "FC")

# Raw VAA percentiles by pitch type: P10, P25, P75, P90.
VAA_THRESHOLDS = {
    "FF": (-5.214, -4.965, -4.377, -4.128),
    "SI": (-6.342, -5.990, -5.463, -5.194),
    "FC": (-7.059, -6.337, -5.461, -5.147),
}


def calculate_vaa(data):
    """Calculate raw VAA in degrees from Statcast trajectory coefficients."""
    required = ["vy0", "vz0", "ay", "az"]
    if not set(required).issubset(data.columns):
        return pd.DataFrame()
    result = data.copy()
    for field in required:
        result[field] = pd.to_numeric(result[field], errors="coerce")
    result = result.dropna(subset=required)
    # Statcast kinematics are specified at y=50 ft; front of plate is 17 inches.
    distance = 50 - 17 / 12
    discriminant = result["vy0"] ** 2 - 2 * result["ay"] * distance
    result = result[discriminant > 0].copy()
    if result.empty:
        return result
    vy_final = -np.sqrt(discriminant.loc[result.index])
    safe_ay = result["ay"].replace(0, np.nan)
    travel_time = (vy_final - result["vy0"]) / safe_ay
    vz_final = result["vz0"] + result["az"] * travel_time
    result["VAA"] = np.degrees(np.arctan2(vz_final, -vy_final))
    result = result[
        result["VAA"].between(-12, 0)
        & travel_time.between(0.2, 0.7)
    ].copy()
    return result


def classify_pitching_approach(pitch_df, min_usage=0.05, min_valid=50):
    """Classify every qualifying FF/SI/FC by season-average raw VAA."""
    if pitch_df.empty or "pitch_type" not in pitch_df.columns:
        return []
    counts = pitch_df["pitch_type"].value_counts()
    total = len(pitch_df)
    fastballs = calculate_vaa(pitch_df[pitch_df["pitch_type"].isin(FASTBALL_TYPES)])
    if fastballs.empty:
        return []

    profiles = []
    for pitch in FASTBALL_TYPES:
        count = int(counts.get(pitch, 0))
        usage = count / total if total else 0
        values = fastballs.loc[fastballs["pitch_type"] == pitch, "VAA"].dropna()
        if usage < min_usage or len(values) < min_valid:
            continue
        score = float(values.mean())
        p10, p25, p75, p90 = VAA_THRESHOLDS[pitch]
        if score >= p90:
            label = "Extremely Flat"
        elif score >= p75:
            label = "Flat"
        elif score >= p25:
            label = "Average"
        elif score >= p10:
            label = "Steep"
        else:
            label = "Extremely Steep"
        profiles.append({"pitch": pitch, "label": label, "vaa": score,
                         "count": int(len(values)), "usage": 100 * usage})
    return profiles


def classify_attack_direction(movement_avg, min_usage=0.05):
    """Compare usage-weighted spread of pitch-type HB and IVB centroids."""
    required = {"HB", "IVB", "Count"}
    if movement_avg.empty or not required.issubset(movement_avg.columns):
        return None

    data = movement_avg.dropna(subset=["HB", "IVB", "Count"]).copy()
    data = data[data["Count"] > 0]
    if data.empty:
        return None

    data["Usage"] = data["Count"] / data["Count"].sum()
    data = data[data["Usage"] >= min_usage].copy()
    if len(data) < 2:
        return None

    weights = data["Count"].to_numpy(dtype=float)
    weights /= weights.sum()
    hb = data["HB"].to_numpy(dtype=float)
    ivb = data["IVB"].to_numpy(dtype=float)

    h_spread = float(np.sqrt(np.average((hb - np.average(hb, weights=weights)) ** 2, weights=weights)))
    v_spread = float(np.sqrt(np.average((ivb - np.average(ivb, weights=weights)) ** 2, weights=weights)))
    total_spread = h_spread + v_spread
    if total_spread < 1e-9:
        return None

    ratio = h_spread / total_spread
    label = "North–South" if ratio < 0.40 else "East–West" if ratio > 0.60 else "Hybrid"
    return {"label": label, "ratio": ratio, "h_spread": h_spread,
            "v_spread": v_spread, "pitch_types": len(data)}


# =====================================
# BASEBALL SAVANT DATA
# =====================================
@st.cache_data(ttl=3600)
def get_savant_leaderboard(leaderboard, season):

    url = (
        f"https://baseballsavant.mlb.com/"
        f"leaderboard/{leaderboard}"
    )

    response = requests.get(
        url,
        params={
            "type": "pitcher",
            "year": season,
            "min": 0,
            "csv": "true"
        },
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )

    response.raise_for_status()

    df = pd.read_csv(StringIO(response.text))
    df.columns = df.columns.str.strip()

    if "player_id" not in df.columns:
        raise ValueError(
            "Baseball Savant did not return player IDs."
        )

    df["player_id"] = pd.to_numeric(
        df["player_id"], errors="coerce"
    )

    return df


# =====================================
# API FUNCTION
# =====================================
@st.cache_data(ttl=3600)
def get_data(endpoint, params=None):
    response = requests.get(
        f"{BASE_URL}/{endpoint}",
        params=params,
        timeout=20
    )
    response.raise_for_status()
    return response.json()


# =====================================
# PITCH-LEVEL STATCAST DATA
# =====================================
@st.cache_data(ttl=3600)
def get_pitch_data(player_id, season):

    start_date = f"{season}-03-01"
    end_date = f"{season}-11-01"

    df = statcast_pitcher(
        start_dt=start_date,
        end_dt=end_date,
        player_id=int(player_id)
    )

    if df.empty:
        return df

    # Regular season only
    if "game_type" in df.columns:
        df = df[df["game_type"] == "R"].copy()

    # Convert relevant columns to numbers
    numeric_columns = [
        "pfx_x",
        "pfx_z",
        "release_speed",
        "release_extension",
        "arm_angle",
        "vy0", "vz0", "ay", "az", "plate_z"
    ]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

    return df


try:
    # =====================================
    # TEAM SELECTION
    # =====================================
    teams_data = get_data(
        "teams",
        {"sportId": 1, "season": SEASON}
    )

    teams = {
        team["name"]: team["id"]
        for team in teams_data["teams"]
    }

    team_col, pitcher_col = st.columns(2, gap="large")
    with team_col:
        selected_team = st.selectbox(
            "MLB Team",
            sorted(teams)
        )

    team_id = teams[selected_team]

    # =====================================
    # GET PITCHERS
    # =====================================
    roster_data = get_data(
        f"teams/{team_id}/roster",
        {
            "rosterType": "fullSeason",
            "season": SEASON
        }
    )

    pitchers = {}

    for player in roster_data.get("roster", []):
        position = player.get("position", {})

        if position.get("type") == "Pitcher" or position.get(
            "abbreviation"
        ) in ["P", "SP", "RP", "TWP"]:

            name = player["person"]["fullName"]
            pitchers[name] = player["person"]["id"]

    if not pitchers:
        st.warning("No pitchers found for this team.")
        st.stop()

    with pitcher_col:
        selected_pitcher = st.selectbox(
            "Pitcher",
            sorted(pitchers)
        )

    player_id = pitchers[selected_pitcher]

    # =====================================
    # PLAYER PROFILE
    # =====================================
    player_data = get_data(f"people/{player_id}")
    player = player_data["people"][0]

    st.header(player["fullName"])
    st.caption(f"{selected_team}  •  {SEASON} regular season")

    weight = player.get("weight")
    weight_text = f"{weight} lbs" if weight is not None else "N/A"
    bio_stats = [
        ("Throws", player.get("pitchHand", {}).get("description", "Unknown")),
        ("Age", player.get("currentAge", "N/A")),
        ("Height", player.get("height", "N/A")),
        ("Weight", weight_text),
    ]
    for column, (label, value) in zip(st.columns(4), bio_stats):
        with column:
            st.markdown(
                '<div class="bio-stat">'
                f'<div class="bio-stat-label">{escape(str(label))}</div>'
                f'<div class="bio-stat-value">{escape(str(value))}</div>'
                '</div>',
                unsafe_allow_html=True,
            )

    # This container is populated after pitch data loads, but renders here in the bio.
    flair_area = st.container()

    # =====================================
    # REPORT NAVIGATION
    overview_tab, strategy_tab = st.tabs([
        "01  ·  Player Overview",
        "02  ·  Pitch Strategy",
    ])

    with overview_tab:
        # SEASON PITCHING STATS
        # =====================================
        stats_data = get_data(
            f"people/{player_id}/stats",
            {
                "stats": "season",
                "group": "pitching",
                "season": SEASON,
                "sportIds": 1,
                "gameType": "R"
            }
        )

        splits = []

        for group in stats_data.get("stats", []):
            splits.extend(group.get("splits", []))

        if not splits:
            st.info(
                "No 2026 MLB regular-season pitching "
                "statistics available for this player."
            )
            st.stop()

        stats = splits[0]["stat"]

        # =====================================
        # CORE PERFORMANCE METRICS
        # =====================================
    
        # =====================================
        # SEASON PITCHING STATISTICS
        # =====================================
        st.subheader("2026 Pitching Statistics")

        # Season data from MLB Stats API
        pitching_stats = {
            "League": "MLB",
            "BF": stats.get("battersFaced", 0),
            "W": stats.get("wins", 0),
            "L": stats.get("losses", 0),
            "ERA": stats.get("era", "-"),
            "G": stats.get("gamesPlayed", 0),
            "GS": stats.get("gamesStarted", 0),
            "SV": stats.get("saves", 0),
            "IP": stats.get("inningsPitched", "0.0"),
            "H": stats.get("hits", 0),
            "R": stats.get("runs", 0),
            "ER": stats.get("earnedRuns", 0),
            "HR": stats.get("homeRuns", 0),
            "BB": stats.get("baseOnBalls", 0),
            "SO": stats.get("strikeOuts", 0),
            "WHIP": stats.get("whip", "-")
        }

        pitching_df = pd.DataFrame([pitching_stats])

        st.dataframe(
            theme_table(pitching_df),
            use_container_width=True,
            hide_index=True
        )


        # =====================================
        # ADVANCED PITCHING STATISTICS
        # =====================================
        st.subheader("Advanced Pitching Statistics")

        # Get Baseball Savant data
        try:
            contact_df = get_savant_leaderboard(
                "statcast", SEASON
            )

            expected_df = get_savant_leaderboard(
                "expected_statistics", SEASON
            )

        except (requests.RequestException, ValueError) as error:
            st.warning(f"Statcast data unavailable: {error}")
            contact_df = pd.DataFrame()
            expected_df = pd.DataFrame()


        # =====================================
        # FIND SELECTED PITCHER
        # =====================================
        def find_player(df, player_id):
            if df.empty:
                return {}

            match = df[df["player_id"] == player_id]

            if match.empty:
                return {}

            return match.iloc[0].to_dict()


        contact = find_player(contact_df, player_id)
        expected = find_player(expected_df, player_id)

        # Reuse these 2026 batted-ball rates later for the Contact Profile flairs.
        league_contact = None
        contact_error = None
        try:
            league_contact = get_contact_profile_league(SEASON)
            profile_match = league_contact.loc[
                league_contact["player_id"].eq(int(player_id))
            ]
            batted_profile = profile_match.iloc[0].to_dict() if not profile_match.empty else {}
        except (requests.RequestException, ValueError, pd.errors.ParserError) as error:
            batted_profile = {}
            contact_error = str(error)


        # =====================================
        # FORMATTING HELPERS
        # =====================================
        def get_number(source, key):
            value = source.get(key)

            if value is None:
                return None

            value = pd.to_numeric(value, errors="coerce")

            if pd.isna(value):
                return None

            return float(value)


        def fmt(source, key, decimals=1):
            value = get_number(source, key)
            return f"{value:.{decimals}f}" if value is not None else "—"


        def fmt_int(source, key):
            value = get_number(source, key)
            return f"{value:,.0f}" if value is not None else "—"


        def fmt_pct(source, key):
            value = get_number(source, key)
            return f"{value:.1f}%" if value is not None else "—"


        def fmt_avg(source, key):
            value = get_number(source, key)
            return f"{value:.3f}" if value is not None else "—"


        # =====================================
        # STRIKEOUT AND WALK METRICS
        # =====================================
        strikeouts = int(stats.get("strikeOuts", 0))
        walks = int(stats.get("baseOnBalls", 0))
        batters_faced = int(stats.get("battersFaced", 0))

        if batters_faced > 0:
            k_pct = strikeouts / batters_faced * 100
            bb_pct = walks / batters_faced * 100
        else:
            k_pct = 0
            bb_pct = 0

        k_bb_pct = k_pct - bb_pct

        # Retain K/9 for the existing summary, if needed
        ip_value = str(stats.get("inningsPitched", "0.0"))
        whole, _, partial = ip_value.partition(".")
        innings = int(whole) + int(partial or 0) / 3
        k9 = strikeouts / innings * 9 if innings > 0 else 0


        # =====================================
        # BUILD ADVANCED STATISTICS TABLE
        # =====================================
        pitch_count = stats.get("numberOfPitches")
        pitch_count = (
            f"{int(pitch_count):,}"
            if pitch_count is not None
            else "—"
        )

        advanced_stats = {
            "Pitches": pitch_count,
            "Batted Balls": fmt_int(contact, "attempts"),
            "Barrel%": fmt_pct(contact, "brl_percent"),
            "Barrel/PA": fmt_pct(contact, "brl_pa"),
            "Exit Velocity": fmt(contact, "avg_hit_speed"),
            "Max EV": fmt(contact, "max_hit_speed"),
            "Launch Angle": fmt(contact, "avg_hit_angle"),
            "LA Sweet Spot%": fmt_pct(
                contact, "anglesweetspotpercent"
            ),
            "xBA": fmt_avg(expected, "est_ba"),
            "xSLG": fmt_avg(expected, "est_slg"),
            "wOBA": fmt_avg(expected, "woba"),
            "xwOBA": fmt_avg(expected, "est_woba"),
            "HardHit%": fmt_pct(contact, "ev95percent"),
            "Groundball%": fmt_pct(batted_profile, "GB_pct"),
            "Flyball%": fmt_pct(batted_profile, "FB_pct"),
            "K%": f"{k_pct:.1f}%" if batters_faced else "—",
            "BB%": f"{bb_pct:.1f}%" if batters_faced else "—",
            "xERA": fmt(expected, "xera", 2)
        }

        advanced_df = pd.DataFrame([advanced_stats])

        st.dataframe(
            theme_table(advanced_df),
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            "Source: MLB Stats API and Baseball Savant. "
            "Contact metrics represent outcomes allowed. "
            "— indicates unavailable data."
        )


        # =====================================
    with overview_tab:
        # PITCH CHARACTERISTICS & ARSENAL
        # =====================================
        st.subheader("Pitch Characteristics & Arsenal")

        pitch_colors = {
            "FF": "#8B263E",  # Four-Seam: maroon
            "SI": "#C36A34",  # Sinker: burnt orange
            "FC": "#A14E59",  # Cutter: dusty red
            "SL": "#D49A3B",  # Slider: ochre
            "ST": "#767B4E",  # Sweeper: olive
            "CU": "#57758B",  # Curveball: slate blue
            "KC": "#806B93",  # Knuckle Curve: muted violet
            "CH": "#4F8B7A",  # Changeup: sage
            "FS": "#A66C52",  # Splitter: clay
            "SV": "#9D7891"   # Slurve: mauve
        }

        try:
            pitch_df = get_pitch_data(player_id, SEASON)

        except Exception as error:
            st.warning(f"Pitch data unavailable: {error}")
            pitch_df = pd.DataFrame()


        if pitch_df.empty:
            st.info("No regular-season Statcast data available.")
            with flair_area:
                st.caption("Player flairs are unavailable without pitch-level data.")

        else:
            # ---------------------------------
            # CLEAN PITCH DATA
            # ---------------------------------
            pitch_df = pitch_df.copy()

            pitch_df = pitch_df.dropna(
                subset=["pitch_type"]
            )

            # Keep pitch types with at least 1 pitch
            pitch_counts = (
                pitch_df["pitch_type"]
                .value_counts()
            )

            total_pitches = pitch_counts.sum()

            arsenal = pd.DataFrame({
                "Pitch": pitch_counts.index,
                "Count": pitch_counts.values
            })

            arsenal["Usage%"] = (
                arsenal["Count"] / total_pitches * 100
            )

            arsenal["Color"] = arsenal["Pitch"].map(
                pitch_colors
            ).fillna("#8D99AE")

            # ---------------------------------
            # LAYOUT: MOVEMENT AND USAGE
            # ---------------------------------
            col1, col2 = st.columns(2)

            # =================================
            # HORIZONTAL VS VERTICAL BREAK
            # =================================
            with col1:

                st.markdown("#### Pitch Movement")

                movement_df = pitch_df.dropna(
                    subset=["pfx_x", "pfx_z"]
                ).copy()

                # Statcast movement is reported
                # in feet. Convert to inches.
                movement_df["HB"] = (
                    movement_df["pfx_x"] * 12
                )

                movement_df["IVB"] = (
                    movement_df["pfx_z"] * 12
                )

                # Average movement per pitch type
                movement_avg = (
                    movement_df
                    .groupby("pitch_type")
                    .agg(
                        HB=("HB", "mean"),
                        IVB=("IVB", "mean"),
                        Count=("HB", "size")
                    )
                    .reset_index()
                )

                fig = go.Figure()

                for pitch in movement_avg["pitch_type"]:

                    pitch_data = movement_df[
                        movement_df["pitch_type"] == pitch
                    ]

                    avg = movement_avg[
                        movement_avg["pitch_type"] == pitch
                    ].iloc[0]

                    color = pitch_colors.get(
                        pitch, "#8D99AE"
                    )

                    # Individual pitches
                    fig.add_trace(go.Scatter(
                        x=pitch_data["HB"],
                        y=pitch_data["IVB"],
                        mode="markers",
                        marker=dict(
                            color=color,
                            size=5,
                            opacity=0.22
                        ),
                        name=pitch,
                        legendgroup=pitch,
                        hovertemplate=(
                            f"{pitch}<br>"
                            "HB: %{x:.1f} in<br>"
                            "IVB: %{y:.1f} in"
                            "<extra></extra>"
                        )
                    ))

                    # Pitch type average
                    fig.add_trace(go.Scatter(
                        x=[avg["HB"]],
                        y=[avg["IVB"]],
                        mode="markers+text",
                        text=[pitch],
                        textposition="top center",
                        marker=dict(
                            color=color,
                            size=15,
                            line=dict(
                                color="white",
                                width=2
                            )
                        ),
                        showlegend=False,
                        legendgroup=pitch,
                        hovertemplate=(
                            f"{pitch} Average<br>"
                            "HB: %{x:.1f} in<br>"
                            "IVB: %{y:.1f} in"
                            "<extra></extra>"
                        )
                    ))

                fig.add_hline(
                    y=0,
                    line_dash="dash",
                    line_color="gray"
                )

                fig.add_vline(
                    x=0,
                    line_dash="dash",
                    line_color="gray"
                )

                fig.update_layout(
                    xaxis_title="Horizontal Break (in)",
                    yaxis_title="Induced Vertical Break (in)",
                    height=450,
                    template="plotly_white",
                    legend_title="Pitch Type",
                    margin=dict(
                        l=10, r=10, t=20, b=10
                    )
                )

                fig.update_xaxes(
                    zeroline=False
                )

                fig.update_yaxes(
                    zeroline=False,
                    scaleanchor="x",
                    scaleratio=1
                )

                st.plotly_chart(
                    style_plotly(fig),
                    use_container_width=True
                )

                attack = classify_attack_direction(movement_avg)

            # =================================
            # PITCH ARSENAL USAGE
            # =================================
            with col2:

                st.markdown("#### Pitch Arsenal Usage")

                fig_usage = go.Figure()

                fig_usage.add_trace(go.Bar(
                    x=arsenal["Usage%"],
                    y=arsenal["Pitch"],
                    orientation="h",
                    marker_color=arsenal["Color"],
                    text=[
                        f"{value:.1f}%"
                        for value in arsenal["Usage%"]
                    ],
                    textposition="outside",
                    customdata=arsenal["Count"],
                    hovertemplate=(
                        "%{y}<br>"
                        "Usage: %{x:.1f}%<br>"
                        "Pitches: %{customdata}"
                        "<extra></extra>"
                    )
                ))

                fig_usage.update_layout(
                    xaxis_title="Usage (%)",
                    yaxis_title="",
                    height=450,
                    template="plotly_white",
                    margin=dict(
                        l=10, r=30, t=20, b=10
                    ),
                    xaxis=dict(
                        range=[
                            0,
                            max(100, arsenal["Usage%"].max() + 10)
                        ]
                    ),
                    yaxis=dict(
                        autorange="reversed"
                    )
                )

                st.plotly_chart(
                    style_plotly(fig_usage),
                    use_container_width=True
                )

            # =================================
            # ARM ANGLE & EXTENSION
            # =================================
            st.markdown("#### Release Characteristics")

            arm_angle = pitch_df["arm_angle"].mean()
            extension = pitch_df["release_extension"].mean()

            m1, m2, m3 = st.columns(3)

            with m1:
                st.metric(
                    "Average Arm Angle",
                    f"{arm_angle:.1f}°"
                    if pd.notna(arm_angle) else "N/A",
                    help=f"Arm slot: {classify_arm_slot(arm_angle)}"
                )

            with m2:
                st.metric(
                    "Average Extension",
                    f"{extension:.2f} ft"
                    if pd.notna(extension) else "N/A"
                )

            with m3:
                st.metric(
                    "Total Pitches",
                    f"{total_pitches:,}"
                )

            # =================================
            # PLAYER FLAIRS — ALL CLASSIFICATIONS
            # =================================
            velocity_profile = classify_velocity(pitch_df)
            approaches = classify_pitching_approach(pitch_df)
            contact_profile = (
                classify_contact_flairs(player_id, league_contact)
                if league_contact is not None else None
            )

            with flair_area:


                flair_groups = [
                    ("Arm Slot", [classify_arm_slot(arm_angle)]),
                    ("Attack Direction", [attack["label"]] if attack else []),
                    ("Velocity", [velocity_profile["label"]] if velocity_profile else []),
                    ("Contact Profile", contact_profile["flairs"] if contact_profile else []),
                    ("Pitching Approach", [
                        f'{item["pitch"]} — {item["label"]}' for item in approaches
                    ]),
                ]
                flair_palette = {
                    "Arm Slot": "#651F32",
                    "Attack Direction": "#A54B35",
                    "Velocity": "#BD602D",
                    "Contact Profile": "#766045",
                    "Pitching Approach": "#89445B",
                }

                all_flair_badges = []
                for group_name, group_tags in flair_groups:
                    if group_name == "Arm Slot":
                        group_tags = [tag for tag in group_tags if tag != "Unavailable"]
                    if not group_tags:
                        continue
                    color = flair_palette[group_name]
                    tags_html = [
                        f'<span style="background:{color};color:#fff;'
                        f'padding:6px 12px;border-radius:16px;'
                        f'margin-right:7px;display:inline-block;font-weight:600;'
                        f'white-space:nowrap">{tag}</span>'
                        for tag in group_tags
                    ]
                    all_flair_badges.extend(tags_html)

                if all_flair_badges:
                    st.markdown(
                        '<div style="display:flex;align-items:center;overflow-x:auto;'
                        'padding:5px 0 10px 0">' + "".join(all_flair_badges) + '</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.caption("No classification flairs available for this pitcher.")

                with st.expander("View classification measurements and rules"):
                    if pd.notna(arm_angle):
                        st.write(f"**Arm Slot:** {arm_angle:.1f}° average arm angle")
                    if attack:
                        st.write(
                            f"**Attack Direction:** horizontal ratio {attack['ratio']:.3f}; "
                            f"HB spread {attack['h_spread']:.1f} in; "
                            f"IVB spread {attack['v_spread']:.1f} in "
                            "(provisional 0.40/0.60 thresholds)"
                        )
                    if velocity_profile:
                        st.write(
                            f"**Velocity:** {velocity_profile['pitch']} average "
                            f"{velocity_profile['velocity']:.1f} mph "
                            f"({velocity_profile['usage']:.1f}% usage)"
                        )
                    if contact_profile:
                        cp = contact_profile["player"]
                        st.write(
                            f"**Contact:** K% {cp['K_pct']:.1f}, "
                            f"GB% {cp['GB_pct']:.1f}, FB% {cp['FB_pct']:.1f}, "
                            f"Hard-Hit% allowed {cp['HH_pct']:.1f}. "
                            "Flairs use 2026 eligible-pitcher percentile thresholds."
                        )
                    elif contact_error:
                        st.caption(f"Contact data unavailable: {contact_error}")
                    if approaches:
                        st.dataframe(
                            theme_table(pd.DataFrame([{
                                "Pitch": item["pitch"], "Approach": item["label"],
                                "Raw VAA": item["vaa"], "Usage%": item["usage"],
                                "Valid Pitches": item["count"]
                            } for item in approaches])),
                            hide_index=True, use_container_width=True,
                            column_config={
                                "Raw VAA": st.column_config.NumberColumn(format="%.3f°"),
                                "Usage%": st.column_config.NumberColumn(format="%.1f%%"),
                            }
                        )
                    st.caption("Approach tags use pitch-specific raw VAA thresholds, "
                               "with at least 5% usage and 50 valid measurements per pitch.")

            # =================================
            # ARSENAL SUMMARY TABLE
            # =================================
            st.markdown("#### Arsenal Breakdown")

            arsenal_summary = (
                pitch_df
                .groupby("pitch_type")
                .agg(
                    Pitches=("pitch_type", "size"),
                    Velocity=("release_speed", "mean"),
                    Extension=("release_extension", "mean"),
                    Arm_Angle=("arm_angle", "mean"),
                    HB=("pfx_x", "mean"),
                    IVB=("pfx_z", "mean")
                )
                .reset_index()
            )

            arsenal_summary["Usage%"] = (
                arsenal_summary["Pitches"] /
                total_pitches * 100
            )

            arsenal_summary["HB"] *= 12
            arsenal_summary["IVB"] *= 12

            # Raw VAA for every pitch type with valid Statcast trajectory data.
            # Flair thresholds still apply to qualifying FF/SI/FC only.
            vaa_pitches = calculate_vaa(pitch_df)
            if not vaa_pitches.empty:
                vaa_means = vaa_pitches.groupby("pitch_type")["VAA"].mean()
                arsenal_summary["VAA"] = arsenal_summary["pitch_type"].map(vaa_means)
            else:
                arsenal_summary["VAA"] = np.nan

            arsenal_summary = arsenal_summary.rename(
                columns={
                    "pitch_type": "Pitch",
                    "Arm_Angle": "Arm Angle"
                }
            )

            arsenal_summary = arsenal_summary[
                [
                    "Pitch",
                    "Pitches",
                    "Usage%",
                    "Velocity",
                    "HB",
                    "IVB",
                    "VAA",
                    "Arm Angle",
                    "Extension"
                ]
            ]

            arsenal_summary = arsenal_summary.sort_values(
                "Pitches",
                ascending=False
            )

            st.dataframe(
                theme_table(arsenal_summary),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Usage%": st.column_config.NumberColumn(
                        format="%.1f%%"
                    ),
                    "Velocity": st.column_config.NumberColumn(
                        format="%.1f mph"
                    ),
                    "HB": st.column_config.NumberColumn(
                        format="%.1f in"
                    ),
                    "IVB": st.column_config.NumberColumn(
                        format="%.1f in"
                    ),
                    "VAA": st.column_config.NumberColumn(
                        "Raw VAA", format="%.2f°",
                        help="Average raw vertical approach angle at the front of home plate."
                    ),
                    "Arm Angle": st.column_config.NumberColumn(
                        format="%.1f°"
                    ),
                    "Extension": st.column_config.NumberColumn(
                        format="%.2f ft"
                    )
                }
            )

        # =====================================
    with strategy_tab:
        # PITCH TYPE FREQUENCY BY COUNT
        # =====================================
        st.subheader("Pitch Selection by Count")

        if pitch_df.empty:
            st.info("No pitch data available for count analysis.")

        else:
            count_df = pitch_df.copy()

            # ---------------------------------
            # BATTER HANDEDNESS FILTER
            # ---------------------------------
            hand_selection = st.selectbox(
                "Batter Handedness",
                ["All", "RHH", "LHH"],
                key="pitch_count_hand"
            )

            if hand_selection == "RHH":
                count_df = count_df[
                    count_df["stand"] == "R"
                ].copy()

            elif hand_selection == "LHH":
                count_df = count_df[
                    count_df["stand"] == "L"
                ].copy()

            # ---------------------------------
            # CLEAN COUNT DATA
            # ---------------------------------
            count_df["balls"] = pd.to_numeric(
                count_df["balls"], errors="coerce"
            )

            count_df["strikes"] = pd.to_numeric(
                count_df["strikes"], errors="coerce"
            )

            count_df = count_df.dropna(
                subset=["balls", "strikes", "pitch_type"]
            )

            count_df = count_df[
                count_df["balls"].isin([0, 1, 2, 3]) &
                count_df["strikes"].isin([0, 1, 2])
            ].copy()

            # Create count labels
            count_df["Count"] = (
                count_df["balls"].astype(int).astype(str)
                + "-"
                + count_df["strikes"].astype(int).astype(str)
            )

            # Count order
            count_order = [
                "0-0", "0-1", "0-2",
                "1-0", "1-1", "1-2",
                "2-0", "2-1", "2-2",
                "3-0", "3-1", "3-2"
            ]

            if count_df.empty:
                st.info("No pitches available for this selection.")

            else:
                # ---------------------------------
                # PITCH FREQUENCY
                # ---------------------------------
                frequency = pd.crosstab(
                    count_df["Count"],
                    count_df["pitch_type"]
                )

                # Order pitch types by overall usage
                pitch_order = (
                    count_df["pitch_type"]
                    .value_counts()
                    .index
                    .tolist()
                )

                frequency = frequency.reindex(
                    index=count_order,
                    columns=pitch_order,
                    fill_value=0
                )

                # Sample sizes by count
                count_totals = frequency.sum(axis=1)

                # Each count sums to 100%
                frequency_pct = frequency.div(
                    count_totals.replace(0, np.nan),
                    axis=0
                ) * 100

                frequency_pct = frequency_pct.fillna(0)

                # ---------------------------------
                # VISUALIZATION SELECTION
                # ---------------------------------
                chart_type = st.radio(
                    "Visualization",
                    ["Stacked Bar Chart", "Heatmap"],
                    horizontal=True,
                    key="count_chart_type"
                )

                if chart_type == "Stacked Bar Chart":

                    fig_count = go.Figure()

                    for pitch in pitch_order:

                        fig_count.add_trace(go.Bar(
                            x=frequency_pct[pitch],
                            y=count_order,
                            name=pitch,
                            orientation="h",
                            marker_color=pitch_colors.get(
                                pitch, "#8D99AE"
                            ),
                            text=[
                                f"{v:.1f}%" if v >= 6 else ""
                                for v in frequency_pct[pitch]
                            ],
                            textposition="inside",
                            customdata=frequency[pitch],
                            hovertemplate=(
                                "Count: %{y}<br>"
                                f"Pitch: {pitch}<br>"
                                "Usage: %{x:.1f}%<br>"
                                "Pitches: %{customdata}"
                                "<extra></extra>"
                            )
                        ))

                    fig_count.update_layout(
                        barmode="stack",
                        title="Pitch Type Frequency by Count",
                        xaxis_title="Pitch Usage (%)",
                        yaxis_title="Count",
                        xaxis=dict(range=[0, 100]),
                        yaxis=dict(
                            categoryorder="array",
                            categoryarray=count_order[::-1]
                        ),
                        template="plotly_white",
                        height=600,
                        legend_title="Pitch Type",
                        margin=dict(
                            l=20, r=20, t=60, b=20
                        )
                    )

                else:
                    # ---------------------------------
                    # HEATMAP
                    # ---------------------------------
                    fig_count = go.Figure()

                    fig_count.add_trace(go.Heatmap(
                        z=frequency_pct.values,
                        x=frequency_pct.columns,
                        y=frequency_pct.index,
                        colorscale=[[0, "#FFF4E3"], [0.5, "#DFA16C"], [1, "#651F32"]],
                        zmin=0,
                        zmax=100,
                        text=frequency_pct.values,
                        texttemplate="%{text:.1f}%",
                        hovertemplate=(
                            "Count: %{y}<br>"
                            "Pitch: %{x}<br>"
                            "Usage: %{z:.1f}%"
                            "<extra></extra>"
                        ),
                        colorbar=dict(title="Usage %")
                    ))

                    fig_count.update_layout(
                        title="Pitch Type Frequency Heatmap",
                        xaxis_title="Pitch Type",
                        yaxis_title="Count",
                        template="plotly_white",
                        height=600,
                        yaxis=dict(
                            categoryorder="array",
                            categoryarray=count_order[::-1]
                        ),
                        margin=dict(
                            l=20, r=20, t=60, b=20
                        )
                    )

                st.plotly_chart(
                    style_plotly(fig_count),
                    use_container_width=True
                )

                # ---------------------------------
                # SAMPLE SIZES
                # ---------------------------------
                st.markdown("#### Count Sample Sizes")

                sample_df = pd.DataFrame({
                    "Count": count_order,
                    "Pitches": count_totals.values
                })

                st.dataframe(
                    theme_table(sample_df),
                    hide_index=True,
                    use_container_width=True
                )

                st.caption(
                    "Pitch usage is calculated independently "
                    "for each count. Each count with recorded "
                    "pitches totals 100%. Counts with no pitches "
                    "display 0%. Percentages represent pitch "
                    "selection before the pitch is thrown."
                )

        # =====================================
    with strategy_tab:
        # PLATE ANALYSIS: SIDE-BY-SIDE HOT ZONES AND PITCH LOCATIONS
        st.subheader("Plate")
        plate_left, plate_right = st.columns(2, gap="large")

        with plate_left:
            st.markdown("#### Attack Zones")

            if pitch_df.empty:
                st.info("No pitch-level data available for hot zone analysis.")
            else:
                zone_df = pitch_df.copy()
                needed = ["zone", "stand", "description", "events", "type"]
                missing = [c for c in needed if c not in zone_df.columns]
                if missing:
                    st.warning(f"Hot zone requires missing Statcast columns: {', '.join(missing)}")
                else:
                    for c in ["zone", "plate_x", "plate_z", "sz_top", "sz_bot",
                              "launch_speed", "launch_angle", "launch_speed_angle",
                              "estimated_woba_using_speedangle",
                              "woba_denom", "woba_value"]:
                        if c in zone_df:
                            zone_df[c] = pd.to_numeric(zone_df[c], errors="coerce")

                    c1, c2 = st.columns(2)
                    with c1:
                        handedness_filter = st.selectbox(
                            "Batter Handedness", ["All", "RHH", "LHH"], key="hotzone_hand"
                        )
                    with c2:
                        zone_category = st.selectbox(
                            "Category", ["Traditional", "Strikes", "Hit Quality"],
                            key="hotzone_category"
                        )

                    if handedness_filter != "All":
                        side = "R" if handedness_filter == "RHH" else "L"
                        zone_df = zone_df.loc[zone_df["stand"] == side].copy()

                    if zone_df.empty:
                        st.info("No pitches available for this handedness split.")
                    else:
                        desc = zone_df["description"].fillna("")
                        ev = zone_df["events"].fillna("")
                        swing_desc = {
                            "swinging_strike", "swinging_strike_blocked", "foul", "foul_tip",
                            "foul_bunt", "hit_into_play", "hit_into_play_no_out",
                            "hit_into_play_score", "missed_bunt", "swinging_pitchout",
                            "foul_pitchout", "bunt_foul_tip"
                        }
                        whiff_desc = {"swinging_strike", "swinging_strike_blocked", "missed_bunt", "swinging_pitchout"}
                        # Ordinary ball calls only; intentional balls/pitchouts are distinct.
                        ball_desc = {"ball", "blocked_ball"}
                        # Foul tips and bunt foul tips are separate Statcast outcomes.
                        foul_desc = {"foul", "foul_bunt", "foul_pitchout"}
                        hit_events = {"single", "double", "triple", "home_run"}
                        excluded_ab = {
                            "walk", "intent_walk", "hit_by_pitch", "sac_bunt", "sac_fly",
                            "catcher_interf", "sac_fly_double_play"
                        }
                        zone_df["is_pa_end"] = zone_df["events"].notna()
                        zone_df["is_strikeout"] = ev.isin({"strikeout", "strikeout_double_play"})
                        zone_df["is_ab"] = zone_df["is_pa_end"] & ~ev.isin(excluded_ab)
                        zone_df["is_hit"] = ev.isin(hit_events)
                        zone_df["is_bb"] = ev.isin({"walk", "intent_walk"})
                        zone_df["is_hbp"] = ev.eq("hit_by_pitch")
                        zone_df["is_sf"] = ev.isin({"sac_fly", "sac_fly_double_play"})
                        zone_df["tb"] = ev.map({"single": 1, "double": 2, "triple": 3, "home_run": 4}).fillna(0)
                        zone_df["is_swing"] = desc.isin(swing_desc)
                        zone_df["is_whiff"] = desc.isin(whiff_desc)
                        zone_df["is_called_strike"] = desc.eq("called_strike")
                        zone_df["is_foul"] = desc.isin(foul_desc)
                        zone_df["is_foul_tip"] = desc.isin({"foul_tip", "bunt_foul_tip"})
                        zone_df["is_ball_call"] = desc.isin(ball_desc)
                        zone_df["is_bbe"] = zone_df["type"].eq("X")
                        zone_df["is_hard_hit"] = zone_df.get("launch_speed", pd.Series(np.nan, index=zone_df.index)).ge(95)
                        zone_df["is_sweet_spot"] = zone_df.get("launch_angle", pd.Series(np.nan, index=zone_df.index)).between(8, 32)
                        zone_df["is_barrel"] = zone_df.get("launch_speed_angle", pd.Series(np.nan, index=zone_df.index)).eq(6)

                        def rate(numerator, denominator, percent=False):
                            if denominator <= 0:
                                return np.nan
                            return numerator / denominator * (100 if percent else 1)

                        def fmt(label, value, digits=3, suffix=""):
                            return f"{label} {value:.{digits}f}{suffix}" if pd.notna(value) else f"{label} —"

                        def traditional(d):
                            pa = d.loc[d["is_pa_end"]]
                            ab = int(pa["is_ab"].sum())
                            h = int(pa["is_hit"].sum())
                            bb = int(pa["is_bb"].sum())
                            hbp = int(pa["is_hbp"].sum())
                            sf = int(pa["is_sf"].sum())
                            if {"woba_value", "woba_denom"}.issubset(pa.columns):
                                eligible_pa = pa[pa["woba_denom"] > 0].copy()
                                # Events that should receive no wOBA credit
                                zero_woba_events = {
                                    "field_error",
                                    "fielders_choice",
                                    "fielders_choice_out",
                                    "force_out",
                                    "field_out",
                                    "grounded_into_double_play",
                                    "strikeout",
                                    "strikeout_double_play",
                                    "double_play",
                                    "triple_play"
                                }

                                eligible_pa.loc[
                                    eligible_pa["events"].isin(zero_woba_events),
                                    "woba_value"
                                ] = 0.0

                                woba = rate(
                                    eligible_pa["woba_value"].sum(),
                                    eligible_pa["woba_denom"].sum()
                                )
                            else:
                                woba = np.nan
                            return [
                                fmt("BA", rate(h, ab)),
                                fmt("OBP", rate(h + bb + hbp, ab + bb + hbp + sf)),
                                fmt("SLG", rate(pa["tb"].sum(), ab)),
                                fmt("wOBA", woba)
                            ]

                        def strikes(d):
                            pa = d.loc[d["is_pa_end"]]
                            return [
                                f"CS {int(d['is_called_strike'].sum())}",
                                f"Whiff {int(d['is_whiff'].sum())}",
                                f"Foul {int(d['is_foul'].sum())}",
                                fmt("K%", rate(pa["is_strikeout"].sum(), len(pa), True), 1, "%")
                            ]

                        def quality(d):
                            b = d.loc[d["is_bbe"]]
                            tracked_ev = b.loc[b["launch_speed"].notna()] if "launch_speed" in b else b.iloc[:0]
                            tracked_la = b.loc[b["launch_angle"].notna()] if "launch_angle" in b else b.iloc[:0]
                            tracked_barrel = b.loc[b["launch_speed_angle"].notna()] if "launch_speed_angle" in b else b.iloc[:0]
                            return [
                                fmt("EV", tracked_ev["launch_speed"].mean() if len(tracked_ev) else np.nan, 1),
                                fmt("Sweet", rate(tracked_la["is_sweet_spot"].sum(), len(tracked_la), True), 1, "%"),
                                fmt("HH", rate(tracked_ev["is_hard_hit"].sum(), len(tracked_ev), True), 1, "%"),
                                fmt("Barrel", rate(tracked_barrel["is_barrel"].sum(), len(tracked_barrel), True), 1, "%")
                            ]

                        def zone_text(d):
                            fn = {"Traditional": traditional, "Strikes": strikes, "Hit Quality": quality}[zone_category]
                            return "<br>".join(fn(d))

                        # Use Statcast's actual 1–9 zone ID rather than approximating
                        # classification with fixed plate_x/plate_z boundaries.
                        zone_map = {i: zone_df.loc[zone_df["zone"].eq(i)] for i in range(1, 10)}

                        # Directional chase regions are CUSTOM, not Savant zones 11–14.
                        # Normalize each pitch's vertical location using its sz_top/sz_bot.
                        # Partition all outside pitches into exactly one direction.
                        x = zone_df.get("plate_x", pd.Series(np.nan, index=zone_df.index))
                        z = zone_df.get("plate_z", pd.Series(np.nan, index=zone_df.index))
                        top = zone_df.get("sz_top", pd.Series(np.nan, index=zone_df.index))
                        bot = zone_df.get("sz_bot", pd.Series(np.nan, index=zone_df.index))
                        valid = x.notna() & z.notna() & top.notna() & bot.notna() & top.gt(bot)
                        # ±0.83 ft is a display/geometry approximation, not Savant's zone IDs.
                        outside = valid & ((x.abs() > 0.83) | (z > top) | (z < bot))
                        above = outside & (z > top)
                        down = outside & ~above & (z < bot)
                        side = outside & ~above & ~down
                        inside = ((zone_df["stand"] == "R") & (x < -0.83)) | ((zone_df["stand"] == "L") & (x > 0.83))
                        chase = {
                            "Above": zone_df.loc[above],
                            "Down": zone_df.loc[down],
                            "In": zone_df.loc[side & inside],
                            "Away": zone_df.loc[side & ~inside],
                        }

                        def chase_text(label):
                            d = chase[label]
                            v = rate(d["is_swing"].sum(), len(d), True)
                            return f"{label}<br>{fmt('Chase', v, 1, '%')}<br>N={len(d)}"

                        # Schematic drawing; underlying zone memberships come from Statcast IDs.
                        x_left, x_right, z_bottom, z_top = -0.83, 0.83, 1.50, 3.50
                        xb = np.linspace(x_left, x_right, 4)
                        zb = np.linspace(z_bottom, z_top, 4)
                        fig_zone = go.Figure()
                        for r in range(3):
                            for c in range(3):
                                zid = 1 + r * 3 + c
                                x0, x1 = xb[c], xb[c + 1]
                                y0, y1 = zb[2 - r], zb[3 - r]
                                fig_zone.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                                                   line=dict(color="#8B4B4D", width=2),
                                                   fillcolor="rgba(101,31,50,0.09)")
                                fig_zone.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2,
                                                        text=zone_text(zone_map[zid]), showarrow=False,
                                                        font=dict(size=10, color="#35262A"), align="center")

                        outer_boxes = {
                            "Above": (x_left, x_right, z_top + .15, z_top + .70),
                            "Down": (x_left, x_right, z_bottom - .70, z_bottom - .15),
                            "In": (x_left - .75, x_left - .15, z_bottom, z_top),
                            "Away": (x_right + .15, x_right + .75, z_bottom, z_top),
                        }
                        for label, (x0, x1, y0, y1) in outer_boxes.items():
                            fig_zone.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                                               line=dict(color="#BD602D", width=2),
                                               fillcolor="rgba(189,96,45,0.12)")
                            fig_zone.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2,
                                                    text=chase_text(label), showarrow=False,
                                                    font=dict(size=11, color="#35262A"), align="center")

                        fig_zone.update_layout(
                            title=f"{zone_category} by Plate Location",
                            template="plotly_white", height=700,
                            margin=dict(l=20, r=20, t=50, b=20),
                            xaxis=dict(range=[x_left-1, x_right+1], showgrid=False,
                                       zeroline=False, showticklabels=False),
                            yaxis=dict(range=[z_bottom-1, z_top+1], showgrid=False,
                                       zeroline=False, showticklabels=False,
                                       scaleanchor="x", scaleratio=1),
                        )
                        st.plotly_chart(style_plotly(fig_zone), use_container_width=True)
                        st.caption(
                            "Inside: Statcast zone IDs 1–9. Outside: custom directional chase "
                            "regions using sz_top/sz_bot; these do not directly match Savant "
                            "zones 11–14. Strikes shows counts of called strikes, whiffs, "
                            "and ordinary fouls (excluding foul tips), plus K% based on "
                            "plate appearances ending in each zone. "
                            "Traditional stats use the location of the plate appearance's final pitch. "
                            "wOBA uses Statcast woba_value / woba_denom on those PA-ending pitches."
                        )

                        with st.expander("Zone validation / sample sizes"):
                            summary = []
                            for zid in range(1, 10):
                                d = zone_map[zid]
                                summary.append({"Statcast zone": zid, "Pitches": len(d),
                                                "PA endings": int(d["is_pa_end"].sum()),
                                                "Swings": int(d["is_swing"].sum()),
                                                "Called strikes": int(d["is_called_strike"].sum()),
                                                "Whiffs": int(d["is_whiff"].sum()),
                                                "Fouls": int(d["is_foul"].sum()),
                                                "Foul tips (separate)": int(d["is_foul_tip"].sum()),
                                                "Strikeouts": int(d["is_strikeout"].sum()),
                                                "Balls": int(d["is_ball_call"].sum())})
                            st.dataframe(theme_table(pd.DataFrame(summary)), hide_index=True)
                            st.write("Unclassified / non-1–9 pitches:",
                                     int((~zone_df["zone"].isin(range(1, 10))).sum()))



        with plate_right:
            st.markdown("#### Pitch Locations")

            if pitch_df.empty or not {"pitch_type", "plate_x", "plate_z"}.issubset(pitch_df.columns):
                st.info("No plate-location data available for this pitcher.")
            else:
                location_data = pitch_df.copy()
                for field in ("plate_x", "plate_z", "sz_top", "sz_bot"):
                    if field in location_data.columns:
                        location_data[field] = pd.to_numeric(location_data[field], errors="coerce")
                location_data = location_data.dropna(subset=["pitch_type", "plate_x", "plate_z"])

                if location_data.empty:
                    st.info("No pitches with valid plate coordinates were recorded.")
                else:
                    location_types = location_data["pitch_type"].value_counts().index.tolist()
                    selected_location_pitch = st.selectbox(
                        "Pitch Type", location_types, key="plate_location_pitch"
                    )
                    location_hand = st.selectbox(
                        "Batter Handedness", ["All", "RHH", "LHH"], key="plate_location_hand"
                    )
                    location_data = location_data.loc[
                        location_data["pitch_type"].eq(selected_location_pitch)
                    ].copy()
                    if location_hand != "All" and "stand" in location_data:
                        location_data = location_data.loc[
                            location_data["stand"].eq("R" if location_hand == "RHH" else "L")
                        ].copy()

                    if location_data.empty:
                        st.info("No plate locations for this pitch and handedness split.")
                    else:
                        top = location_data["sz_top"] if "sz_top" in location_data else pd.Series(dtype=float)
                        bottom = location_data["sz_bot"] if "sz_bot" in location_data else pd.Series(dtype=float)
                        zone_top = float(top.median()) if top.notna().any() else 3.5
                        zone_bottom = float(bottom.median()) if bottom.notna().any() else 1.5
                        if zone_top <= zone_bottom:
                            zone_bottom, zone_top = 1.5, 3.5

                        fig_locations = go.Figure()
                        fig_locations.add_shape(
                            type="rect", x0=-0.83, x1=0.83,
                            y0=zone_bottom, y1=zone_top,
                            line=dict(color=MAROON, width=3),
                            fillcolor="rgba(101,31,50,0.06)",
                        )
                        for x_guide in (-0.83 / 3, 0.83 / 3):
                            fig_locations.add_shape(
                                type="line", x0=x_guide, x1=x_guide,
                                y0=zone_bottom, y1=zone_top,
                                line=dict(color="#C9A5A0", width=1, dash="dot"),
                            )
                        for fraction in (1 / 3, 2 / 3):
                            y_guide = zone_bottom + fraction * (zone_top - zone_bottom)
                            fig_locations.add_shape(
                                type="line", x0=-0.83, x1=0.83,
                                y0=y_guide, y1=y_guide,
                                line=dict(color="#C9A5A0", width=1, dash="dot"),
                            )

                        fig_locations.add_trace(go.Scattergl(
                            x=location_data["plate_x"],
                            y=location_data["plate_z"],
                            mode="markers",
                            marker=dict(
                                size=7, opacity=0.42,
                                color=pitch_colors.get(selected_location_pitch, BURNT_ORANGE),
                            ),
                            name=selected_location_pitch,
                            hovertemplate=(
                                f"{selected_location_pitch}<br>"
                                "Plate X: %{x:.2f} ft<br>"
                                "Plate Z: %{y:.2f} ft<extra></extra>"
                            ),
                        ))
                        fig_locations.update_layout(
                            height=700,
                            xaxis_title="Horizontal Plate Location (ft)",
                            yaxis_title="Height Above Ground (ft)",
                            showlegend=False,
                            margin=dict(l=25, r=20, t=20, b=35),
                            xaxis=dict(range=[-2.5, 2.5]),
                            yaxis=dict(range=[0.5, 5.2]),
                        )
                        st.plotly_chart(style_plotly(fig_locations), use_container_width=True)
                        st.caption(
                            f"{len(location_data):,} {selected_location_pitch} pitches shown. "
                            "Strike-zone boundaries use the selected pitches' median batter-specific "
                            "top and bottom; locations are plotted from Statcast plate coordinates."
                        )


except requests.RequestException as error:
    st.error(f"MLB API request failed: {error}")

except (KeyError, IndexError, ValueError) as error:
    st.error(f"Unable to process player data: {error}")









