from __future__ import annotations

import base64
import html
import os
from datetime import date
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client


ROOT_DIR = Path(__file__).parent
BACKGROUND_PATH = ROOT_DIR / "assets" / "background.png"
TEAM_LOGO_BUCKET = "camp-br-u20-player-images"
TEAM_LOGO_FOLDER = "teams"

TABLE_CANDIDATES = [
    "bio_jogadores",
    "jogadores_visualizacao",
    "visualizacao_jogadores",
    "base_visualizacao",
    "jogadores_stats",
    "player_stats",
    "jogadores",
    "players",
    "camp_br_u20",
    "brasileirao_sub20_2026",
    "jogadores_brasileirao_sub20_2026",
]

TEAM_COLUMN_CANDIDATES = [
    "time",
    "equipe",
    "clube",
    "team",
    "club",
    "nome_time",
    "team_name",
]

PLAYER_COLUMN_CANDIDATES = [
    "jogador",
    "nome_jogador",
    "player",
    "player_name",
    "atleta",
    "nome",
    "name",
]


st.set_page_config(
    page_title="Brasileiro Sub-20 2026",
    page_icon=str(BACKGROUND_PATH),
    layout="wide",
    initial_sidebar_state="expanded",
)


def get_env_value(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value.strip()
    return None


def first_existing_column(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    normalized = {column.lower(): column for column in columns}
    for candidate in candidates:
        if candidate.lower() in normalized:
            return normalized[candidate.lower()]
    return None


def load_background_css() -> str:
    if not BACKGROUND_PATH.exists():
        return ""

    encoded = base64.b64encode(BACKGROUND_PATH.read_bytes()).decode("utf-8")
    return f"""
    <style>
        .stApp {{
            background:
                radial-gradient(circle at 82% 18%, rgba(56, 189, 248, 0.22), transparent 28rem),
                linear-gradient(90deg, rgba(5, 10, 14, 0.96), rgba(5, 10, 14, 0.78) 48%, rgba(5, 10, 14, 0.58)),
                url("data:image/png;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}

        [data-testid="stSidebar"] {{
            background: rgba(4, 10, 14, 0.94);
            border-right: 1px solid rgba(255, 255, 255, 0.13);
        }}

        [data-testid="stHeader"] {{
            background: rgba(0, 0, 0, 0);
        }}

        .block-container {{
            padding-top: 1.4rem;
            padding-bottom: 2rem;
            max-width: 1320px;
        }}

        .hero {{
            background: linear-gradient(135deg, rgba(8, 16, 22, 0.90), rgba(8, 16, 22, 0.58));
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 8px;
            box-shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
            display: grid;
            grid-template-columns: 128px minmax(0, 1fr);
            gap: 1.25rem;
            margin-bottom: 1.15rem;
            overflow: hidden;
            padding: 1.15rem 1.25rem;
            position: relative;
        }}

        .hero::before {{
            background: linear-gradient(90deg, #22c55e, #facc15, #38bdf8);
            content: "";
            height: 4px;
            left: 0;
            position: absolute;
            right: 0;
            top: 0;
        }}

        .team-crest {{
            align-items: center;
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid rgba(255, 255, 255, 0.45);
            border-radius: 8px;
            display: flex;
            height: 118px;
            justify-content: center;
            padding: 0.85rem;
            width: 118px;
        }}

        .team-crest img {{
            max-height: 92px;
            max-width: 92px;
            object-fit: contain;
        }}

        .eyebrow {{
            color: rgba(226, 232, 240, 0.74);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0;
            margin-bottom: 0.35rem;
            text-transform: uppercase;
        }}

        .main-title {{
            color: #f8fafc;
            font-size: clamp(2.1rem, 5vw, 5.2rem);
            font-weight: 900;
            line-height: 0.92;
            margin: 0 0 0.55rem 0;
            text-shadow: 0 14px 44px rgba(0, 0, 0, 0.42);
        }}

        .subtitle {{
            color: rgba(248, 250, 252, 0.84);
            font-size: 1.06rem;
            font-weight: 600;
            margin: 0;
        }}

        .quick-row {{
            display: grid;
            gap: 0.75rem;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            margin: 0.95rem 0 1.15rem 0;
        }}

        .bio-card {{
            background: rgba(7, 13, 18, 0.76);
            border: 1px solid rgba(255, 255, 255, 0.13);
            border-radius: 8px;
            min-height: 86px;
            padding: 0.85rem 0.95rem;
        }}

        .bio-label {{
            color: rgba(203, 213, 225, 0.72);
            font-size: 0.72rem;
            font-weight: 700;
            margin-bottom: 0.35rem;
            text-transform: uppercase;
        }}

        .bio-value {{
            color: #f8fafc;
            font-size: clamp(1.05rem, 1.55vw, 1.55rem);
            font-weight: 800;
            line-height: 1.08;
        }}

        .panel {{
            background: rgba(7, 13, 18, 0.74);
            border: 1px solid rgba(255, 255, 255, 0.13);
            border-radius: 8px;
            padding: 1.05rem;
        }}

        [data-testid="stMetric"] {{
            background: rgba(9, 16, 21, 0.72);
            border: 1px solid rgba(255, 255, 255, 0.10);
            border-radius: 8px;
            padding: 0.85rem 1rem;
        }}

        [data-testid="stMetricLabel"] p,
        [data-testid="stMetricValue"] {{
            color: #f8fafc;
        }}

        h1, h2, h3, label, p, span {{
            color: #f8fafc;
        }}

        @media (max-width: 760px) {{
            .hero {{
                grid-template-columns: 82px minmax(0, 1fr);
                padding: 1rem;
            }}

            .team-crest {{
                height: 76px;
                width: 76px;
            }}

            .team-crest img {{
                max-height: 60px;
                max-width: 60px;
            }}

            .quick-row {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
        }}
    </style>
    """


@st.cache_resource(show_spinner=False)
def get_supabase_client() -> Client:
    load_dotenv()
    url = get_env_value("SUPABASE_URL")
    key = get_env_value("SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SECRET_KEY")

    if not url or not key:
        st.error("Configure SUPABASE_URL e uma chave do Supabase no .env.")
        st.stop()

    return create_client(url, key)


@st.cache_data(ttl=300, show_spinner="Carregando dados do Supabase...")
def load_table_data() -> tuple[pd.DataFrame, str]:
    client = get_supabase_client()
    schema = get_env_value("SUPABASE_SCHEMA") or "camp-br-u20"
    preferred_table = get_env_value("SUPABASE_TABLE", "SUPABASE_PLAYERS_TABLE")
    tables = [preferred_table, *TABLE_CANDIDATES] if preferred_table else TABLE_CANDIDATES
    last_error = ""

    for table in dict.fromkeys(filter(None, tables)):
        try:
            rows: list[dict] = []
            page_size = 1000
            start = 0

            while True:
                response = (
                    client.schema(schema)
                    .table(table)
                    .select("*")
                    .range(start, start + page_size - 1)
                    .execute()
                )
                batch = response.data or []
                rows.extend(batch)

                if len(batch) < page_size:
                    break

                start += page_size

            if rows:
                return pd.DataFrame(rows), f"{schema}.{table}"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)

    detail = f" Último retorno: {last_error}" if last_error else ""
    raise RuntimeError(
        "Não encontrei uma tabela de jogadores com os nomes esperados. "
        "Defina SUPABASE_TABLE no .env com o nome correto da tabela."
        + detail
    )


def format_number(value: object) -> str:
    if pd.isna(value):
        return "-"

    if isinstance(value, (int, np.integer)):
        return f"{value:,}".replace(",", ".")

    if isinstance(value, (float, np.floating)):
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    return str(value)


def clean_text(value: object, fallback: str = "-") -> str:
    if pd.isna(value):
        return fallback

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "-"}:
        return fallback

    return text.replace("_", " ").title()


def row_value(row: pd.Series, column: str, fallback: str = "-") -> str:
    return clean_text(row[column], fallback) if column in row.index else fallback


def calculate_age(value: object) -> str:
    if pd.isna(value):
        return "-"

    try:
        born = pd.to_datetime(value, errors="coerce").date()
    except Exception:  # noqa: BLE001
        return "-"

    if pd.isna(born):
        return "-"

    today = date.today()
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    return f"{age} anos"


def format_height(value: object) -> str:
    if pd.isna(value):
        return "-"

    text = str(value).strip().replace(",", ".")
    if not text or text == "-":
        return "-"

    try:
        height = float(text)
        return f"{int(height)} cm" if height.is_integer() else f"{height:.1f} cm"
    except ValueError:
        return text


def image_data_uri(image_bytes: bytes | None) -> str:
    if not image_bytes:
        return ""

    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def normalized_options(series: pd.Series) -> list[str]:
    values = series.dropna().astype(str).str.strip()
    return sorted(value for value in values.unique() if value)


def storage_path_id(value: object) -> str | None:
    if pd.isna(value):
        return None

    if isinstance(value, (int, np.integer)):
        return str(value)

    if isinstance(value, (float, np.floating)) and value.is_integer():
        return str(int(value))

    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


@st.cache_data(ttl=3600, show_spinner=False)
def load_team_logo(team_id: object) -> bytes | None:
    path_id = storage_path_id(team_id)
    if not path_id:
        return None

    try:
        bucket = get_env_value("SUPABASE_TEAM_LOGO_BUCKET") or TEAM_LOGO_BUCKET
        folder = get_env_value("SUPABASE_TEAM_LOGO_FOLDER") or TEAM_LOGO_FOLDER
        path = f"{folder}/{path_id}.png"
        return get_supabase_client().storage.from_(bucket).download(path)
    except Exception:  # noqa: BLE001
        return None


def numeric_columns_for_player(df: pd.DataFrame, excluded: set[str]) -> list[str]:
    numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()
    return [
        column
        for column in numeric_columns
        if column not in excluded and not column.lower().endswith("_id") and column.lower() != "id"
    ]


st.markdown(load_background_css(), unsafe_allow_html=True)

try:
    data, table_name = load_table_data()
except Exception as exc:  # noqa: BLE001
    st.error(str(exc))
    st.stop()

team_column = get_env_value("SUPABASE_TEAM_COLUMN") or first_existing_column(
    data.columns,
    TEAM_COLUMN_CANDIDATES,
)
player_column = get_env_value("SUPABASE_PLAYER_COLUMN") or first_existing_column(
    data.columns,
    PLAYER_COLUMN_CANDIDATES,
)

if not team_column or team_column not in data.columns:
    st.error("Não encontrei a coluna do time. Defina SUPABASE_TEAM_COLUMN no .env.")
    st.stop()

if not player_column or player_column not in data.columns:
    st.error("Não encontrei a coluna do jogador. Defina SUPABASE_PLAYER_COLUMN no .env.")
    st.stop()

teams = normalized_options(data[team_column])

with st.sidebar:
    st.title("Filtros")
    selected_team = st.selectbox("Time", teams, index=0 if teams else None)

    team_data = data[data[team_column].astype(str).str.strip() == selected_team].copy()
    players = normalized_options(team_data[player_column])
    selected_player = st.selectbox("Jogador", players, index=0 if players else None)

if not selected_team or not selected_player:
    st.warning("Selecione um time e um jogador.")
    st.stop()

player_rows = team_data[team_data[player_column].astype(str).str.strip() == selected_player].copy()
player_row = player_rows.iloc[0]
excluded_columns = {team_column, player_column}
numeric_columns = numeric_columns_for_player(player_rows, excluded_columns)
team_id = player_row["time_id"] if "time_id" in player_row.index else None
team_logo = load_team_logo(team_id)
team_logo_uri = image_data_uri(team_logo)
team_logo_html = (
    f'<img src="{team_logo_uri}" alt="Escudo {html.escape(selected_team)}">'
    if team_logo_uri
    else ""
)
player_position = row_value(player_row, "posicao_principal_detalhada") or row_value(player_row, "posicao_jogador")
player_country = row_value(player_row, "pais")
player_height = format_height(player_row["altura_cm"]) if "altura_cm" in player_row.index else "-"
player_age = calculate_age(player_row["data_nascimento"]) if "data_nascimento" in player_row.index else "-"
player_foot = row_value(player_row, "pe_preferido")
player_contract = row_value(player_row, "contrato_ate")

st.markdown(
    f"""
    <section class="hero">
        <div class="team-crest">{team_logo_html}</div>
        <div>
            <div class="eyebrow">Campeonato Brasileiro Sub-20 2026</div>
            <div class="main-title">{html.escape(selected_team)}</div>
            <p class="subtitle">{html.escape(selected_player)} | {html.escape(player_position)}</p>
        </div>
    </section>
    <section class="quick-row">
        <div class="bio-card">
            <div class="bio-label">Altura</div>
            <div class="bio-value">{html.escape(player_height)}</div>
        </div>
        <div class="bio-card">
            <div class="bio-label">Idade</div>
            <div class="bio-value">{html.escape(player_age)}</div>
        </div>
        <div class="bio-card">
            <div class="bio-label">Pe preferido</div>
            <div class="bio-value">{html.escape(player_foot)}</div>
        </div>
        <div class="bio-card">
            <div class="bio-label">Pais</div>
            <div class="bio-value">{html.escape(player_country)}</div>
        </div>
        <div class="bio-card">
            <div class="bio-label">Contrato ate</div>
            <div class="bio-value">{html.escape(player_contract)}</div>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([1.05, 0.95], gap="large")

with left:
    st.subheader("Ficha do Atleta")
    display_columns = [
        column
        for column in [
            player_column,
            "posicao_principal_detalhada",
            "posicao_jogador",
            "altura_cm",
            "data_nascimento",
            "pe_preferido",
            "pais",
            "contrato_ate",
            team_column,
        ]
        if column in player_rows.columns
    ]
    display_data = player_rows[display_columns].dropna(axis=1, how="all").copy()
    display_data = display_data.rename(
        columns={
            player_column: "Jogador",
            team_column: "Time",
            "posicao_principal_detalhada": "Posicao",
            "posicao_jogador": "Perfil",
            "altura_cm": "Altura",
            "data_nascimento": "Nascimento",
            "pe_preferido": "Pe preferido",
            "pais": "Pais",
            "contrato_ate": "Contrato ate",
        }
    )
    st.dataframe(display_data, use_container_width=True, hide_index=True)

with right:
    st.subheader("Mapa do Elenco")
    position_column = (
        "posicao_principal_detalhada"
        if "posicao_principal_detalhada" in team_data.columns
        else "posicao_jogador"
        if "posicao_jogador" in team_data.columns
        else None
    )

    if position_column:
        chart_data = (
            team_data[position_column]
            .dropna()
            .astype(str)
            .str.replace("_", " ")
            .str.title()
            .value_counts()
            .reset_index()
        )
        chart_data.columns = ["posicao", "jogadores"]
        chart_data = chart_data.sort_values("jogadores", ascending=True)

        fig = px.bar(
            chart_data,
            x="jogadores",
            y="posicao",
            orientation="h",
            text="jogadores",
            color="jogadores",
            color_continuous_scale=["#22c55e", "#facc15", "#38bdf8"],
        )
        fig.update_layout(
            height=max(360, 28 * len(chart_data)),
            margin=dict(l=8, r=8, t=8, b=8),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#f8fafc",
            coloraxis_showscale=False,
            xaxis=dict(gridcolor="rgba(255,255,255,0.12)", zeroline=False, title=""),
            yaxis=dict(gridcolor="rgba(255,255,255,0.00)", title=""),
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Ainda nao ha dados suficientes para montar o mapa do elenco.")

st.caption(f"Tabela Supabase: {table_name}")
