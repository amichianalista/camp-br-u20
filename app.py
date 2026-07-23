from __future__ import annotations

import base64
import html
import os
import unicodedata
from datetime import date
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import psycopg
import streamlit as st
from psycopg import sql
from dotenv import load_dotenv
from supabase import Client, create_client


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")
BACKGROUND_PATH = ROOT_DIR / "assets" / "background.png"
TEAM_LOGO_BUCKET = "jogadores-br-sub-20"
TEAM_LOGO_FOLDER = "teams"
PLAYER_IMAGE_FOLDER = "players"
SCORE_SCHEMA = "jogadores-br-sub-20"
SCORE_TABLES = [
    "fact.scores_players.atacantes",
    "fact.scores_players.defensores",
    "fact.scores_players.goleiros",
    "fact.scores_players.laterais",
    "fact.scores_players.meias",
]
SCORE_ID_COLUMN = "jogador_id"
SCORE_VALUE_PREFIX = "pontuacao_"
SCORE_PERCENTILE_PREFIX = "percentil_"
SCORE_METADATA_COLUMNS = {
    "jogador_id",
    "posicao",
    "minutos_jogados",
    "persona",
    "ranking_percentil",
}
IMAGE_MIME_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}

TABLE_CANDIDATES = [
    "player_bio",
    "bio_jogadores",
    "jogadores_visualizacao",
    "visualizacao_jogadores",
    "base_visualizacao",
    "jogadores_stats",
    "player_stats",
    "jogadores",
    "players",
    "camp_br_u20",
    "jogadores_br_sub_20",
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

POSITION_COLUMN_CANDIDATES = [
    "posicao_principal_detalhada",
    "posicao_principal",
    "posicao_jogador",
    "posicao",
    "position",
    "player_position",
]

PAGE_PERFIL_INDIVIDUAL = "Perfil Individual"
PAGE_PERFIL_FUNCAO = "Perfil por Função"
APP_PAGES = [PAGE_PERFIL_INDIVIDUAL, PAGE_PERFIL_FUNCAO]
DEFAULT_TEAM_NAME = "América Mineiro U20"
DEFAULT_TEAM_ALIASES = (
    DEFAULT_TEAM_NAME,
    "America Mineiro U20",
    "Am�rica Mineiro U20",
)
FUNCTION_ORDER = ["Goleiro", "Lateral", "Defensor", "Meia", "Atacante", "Outras funções"]


st.set_page_config(
    page_title="Variaveis Tecnicas | Base BR",
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

        [data-testid="stHeader"] {{
            background: rgba(0, 0, 0, 0);
        }}

        [data-testid="stSidebar"] {{
            background: rgba(4, 10, 14, 0.95);
            border-right: 1px solid rgba(255, 255, 255, 0.12);
            min-width: 185px;
            width: 185px;
        }}

        [data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
            padding: 1rem 0.65rem;
        }}

        .nav-title {{
            color: rgba(34, 197, 94, 0.95);
            font-size: 0.72rem;
            font-weight: 900;
            margin: 0 0 0.55rem 0;
            text-transform: uppercase;
        }}

        [data-testid="stSidebar"] label p,
        [data-testid="stSidebar"] span {{
            color: #f8fafc;
        }}

        .block-container {{
            max-width: 1080px;
            min-height: 1030px;
            padding-bottom: 1rem;
            padding-left: 1.25rem;
            padding-right: 1.25rem;
            padding-top: 0.45rem;
        }}

        .filter-heading {{
            color: rgba(34, 197, 94, 0.95);
            font-size: 0.72rem;
            font-weight: 800;
            margin: 0 0 0.25rem 0;
            text-transform: uppercase;
        }}

        div[data-testid="stSelectbox"] label p {{
            color: rgba(226, 232, 240, 0.74);
            font-size: 0.72rem;
            font-weight: 800;
            text-transform: uppercase;
        }}

        div[data-testid="stSelectbox"] > div {{
            background: rgba(7, 13, 18, 0.78);
            border-radius: 8px;
        }}

        .team-hero {{
            background: linear-gradient(135deg, rgba(8, 16, 22, 0.90), rgba(8, 16, 22, 0.58));
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 8px;
            box-shadow: 0 18px 54px rgba(0, 0, 0, 0.34);
            display: grid;
            grid-template-columns: 96px minmax(0, 1fr);
            gap: 0.95rem;
            margin-bottom: 0.55rem;
            margin-top: 0.25rem;
            overflow: hidden;
            padding: 0.68rem 0.9rem;
            position: relative;
        }}

        .team-hero::before {{
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
            height: 78px;
            justify-content: center;
            padding: 0.65rem;
            width: 78px;
        }}

        .team-crest img {{
            max-height: 60px;
            max-width: 60px;
            object-fit: contain;
        }}

        .eyebrow {{
            color: rgba(226, 232, 240, 0.74);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0;
            margin-bottom: 0.22rem;
            text-transform: uppercase;
        }}

        .main-title {{
            color: #f8fafc;
            font-size: clamp(1.8rem, 4.2vw, 3.8rem);
            font-weight: 900;
            line-height: 0.95;
            margin: 0 0 0.32rem 0;
            text-shadow: 0 14px 44px rgba(0, 0, 0, 0.42);
        }}

        .subtitle {{
            color: rgba(248, 250, 252, 0.84);
            font-size: 0.95rem;
            font-weight: 600;
            margin: 0;
        }}

        .player-kicker {{
            color: rgba(34, 197, 94, 0.95);
            font-size: 0.78rem;
            font-weight: 800;
            margin: 0.35rem 0 0.16rem 0;
            text-transform: uppercase;
        }}

        .player-name {{
            color: #f8fafc;
            font-size: clamp(1.8rem, 4vw, 3.45rem);
            font-weight: 900;
            line-height: 0.98;
            margin: 0;
            text-shadow: 0 12px 38px rgba(0, 0, 0, 0.48);
        }}

        .player-position {{
            color: rgba(248, 250, 252, 0.78);
            font-size: clamp(0.95rem, 1.45vw, 1.15rem);
            font-weight: 700;
            margin: 0.22rem 0 0.6rem 0;
        }}

        .player-board {{
            background:
                linear-gradient(135deg, rgba(7, 13, 18, 0.92), rgba(7, 13, 18, 0.66));
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 8px;
            display: grid;
            align-items: start;
            gap: 0.65rem;
            grid-template-columns: minmax(160px, 205px) minmax(245px, 310px) minmax(300px, 1fr);
            overflow: hidden;
            padding: 0.65rem;
        }}

        .player-photo {{
            align-items: flex-end;
            background: linear-gradient(180deg, rgba(15, 23, 42, 0.32), rgba(2, 6, 23, 0.84));
            border: 1px solid rgba(255, 255, 255, 0.13);
            border-radius: 8px;
            display: flex;
            justify-content: center;
            min-height: 220px;
            overflow: hidden;
        }}

        .player-photo img {{
            display: block;
            height: 220px;
            max-width: 100%;
            object-fit: cover;
            object-position: center top;
            width: 100%;
        }}

        .player-photo-placeholder {{
            color: rgba(226, 232, 240, 0.62);
            font-size: 0.86rem;
            font-weight: 700;
            padding: 2rem;
            text-align: center;
            text-transform: uppercase;
        }}

        .bio-grid {{
            display: grid;
            align-content: start;
            gap: 0.38rem;
            grid-auto-rows: minmax(58px, auto);
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }}

        .bio-card {{
            background: rgba(255, 255, 255, 0.075);
            border: 1px solid rgba(255, 255, 255, 0.13);
            border-radius: 8px;
            min-height: 58px;
            padding: 0.44rem 0.5rem;
        }}

        .bio-label {{
            color: rgba(203, 213, 225, 0.72);
            font-size: 0.58rem;
            font-weight: 700;
            margin-bottom: 0.22rem;
            text-transform: uppercase;
        }}

        .bio-value {{
            color: #f8fafc;
            font-size: 0.94rem;
            font-weight: 800;
            line-height: 1.08;
        }}

        .cluster-panel {{
            background:
                linear-gradient(160deg, rgba(34, 197, 94, 0.18), rgba(56, 189, 248, 0.10)),
                rgba(255, 255, 255, 0.075);
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-height: 220px;
            padding: 1.2rem;
        }}

        .cluster-label {{
            color: rgba(203, 213, 225, 0.72);
            font-size: 0.72rem;
            font-weight: 800;
            margin-bottom: 0.55rem;
            text-transform: uppercase;
        }}

        .cluster-value {{
            color: #f8fafc;
            font-size: clamp(2.15rem, 4vw, 3.6rem);
            font-weight: 900;
            line-height: 1;
            margin-bottom: 0;
        }}

        .performance-section {{
            margin-top: 0.7rem;
        }}

        .score-style-section {{
            margin-top: 0.75rem;
        }}

        .score-style-heading {{
            align-items: end;
            display: flex;
            gap: 1rem;
            justify-content: space-between;
            margin-bottom: 0.55rem;
        }}

        .score-radar-panel,
        .score-support-panel {{
            background:
                linear-gradient(145deg, rgba(8, 16, 22, 0.94), rgba(7, 13, 18, 0.74));
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 8px;
            box-shadow: 0 16px 38px rgba(0, 0, 0, 0.26);
            overflow: hidden;
            padding: 0.82rem;
            position: relative;
        }}

        .score-radar-panel::before,
        .score-support-panel::before {{
            background: linear-gradient(90deg, #22c55e, #facc15, #38bdf8);
            content: "";
            height: 3px;
            left: 0;
            position: absolute;
            right: 0;
            top: 0;
        }}

        .score-radar-panel {{
            min-height: 460px;
        }}

        div[data-testid="stPlotlyChart"] {{
            background:
                linear-gradient(145deg, rgba(8, 16, 22, 0.94), rgba(7, 13, 18, 0.74));
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 8px;
            box-shadow: 0 16px 38px rgba(0, 0, 0, 0.26);
            min-height: 460px;
            overflow: hidden;
            padding: 0.82rem;
        }}

        .score-support-panel {{
            min-height: 460px;
        }}

        .ranking-card {{
            background:
                linear-gradient(135deg, rgba(34, 197, 94, 0.16), rgba(56, 189, 248, 0.08)),
                rgba(255, 255, 255, 0.055);
            border: 1px solid rgba(34, 197, 94, 0.22);
            border-radius: 8px;
            margin-bottom: 0.72rem;
            padding: 0.76rem 0.82rem;
        }}

        .ranking-label {{
            color: rgba(203, 213, 225, 0.72);
            font-size: 0.62rem;
            font-weight: 900;
            margin-bottom: 0.18rem;
            text-transform: uppercase;
        }}

        .ranking-value {{
            color: #f8fafc;
            font-size: 2.05rem;
            font-weight: 900;
            line-height: 1;
        }}

        .score-support-table {{
            border-collapse: separate;
            border-spacing: 0 0.36rem;
            width: 100%;
        }}

        .score-support-table th {{
            color: rgba(203, 213, 225, 0.66);
            font-size: 0.58rem;
            font-weight: 900;
            padding: 0 0.36rem 0.1rem 0.36rem;
            text-align: left;
            text-transform: uppercase;
        }}

        .score-support-table td {{
            background: rgba(255, 255, 255, 0.055);
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            border-top: 1px solid rgba(255, 255, 255, 0.08);
            color: #f8fafc;
            font-size: 0.74rem;
            font-weight: 800;
            line-height: 1.1;
            padding: 0.48rem 0.36rem;
            vertical-align: middle;
        }}

        .score-support-table td:first-child {{
            border-left: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px 0 0 8px;
            color: rgba(226, 232, 240, 0.84);
            font-weight: 900;
        }}

        .score-support-table td:last-child {{
            border-radius: 0 8px 8px 0;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }}

        .section-header {{
            align-items: end;
            display: flex;
            gap: 1rem;
            justify-content: space-between;
            margin: 0 0 0.55rem 0;
        }}

        .section-title {{
            color: #f8fafc;
            font-size: clamp(1.25rem, 2vw, 1.8rem);
            font-weight: 900;
            line-height: 1;
            margin: 0;
        }}

        .section-note {{
            color: rgba(226, 232, 240, 0.64);
            font-size: 0.82rem;
            font-weight: 700;
            margin: 0;
        }}

        .performance-grid {{
            display: grid;
            gap: 0.6rem;
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }}

        .performance-card {{
            background:
                linear-gradient(160deg, rgba(15, 23, 42, 0.86), rgba(7, 13, 18, 0.72));
            border: 1px solid rgba(255, 255, 255, 0.13);
            border-radius: 8px;
            overflow: hidden;
            padding: 0.72rem;
        }}

        .performance-top {{
            align-items: center;
            display: grid;
            gap: 0.85rem;
            grid-template-columns: 92px minmax(0, 1fr);
            margin-bottom: 0.65rem;
        }}

        .percent-gauge {{
            align-items: center;
            background:
                conic-gradient(#22c55e calc(var(--pct) * 1%), rgba(255, 255, 255, 0.10) 0);
            border-radius: 50%;
            display: flex;
            height: 86px;
            justify-content: center;
            position: relative;
            width: 86px;
        }}

        .percent-gauge::after {{
            background: rgba(7, 13, 18, 0.96);
            border-radius: 50%;
            content: "";
            height: 66px;
            position: absolute;
            width: 66px;
        }}

        .percent-number {{
            color: #f8fafc;
            font-size: 1.3rem;
            font-weight: 900;
            position: relative;
            z-index: 1;
        }}

        .performance-label {{
            color: rgba(203, 213, 225, 0.72);
            font-size: 0.66rem;
            font-weight: 800;
            margin-bottom: 0.3rem;
            text-transform: uppercase;
        }}

        .performance-name {{
            color: #f8fafc;
            font-size: 1.06rem;
            font-weight: 900;
            line-height: 1.05;
            margin-bottom: 0.45rem;
        }}

        .percent-bar {{
            background: rgba(255, 255, 255, 0.10);
            border-radius: 999px;
            height: 7px;
            overflow: hidden;
        }}

        .percent-fill {{
            background: linear-gradient(90deg, #22c55e, #facc15, #38bdf8);
            border-radius: 999px;
            height: 100%;
            width: calc(var(--pct) * 1%);
        }}

        .metric-list {{
            display: grid;
            gap: 0.38rem;
        }}

        .metric-row {{
            align-items: center;
            background: rgba(255, 255, 255, 0.055);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
            padding: 0.43rem 0.52rem;
        }}

        .metric-name {{
            color: rgba(226, 232, 240, 0.78);
            font-size: 0.76rem;
            font-weight: 700;
            overflow: hidden;
            padding-right: 0.6rem;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .metric-value {{
            color: #f8fafc;
            font-size: 0.86rem;
            font-weight: 900;
            white-space: nowrap;
        }}

        .panel {{
            background: rgba(7, 13, 18, 0.74);
            border: 1px solid rgba(255, 255, 255, 0.13);
            border-radius: 8px;
            padding: 1.05rem;
        }}

        .empty-page {{
            background: linear-gradient(135deg, rgba(8, 16, 22, 0.90), rgba(8, 16, 22, 0.58));
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 8px;
            margin-top: 0.25rem;
            padding: 1rem;
        }}

        .function-section {{
            background:
                linear-gradient(145deg, rgba(8, 16, 22, 0.92), rgba(7, 13, 18, 0.70));
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 8px;
            box-shadow: 0 10px 26px rgba(0, 0, 0, 0.22);
            margin-top: 0.55rem;
            margin-bottom: 0.08rem;
            overflow: hidden;
            padding: 0.48rem 0.62rem;
            position: relative;
        }}

        .cluster-button-row {{
            margin-top: -0.42rem;
        }}

        .cluster-button-row div[data-testid="column"] {{
            padding-top: 0;
        }}

        .function-section::before {{
            background: linear-gradient(90deg, #22c55e, #facc15, #38bdf8);
            content: "";
            height: 3px;
            left: 0;
            position: absolute;
            right: 0;
            top: 0;
        }}

        .function-header {{
            align-items: center;
            display: flex;
            gap: 0.8rem;
            justify-content: space-between;
            margin: 0.08rem 0 0 0;
        }}

        .function-title {{
            color: #f8fafc;
            font-size: 0.98rem;
            font-weight: 900;
            line-height: 1;
            margin: 0;
        }}

        .function-count {{
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 999px;
            color: rgba(248, 250, 252, 0.76);
            font-size: 0.66rem;
            font-weight: 800;
            padding: 0.2rem 0.46rem;
            white-space: nowrap;
        }}

        .function-note {{
            color: rgba(226, 232, 240, 0.62);
            font-size: 0.78rem;
            font-weight: 700;
            margin: 0 0 0.55rem 0;
        }}

        .selected-cluster {{
            background:
                linear-gradient(135deg, rgba(34, 197, 94, 0.13), rgba(56, 189, 248, 0.08)),
                rgba(255, 255, 255, 0.045);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 8px;
            margin-top: 0.1rem;
            margin-bottom: 0.05rem;
            padding: 0.48rem 0.58rem;
            position: relative;
        }}

        .cluster-player-row {{
            margin-top: -0.42rem;
        }}

        .player-list-title {{
            color: #f8fafc;
            font-size: 0.94rem;
            font-weight: 900;
            margin: 0.12rem 0 0 0;
        }}

        .selected-player-summary {{
            color: rgba(248, 250, 252, 0.72);
            font-size: 0.82rem;
            font-weight: 700;
            margin: 0.15rem 0 0.6rem 0;
        }}

        .player-score-shell {{
            background:
                linear-gradient(135deg, rgba(8, 16, 22, 0.96), rgba(7, 13, 18, 0.78));
            border: 1px solid rgba(34, 197, 94, 0.22);
            border-radius: 8px;
            box-shadow: 0 16px 36px rgba(0, 0, 0, 0.28);
            margin-bottom: 0.7rem;
            margin-top: 0;
            padding: 0.88rem;
            position: relative;
        }}

        .player-score-shell::before {{
            background: linear-gradient(90deg, #22c55e, #facc15, #38bdf8);
            content: "";
            height: 3px;
            left: 0;
            position: absolute;
            right: 0;
            top: 0;
        }}

        .dialog-player-card {{
            background:
                linear-gradient(135deg, rgba(8, 16, 22, 0.96), rgba(7, 13, 18, 0.78));
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 8px;
            display: grid;
            gap: 0.85rem;
            grid-template-columns: 150px minmax(0, 1fr);
            margin-bottom: 0.65rem;
            overflow: hidden;
            padding: 0.68rem;
        }}

        .dialog-bio-shell {{
            background:
                linear-gradient(135deg, rgba(8, 16, 22, 0.90), rgba(7, 13, 18, 0.68));
            border: 1px solid rgba(255, 255, 255, 0.10);
            border-radius: 8px;
            padding: 0.62rem;
        }}

        .dialog-player-photo {{
            align-items: flex-end;
            background: rgba(2, 6, 23, 0.56);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 8px;
            display: flex;
            height: 176px;
            justify-content: center;
            overflow: hidden;
        }}

        .dialog-player-photo img {{
            display: block;
            height: 176px;
            object-fit: cover;
            object-position: center top;
            width: 100%;
        }}

        .dialog-player-meta {{
            align-content: start;
            display: grid;
            gap: 0.56rem;
        }}

        .dialog-quick-facts {{
            display: grid;
            gap: 0.42rem;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            margin-top: 0.4rem;
            max-width: 620px;
        }}

        .dialog-cluster-highlight {{
            background:
                linear-gradient(135deg, rgba(34, 197, 94, 0.20), rgba(56, 189, 248, 0.11)),
                rgba(255, 255, 255, 0.055);
            border: 1px solid rgba(34, 197, 94, 0.26);
            border-radius: 8px;
            margin-top: 0.35rem;
            padding: 0.58rem 0.68rem;
        }}

        .dialog-cluster-label {{
            color: rgba(34, 197, 94, 0.96);
            font-size: 0.66rem;
            font-weight: 900;
            margin-bottom: 0.18rem;
            text-transform: uppercase;
        }}

        .dialog-cluster-value {{
            color: #f8fafc;
            font-size: clamp(1.25rem, 2vw, 1.9rem);
            font-weight: 900;
            line-height: 1;
        }}

        .dialog-raw-title {{
            align-items: center;
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
        }}

        .dialog-bio-grid {{
            display: grid;
            gap: 0.38rem;
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }}

        .dialog-bio-card {{
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            min-height: 48px;
            padding: 0.38rem 0.46rem;
        }}

        .dialog-bio-label {{
            color: rgba(203, 213, 225, 0.72);
            font-size: 0.58rem;
            font-weight: 800;
            margin-bottom: 0.16rem;
            text-transform: uppercase;
        }}

        .dialog-bio-value {{
            color: #f8fafc;
            font-size: 0.82rem;
            font-weight: 900;
            line-height: 1.08;
        }}

        .score-grid {{
            display: grid;
            gap: 0.68rem;
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }}

        .score-card {{
            background:
                linear-gradient(135deg, rgba(34, 197, 94, 0.16), rgba(56, 189, 248, 0.08)),
                rgba(255, 255, 255, 0.065);
            border: 1px solid rgba(34, 197, 94, 0.24);
            border-radius: 8px;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.10);
            padding: 0.78rem 0.86rem;
        }}

        .score-row {{
            align-items: center;
            display: flex;
            gap: 0.75rem;
            justify-content: space-between;
            min-height: 50px;
        }}

        .score-name {{
            color: rgba(226, 232, 240, 0.84);
            font-size: 0.82rem;
            font-weight: 800;
            line-height: 1.12;
        }}

        .score-value {{
            color: #f8fafc;
            font-size: 1.26rem;
            font-weight: 900;
            white-space: nowrap;
        }}

        div[data-testid="stButton"] > button {{
            background:
                linear-gradient(135deg, rgba(34, 197, 94, 0.22), rgba(56, 189, 248, 0.13)),
                rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(34, 197, 94, 0.32);
            border-radius: 8px;
            color: #f8fafc;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12), 0 10px 22px rgba(0, 0, 0, 0.16);
            font-weight: 900;
            min-height: 2.7rem;
            white-space: normal;
            width: 100%;
        }}

        div[data-testid="stButton"] > button:hover {{
            background:
                linear-gradient(135deg, rgba(34, 197, 94, 0.32), rgba(56, 189, 248, 0.18)),
                rgba(255, 255, 255, 0.10);
            border-color: rgba(250, 204, 21, 0.58);
            color: #f8fafc;
            transform: translateY(-1px);
        }}

        div[data-testid="stButton"] > button[data-testid="baseButton-secondary"] {{
            background: rgba(255, 255, 255, 0.06);
            border-color: rgba(255, 255, 255, 0.13);
            box-shadow: none;
            font-weight: 800;
            min-height: 2.35rem;
        }}

        div[data-testid="stButton"] > button[data-testid="baseButton-secondary"]:hover {{
            background: rgba(56, 189, 248, 0.12);
            border-color: rgba(56, 189, 248, 0.34);
            transform: none;
        }}

        div[data-testid="stButton"] > button[title="X"] {{
            background: rgba(255, 255, 255, 0.07);
            border-color: rgba(255, 255, 255, 0.16);
            box-shadow: none;
            font-size: 0.78rem;
            min-height: 2rem;
            padding: 0;
        }}

        div[data-testid="stButton"] > button[title="Fechar cluster"] {{
            background: rgba(255, 255, 255, 0.07);
            border-color: rgba(255, 255, 255, 0.16);
            border-radius: 999px;
            box-shadow: none;
            color: rgba(248, 250, 252, 0.72);
            font-size: 0.72rem;
            min-height: 1.55rem;
            padding: 0;
            width: 1.55rem;
        }}

        div[data-testid="stButton"] > button[title="Fechar cluster"]:hover {{
            background: rgba(248, 113, 113, 0.16);
            border-color: rgba(248, 113, 113, 0.34);
            color: #f8fafc;
        }}

        div[data-testid="stDialog"],
        div[data-testid="stDialog"] div[role="dialog"],
        div[role="dialog"] {{
            background:
                linear-gradient(145deg, rgba(8, 16, 22, 0.98), rgba(7, 13, 18, 0.94)) !important;
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 8px;
        }}

        div[data-testid="stDialog"] h1,
        div[data-testid="stDialog"] h2,
        div[data-testid="stDialog"] h3,
        div[data-testid="stDialog"] p,
        div[data-testid="stDialog"] span,
        div[data-testid="stDialog"] div,
        div[role="dialog"] h1,
        div[role="dialog"] h2,
        div[role="dialog"] h3,
        div[role="dialog"] p,
        div[role="dialog"] span,
        div[role="dialog"] div {{
            color: #f8fafc !important;
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
            .team-hero {{
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

            .player-board {{
                grid-template-columns: 1fr;
            }}

            .player-photo {{
                min-height: 220px;
            }}

            .player-photo img {{
                height: 220px;
            }}

            .bio-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}

            .performance-grid {{
                grid-template-columns: 1fr;
            }}

            .score-grid {{
                grid-template-columns: 1fr;
            }}

            .dialog-player-card {{
                grid-template-columns: 1fr;
            }}

            .dialog-bio-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}

            .dialog-quick-facts {{
                grid-template-columns: 1fr;
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


def get_score_schema() -> str:
    return get_env_value("SUPABASE_SCHEMA") or SCORE_SCHEMA


def get_database_url() -> str | None:
    return get_env_value("SUPABASE_DATABASE_URL")


def fetch_rows_from_database(
    schema: str,
    table: str,
    where_column: str | None = None,
    where_value: object | None = None,
) -> list[dict]:
    database_url = get_database_url()
    if not database_url:
        raise RuntimeError("SUPABASE_DATABASE_URL nao configurado.")

    query = sql.SQL("select * from {}.{}").format(sql.Identifier(schema), sql.Identifier(table))
    params: tuple[object, ...] = ()
    if where_column:
        query += sql.SQL(" where {} = %s").format(sql.Identifier(where_column))
        params = (where_value,)

    with psycopg.connect(database_url, connect_timeout=20) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [description.name for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


def fetch_rows_from_supabase_api(schema: str, table: str) -> list[dict]:
    client = get_supabase_client()
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

    return rows


@st.cache_data(ttl=300, show_spinner="Carregando dados do Supabase...")
def load_table_data() -> tuple[pd.DataFrame, str]:
    schema = get_score_schema()
    preferred_table = get_env_value("SUPABASE_TABLE", "SUPABASE_PLAYERS_TABLE")
    tables = [preferred_table, *TABLE_CANDIDATES] if preferred_table else TABLE_CANDIDATES
    last_error = ""

    for table in dict.fromkeys(filter(None, tables)):
        try:
            rows = (
                fetch_rows_from_database(schema, table)
                if get_database_url()
                else fetch_rows_from_supabase_api(schema, table)
            )
            if rows:
                return pd.DataFrame(rows), f"{schema}.{table}"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)

    detail = f" Ultimo retorno: {last_error}" if last_error else ""
    raise RuntimeError(
        "Nao encontrei uma tabela de jogadores com os nomes esperados. "
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


def first_valid_text(*values: object, fallback: str = "-") -> str:
    for value in values:
        text = clean_text(value, fallback="")
        if text:
            return text
    return fallback


def format_date(value: object) -> str:
    if pd.isna(value):
        return "-"

    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return clean_text(value)

    return parsed.strftime("%d/%m/%Y")


def format_score(value: object) -> str:
    if pd.isna(value):
        return "-"

    try:
        number = float(value)
    except (TypeError, ValueError):
        return clean_text(value)

    return f"{number:.1f}".replace(".", ",")


def format_rank(value: object) -> str:
    if pd.isna(value):
        return "-"

    try:
        number = float(value)
    except (TypeError, ValueError):
        return clean_text(value)

    return f"#{int(number)}" if number.is_integer() else f"#{format_score(number)}"


def format_percentile(value: object) -> str:
    formatted = format_score(value)
    return "-" if formatted == "-" else f"{formatted}%"


def format_metric_value(value: object, is_percentual: object = False) -> str:
    if pd.isna(value):
        return "-"

    try:
        number = float(value)
    except (TypeError, ValueError):
        return clean_text(value)

    suffix = "%" if str(is_percentual).lower() == "true" else ""
    if number.is_integer():
        return f"{int(number)}{suffix}"

    return f"{number:.1f}".replace(".", ",") + suffix


def humanize_key(value: str) -> str:
    return clean_text(value)


def score_category_name(column_suffix: str) -> str:
    return humanize_key(column_suffix)


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


def image_data_uri(image_bytes: bytes | None, mime_type: str = "image/png") -> str:
    if not image_bytes:
        return ""

    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


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
def load_team_logo(team_id: object) -> tuple[bytes | None, str]:
    path_id = storage_path_id(team_id)
    if not path_id:
        return None, "image/png"

    bucket = get_env_value("SUPABASE_TEAM_LOGO_BUCKET") or TEAM_LOGO_BUCKET
    folder = get_env_value("SUPABASE_TEAM_LOGO_FOLDER") or TEAM_LOGO_FOLDER

    for extension, mime_type in IMAGE_MIME_TYPES.items():
        try:
            path = f"{folder}/{path_id}.{extension}"
            return get_supabase_client().storage.from_(bucket).download(path), mime_type
        except Exception:  # noqa: BLE001
            continue

    return None, "image/png"


@st.cache_data(ttl=3600, show_spinner=False)
def load_player_photo(player_id: object) -> tuple[bytes | None, str]:
    path_id = storage_path_id(player_id)
    if not path_id:
        return None, "image/png"

    bucket = get_env_value("SUPABASE_PLAYER_IMAGE_BUCKET") or TEAM_LOGO_BUCKET
    folder = get_env_value("SUPABASE_PLAYER_IMAGE_FOLDER") or PLAYER_IMAGE_FOLDER

    for extension, mime_type in IMAGE_MIME_TYPES.items():
        try:
            path = f"{folder}/{path_id}.{extension}"
            return get_supabase_client().storage.from_(bucket).download(path), mime_type
        except Exception:  # noqa: BLE001
            continue

    return None, "image/png"


@st.cache_data(ttl=300, show_spinner=False)
def load_player_score_rows(player_id: object) -> list[dict]:
    path_id = storage_path_id(player_id)
    if not path_id:
        return []

    try:
        normalized_player_id = int(path_id)
    except ValueError:
        normalized_player_id = path_id

    schema = get_score_schema()

    for table in SCORE_TABLES:
        try:
            if get_database_url():
                rows = fetch_rows_from_database(schema, table, SCORE_ID_COLUMN, normalized_player_id)
                if rows:
                    return rows
            else:
                rows = (
                    get_supabase_client()
                    .schema(schema)
                    .table(table)
                    .select("*")
                    .eq(SCORE_ID_COLUMN, normalized_player_id)
                    .execute()
                    .data
                    or []
                )
                if rows:
                    return rows
        except Exception:  # noqa: BLE001
            continue

    return []


def wide_score_categories(score_rows: list[dict]) -> list[dict]:
    categories = []
    for row in score_rows:
        for column, value in row.items():
            if not column.startswith(SCORE_VALUE_PREFIX) or pd.isna(value):
                continue

            suffix = column.removeprefix(SCORE_VALUE_PREFIX)
            percentile = row.get(f"{SCORE_PERCENTILE_PREFIX}{suffix}")
            categories.append(
                {
                    "name": score_category_name(suffix),
                    "score": value,
                    "percentile": percentile,
                }
            )
    return categories


def old_score_categories(score_rows: list[dict]) -> list[dict]:
    grouped: dict[str, list[float]] = {}
    for row in score_rows:
        if pd.isna(row.get("valor")):
            continue

        category = clean_text(row.get("categoria"), "Sem categoria")
        try:
            grouped.setdefault(category, []).append(float(row.get("valor")))
        except (TypeError, ValueError):
            continue

    return [
        {
            "name": category,
            "score": float(np.mean(values)),
            "percentile": None,
        }
        for category, values in sorted(grouped.items(), key=lambda item: item[0])
        if values
    ]


def score_categories(score_rows: list[dict]) -> list[dict]:
    categories = wide_score_categories(score_rows)
    return categories if categories else old_score_categories(score_rows)


def score_cluster_from_rows(score_rows: list[dict], fallback: str = "Sem cluster") -> str:
    values = []
    for row in score_rows:
        values.extend([row.get("persona"), row.get("cluster")])

    return first_valid_text(*values, fallback=fallback)


def score_position_from_rows(score_rows: list[dict], fallback: str = "Sem posicao") -> str:
    return first_valid_text(*(row.get("posicao") for row in score_rows), fallback=fallback)


@st.cache_data(ttl=300, show_spinner=False)
def load_score_profiles_by_player() -> dict[str, dict[str, str]]:
    schema = get_score_schema()
    profiles: dict[str, dict[str, str]] = {}

    for table in SCORE_TABLES:
        try:
            rows = (
                fetch_rows_from_database(schema, table)
                if get_database_url()
                else fetch_rows_from_supabase_api(schema, table)
            )
        except Exception:  # noqa: BLE001
            continue

        for row in rows:
            player_key = storage_path_id(row.get(SCORE_ID_COLUMN))
            if not player_key or player_key in profiles:
                continue

            profiles[player_key] = {
                "cluster": score_cluster_from_rows([row], fallback="Sem cluster"),
                "position": score_position_from_rows([row], fallback="Sem posicao"),
            }

    return profiles


@st.cache_data(ttl=300, show_spinner=False)
def load_player_score_cluster(player_id: object) -> str:
    return score_cluster_from_rows(load_player_score_rows(player_id))


@st.cache_data(ttl=300, show_spinner=False)
def load_player_score_cards(player_id: object) -> list[dict]:
    return [
        {
            "name": category["name"],
            "value": format_score(category.get("score")),
        }
        for category in score_categories(load_player_score_rows(player_id))
    ]


@st.cache_data(ttl=300, show_spinner=False)
def load_player_score_details(player_id: object) -> list[dict]:
    score_rows = load_player_score_rows(player_id)
    if not score_rows:
        return []

    details = []
    first_row = score_rows[0]
    metadata = [
        ("Persona", score_cluster_from_rows(score_rows, fallback="-")),
        ("Minutos jogados", first_row.get("minutos_jogados")),
        ("Ranking percentil", first_row.get("ranking_percentil")),
    ]
    for label, value in metadata:
        if not pd.isna(value):
            details.append({"name": label, "value": format_score(value) if label != "Persona" else clean_text(value)})

    for category in score_categories(score_rows):
        details.append(
            {
                "name": category["name"],
                "value": format_score(category.get("score")),
            }
        )

        percentile = category.get("percentile")
        if not pd.isna(percentile):
            details.append(
                {
                    "name": f"Percentil {category['name']}",
                    "value": format_percentile(percentile),
                }
            )

    if len(details) == 3:
        for row in score_rows:
            for column, value in row.items():
                if column in SCORE_METADATA_COLUMNS or pd.isna(value):
                    continue
                details.append(
                    {
                        "name": humanize_key(column),
                        "value": format_score(value),
                    }
                )

    return details[:12]


def score_table_html(score_rows: list[dict], categories: list[dict]) -> str:
    first_row = score_rows[0] if score_rows else {}
    ranking = format_rank(first_row.get("ranking_percentil"))
    rows_html = []

    for category in categories:
        rows_html.append(
            "<tr>"
            f"<td>{html.escape(category['name'])}</td>"
            f"<td>{html.escape(format_score(category.get('score')))}</td>"
            f"<td>{html.escape(format_percentile(category.get('percentile')))}</td>"
            "</tr>"
        )

    if not rows_html:
        rows_html.append(
            "<tr>"
            "<td>Sem categoria</td>"
            "<td>-</td>"
            "<td>-</td>"
            "</tr>"
        )

    return (
        '<section class="score-support-panel">'
        '<div class="ranking-card">'
        '<div class="ranking-label">Posicao no ranking</div>'
        f'<div class="ranking-value">{html.escape(ranking)}</div>'
        "</div>"
        '<table class="score-support-table">'
        "<thead><tr><th>Categoria</th><th>Score bruto</th><th>Percentil</th></tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody>"
        "</table>"
        "</section>"
    )


def score_radar_figure(categories: list[dict], player_name: str, cluster_value: str) -> go.Figure:
    labels = []
    values = []
    for category in categories:
        percentile = category.get("percentile")
        if pd.isna(percentile):
            continue

        try:
            percentile_number = float(percentile)
        except (TypeError, ValueError):
            continue

        labels.append(category["name"])
        values.append(max(0, min(100, percentile_number)))

    if labels and values:
        labels = [*labels, labels[0]]
        values = [*values, values[0]]

    figure = go.Figure()
    figure.add_trace(
        go.Scatterpolar(
            r=values,
            theta=labels,
            fill="toself",
            fillcolor="rgba(34, 197, 94, 0.26)",
            line={"color": "#22c55e", "width": 3},
            marker={"color": "#facc15", "size": 8, "line": {"color": "#0f172a", "width": 1}},
            hovertemplate="%{theta}<br>Percentil %{r:.1f}%<extra></extra>",
            name="Percentil",
        )
    )
    figure.update_layout(
        height=430,
        margin={"l": 34, "r": 34, "t": 64, "b": 28},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        title={
            "text": f"{html.escape(player_name)}<br><sup>{html.escape(cluster_value)}</sup>",
            "x": 0.5,
            "xanchor": "center",
            "font": {"color": "#f8fafc", "size": 22},
        },
        polar={
            "bgcolor": "rgba(2, 6, 23, 0.18)",
            "radialaxis": {
                "range": [0, 100],
                "tickvals": [20, 40, 60, 80, 100],
                "tickfont": {"color": "rgba(226, 232, 240, 0.62)", "size": 10},
                "gridcolor": "rgba(255, 255, 255, 0.16)",
                "linecolor": "rgba(255, 255, 255, 0.16)",
            },
            "angularaxis": {
                "tickfont": {"color": "#f8fafc", "size": 12},
                "gridcolor": "rgba(255, 255, 255, 0.12)",
                "linecolor": "rgba(255, 255, 255, 0.18)",
            },
        },
    )
    return figure


def render_score_profile_section(player_id: object, player_name: str, cluster_value: str) -> None:
    score_rows = load_player_score_rows(player_id)
    categories = score_categories(score_rows)
    radar_categories = [category for category in categories if not pd.isna(category.get("percentile"))]

    st.markdown(
        """
        <section class="score-style-section">
            <div class="score-style-heading">
                <div>
                    <div class="player-kicker">Estilo de jogo</div>
                    <h2 class="section-title">Radar de percentis</h2>
                </div>
                <p class="section-note">Percentis por categoria de score; apoio lateral com valores brutos</p>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if not score_rows or not radar_categories:
        st.warning("Nao encontrei percentis de score para desenhar o radar desse jogador.")
        return

    radar_column, table_column = st.columns([1.85, 1], gap="small")
    with radar_column:
        st.plotly_chart(
            score_radar_figure(categories, player_name, cluster_value),
            use_container_width=True,
            config={"displayModeBar": False, "responsive": True},
        )

    with table_column:
        st.markdown(score_table_html(score_rows, categories), unsafe_allow_html=True)


def numeric_columns_for_player(df: pd.DataFrame, excluded: set[str]) -> list[str]:
    numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()
    return [
        column
        for column in numeric_columns
        if column not in excluded and not column.lower().endswith("_id") and column.lower() != "id"
    ]


def normalize_search_text(value: object) -> str:
    if pd.isna(value):
        return ""

    text = str(value).strip().lower()
    return "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )


def default_team_index(teams: list[str]) -> int | None:
    if not teams:
        return None

    normalized_aliases = {normalize_search_text(alias) for alias in DEFAULT_TEAM_ALIASES}
    for index, team in enumerate(teams):
        if team in DEFAULT_TEAM_ALIASES or normalize_search_text(team) in normalized_aliases:
            return index

    for index, team in enumerate(teams):
        normalized_team = normalize_search_text(team)
        if "mineiro" in normalized_team and "u20" in normalized_team and normalized_team.startswith("am"):
            return index

    return 0


def function_label_from_position(value: object) -> str:
    text = normalize_search_text(value)

    if any(keyword in text for keyword in ("goleiro", "goalkeeper")):
        return "Goleiro"

    if any(keyword in text for keyword in ("lateral", "ala", "fullback", "wingback")):
        return "Lateral"

    if any(keyword in text for keyword in ("zagueiro", "defensor", "defesa", "centre-back", "center-back")):
        return "Defensor"

    if any(keyword in text for keyword in ("meia", "meio", "volante", "midfielder")):
        return "Meia"

    if any(keyword in text for keyword in ("atacante", "ataque", "ponta", "centroavante", "forward", "winger", "striker")):
        return "Atacante"

    return "Outras funções"


def player_position_text(row: pd.Series, position_column: str | None) -> str:
    values = [
        row[position_column]
        if position_column and position_column in row.index
        else None,
        row["posicao_principal_detalhada"] if "posicao_principal_detalhada" in row.index else None,
        row["posicao_principal"] if "posicao_principal" in row.index else None,
        row["posicao_jogador"] if "posicao_jogador" in row.index else None,
        row["posicao"] if "posicao" in row.index else None,
    ]
    return first_valid_text(*values, fallback="Funcao nao informada")


def prepare_function_profile_data(
    data: pd.DataFrame,
    position_column: str | None,
) -> pd.DataFrame:
    source = data.copy()
    score_profiles = load_score_profiles_by_player()
    if SCORE_ID_COLUMN in source.columns and score_profiles:
        source = source[
            source[SCORE_ID_COLUMN].map(lambda value: (storage_path_id(value) or "") in score_profiles)
        ].copy()
        source["_score_position_text"] = source[SCORE_ID_COLUMN].map(
            lambda value: score_profiles.get(storage_path_id(value) or "", {}).get("position", "Sem posicao")
        )
    else:
        source["_score_position_text"] = "Sem posicao"

    source["_position_text"] = source.apply(
        lambda row: first_valid_text(
            row["_score_position_text"],
            player_position_text(row, position_column),
            fallback="Funcao nao informada",
        ),
        axis=1,
    )
    source["_function_label"] = source["_position_text"].map(function_label_from_position)
    if SCORE_ID_COLUMN in source.columns:
        source["_cluster_text"] = source[SCORE_ID_COLUMN].map(
            lambda value: score_profiles.get(storage_path_id(value) or "", {}).get("cluster", "Sem cluster")
        )
    else:
        source["_cluster_text"] = "Sem cluster"
    return source


def sorted_function_labels(values: Iterable[str]) -> list[str]:
    order = {name: index for index, name in enumerate(FUNCTION_ORDER)}
    return sorted(values, key=lambda value: (order.get(value, 999), value))


def key_fragment(value: object) -> str:
    text = normalize_search_text(value)
    return "".join(char if char.isalnum() else "_" for char in text).strip("_") or "item"


def render_score_cards(score_cards: list[dict]) -> str:
    if not score_cards:
        return ""

    cards_html = []
    for card in score_cards:
        cards_html.append(
            '<article class="score-card">'
            '<div class="score-row">'
            f'<div class="score-name">{html.escape(card["name"])}</div>'
            f'<div class="score-value">{html.escape(card["value"])}</div>'
            "</div>"
            "</article>"
        )

    return (
        '<section class="player-score-shell">'
        '<div class="section-header">'
        "<div>"
        '<div class="player-kicker">Scores do jogador</div>'
        '<h2 class="section-title">Categorias de score</h2>'
        "</div>"
        '<p class="section-note">Fonte: fact.scores_players</p>'
        "</div>"
        f'<div class="score-grid">{"".join(cards_html)}</div>'
        "</section>"
    )


def render_player_score_content(
    player_info: dict,
) -> None:
    player_name = clean_text(player_info.get("name"), "Jogador")
    team_name = clean_text(player_info.get("team"), "Time nao informado")
    player_position = clean_text(player_info.get("position"), "Funcao nao informada")
    cluster_value = clean_text(player_info.get("cluster"), "-")
    height_value = clean_text(player_info.get("height"), "-")
    age_value = clean_text(player_info.get("age"), "-")
    foot_value = clean_text(player_info.get("foot"), "-")
    player_id = player_info.get("player_id")
    player_photo, player_photo_mime = load_player_photo(player_id)
    player_photo_uri = image_data_uri(player_photo, player_photo_mime)
    player_photo_html = (
        f'<img src="{player_photo_uri}" alt="Foto {html.escape(player_name)}">'
        if player_photo_uri
        else '<div class="player-photo-placeholder">Foto indisponivel</div>'
    )
    quick_facts = [
        ("Idade", age_value),
        ("Altura", height_value),
        ("Pe preferido", foot_value),
    ]
    quick_facts_html = "".join(
        '<div class="dialog-bio-card">'
        f'<div class="dialog-bio-label">{html.escape(label)}</div>'
        f'<div class="dialog-bio-value">{html.escape(value)}</div>'
        "</div>"
        for label, value in quick_facts
    )

    score_details = load_player_score_details(player_id)
    score_details_html = "".join(
        '<div class="dialog-bio-card">'
        f'<div class="dialog-bio-label">{html.escape(detail["name"])}</div>'
        f'<div class="dialog-bio-value">{html.escape(detail["value"])}</div>'
        "</div>"
        for detail in score_details
    )
    if not score_details_html:
        score_details_html = (
            '<div class="dialog-bio-card">'
            '<div class="dialog-bio-label">Scores</div>'
            '<div class="dialog-bio-value">-</div>'
            "</div>"
        )

    st.markdown(
        f"""
        <section class="dialog-player-card">
            <div class="dialog-player-photo">{player_photo_html}</div>
            <div class="dialog-player-meta">
                <div class="player-kicker">Jogador selecionado</div>
                <h1 class="player-name">{html.escape(player_name)}</h1>
                <p class="selected-player-summary">{html.escape(team_name)} | {html.escape(player_position)}</p>
                <div class="dialog-quick-facts">{quick_facts_html}</div>
                <div class="dialog-cluster-highlight">
                    <div class="dialog-cluster-label">Cluster</div>
                    <div class="dialog-cluster-value">{html.escape(cluster_value)}</div>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if player_id is None:
        st.warning("Nao encontrei jogador_id para carregar os scores desse atleta.")
        return

    score_cards = load_player_score_cards(player_id)
    score_html = render_score_cards(score_cards)
    if score_html:
        st.markdown(score_html, unsafe_allow_html=True)
    else:
        st.warning("Nao encontrei scores em fact.scores_players para esse jogador.")

    st.markdown(
        f"""
        <section class="dialog-bio-shell">
            <div class="dialog-raw-title">
                <div class="player-kicker">Scores</div>
                <p class="section-note">Fonte: fact.scores_players</p>
            </div>
            <div class="dialog-bio-grid">{score_details_html}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


if hasattr(st, "dialog"):

    @st.dialog("Scores do jogador", width="large")
    def render_player_score_dialog(
        player_info: dict,
    ) -> None:
        render_player_score_content(player_info)

else:

    def render_player_score_dialog(
        player_info: dict,
    ) -> None:
        render_player_score_content(player_info)


def render_selected_cluster_players(
    selected_rows: pd.DataFrame,
    selected_function: str,
    selected_cluster_name: str,
    team_column: str,
    player_column: str,
) -> None:
    title_column, close_column = st.columns([0.96, 0.04], gap="small")
    with title_column:
        st.markdown(
            f"""
            <section class="selected-cluster">
                <div class="player-kicker">Cluster selecionado</div>
                <div class="player-list-title">{html.escape(selected_function)} | {html.escape(selected_cluster_name)}</div>
            </section>
            """,
            unsafe_allow_html=True,
        )
    with close_column:
        if st.button("X", key=f"close_cluster_{key_fragment(selected_function)}", help="Fechar cluster"):
            st.session_state.pop("perfil_funcao_cluster", None)
            return

    if selected_rows.empty:
        st.warning("Nao encontrei jogadores para esse cluster.")
        return

    display_rows = selected_rows.copy()
    display_rows["_player_name"] = display_rows[player_column].map(lambda value: clean_text(value))
    display_rows["_team_name"] = display_rows[team_column].map(lambda value: clean_text(value))
    display_rows = display_rows.sort_values(["_team_name", "_player_name"])

    st.markdown('<div class="cluster-player-row">', unsafe_allow_html=True)
    player_columns = st.columns(2, gap="small")
    for button_index, (row_index, row) in enumerate(display_rows.iterrows()):
        player_name = row_value(row, player_column)
        team_name = row_value(row, team_column)
        with player_columns[button_index % len(player_columns)]:
            if st.button(
                f"{player_name} | {team_name}",
                key=(
                    "player_"
                    f"{key_fragment(selected_function)}_"
                    f"{key_fragment(selected_cluster_name)}_"
                    f"{row_index}"
                ),
            ):
                selected_position = clean_text(row["_position_text"], "Funcao nao informada")
                selected_player_id = row[SCORE_ID_COLUMN] if SCORE_ID_COLUMN in row.index else None
                player_info = {
                    "name": player_name,
                    "team": team_name,
                    "position": selected_position,
                    "player_id": selected_player_id,
                    "height": format_height(row["altura_cm"]) if "altura_cm" in row.index else "-",
                    "age": calculate_age(row["data_nascimento"]) if "data_nascimento" in row.index else "-",
                    "foot": row_value(row, "pe_preferido"),
                    "country": row_value(row, "pais"),
                    "contract": format_date(row["contrato_ate"]) if "contrato_ate" in row.index else "-",
                    "birth_date": format_date(row["data_nascimento"]) if "data_nascimento" in row.index else "-",
                    "cluster": clean_text(row["_cluster_text"], "-"),
                }
                render_player_score_dialog(player_info)
    st.markdown("</div>", unsafe_allow_html=True)


def render_function_profile_page(
    data: pd.DataFrame,
    team_column: str,
    player_column: str,
    position_column: str | None,
) -> None:
    source = prepare_function_profile_data(data, position_column)

    st.markdown(
        """
        <section class="team-hero">
            <div class="team-crest"></div>
            <div>
                <div class="eyebrow">Pagina 2</div>
                <div class="main-title">Perfil por Função</div>
                <p class="subtitle">Clusters por posicao, atletas e scores tecnicos por categoria</p>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    available_functions = sorted_function_labels(source["_function_label"].dropna().unique())
    if not available_functions:
        st.warning("Nao encontrei posicoes para montar os clusters por funcao.")
        return

    for function_label in available_functions:
        function_data = source[source["_function_label"] == function_label].copy()
        clusters = normalized_options(function_data["_cluster_text"])
        if not clusters:
            continue

        st.markdown(
            f"""
            <section class="function-section">
                <div class="function-header">
                    <div class="function-title">{html.escape(function_label)}</div>
                    <div class="function-count">{len(function_data)} atletas | {len(clusters)} clusters</div>
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="cluster-button-row">', unsafe_allow_html=True)
        button_columns = st.columns(min(4, max(1, len(clusters))), gap="small")
        for index, cluster in enumerate(clusters):
            with button_columns[index % len(button_columns)]:
                if st.button(
                    cluster,
                    key=f"cluster_{key_fragment(function_label)}_{key_fragment(cluster)}_{index}",
                    type="primary",
                ):
                    st.session_state["perfil_funcao_cluster"] = {
                        "function": function_label,
                        "cluster": cluster,
                    }
        st.markdown("</div>", unsafe_allow_html=True)

        selected_cluster = st.session_state.get("perfil_funcao_cluster")
        if selected_cluster and selected_cluster["function"] == function_label:
            selected_cluster_name = selected_cluster["cluster"]
            selected_rows = function_data[
                function_data["_cluster_text"] == selected_cluster_name
            ].copy()
            render_selected_cluster_players(
                selected_rows,
                function_label,
                selected_cluster_name,
                team_column,
                player_column,
            )

    if not st.session_state.get("perfil_funcao_cluster"):
        st.info("Selecione um cluster para ver os jogadores.")


st.markdown(load_background_css(), unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="nav-title">Paginas</div>', unsafe_allow_html=True)
    selected_page = st.radio("Navegacao", APP_PAGES, label_visibility="collapsed")

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
position_column = get_env_value("SUPABASE_POSITION_COLUMN") or first_existing_column(
    data.columns,
    POSITION_COLUMN_CANDIDATES,
)

if not team_column or team_column not in data.columns:
    st.error("Não encontrei a coluna do time. Defina SUPABASE_TEAM_COLUMN no .env.")
    st.stop()

if not player_column or player_column not in data.columns:
    st.error("Não encontrei a coluna do jogador. Defina SUPABASE_PLAYER_COLUMN no .env.")
    st.stop()

if SCORE_ID_COLUMN not in data.columns:
    st.error("Nao encontrei a coluna jogador_id para relacionar bio e scores.")
    st.stop()

if selected_page == PAGE_PERFIL_FUNCAO:
    render_function_profile_page(data, team_column, player_column, position_column)
    st.stop()

score_profiles = load_score_profiles_by_player()
score_player_ids = set(score_profiles)
score_data = data[
    data[SCORE_ID_COLUMN].map(lambda value: (storage_path_id(value) or "") in score_player_ids)
].copy()
profile_data = score_data if not score_data.empty else data
teams = normalized_options(profile_data[team_column])

st.markdown('<div class="filter-heading">Selecao</div>', unsafe_allow_html=True)
team_filter, position_filter, player_filter = st.columns([1.05, 1.05, 1.35], gap="small")

with team_filter:
    selected_team = st.selectbox("Clube", teams, index=default_team_index(teams))

team_data = profile_data[profile_data[team_column].astype(str).str.strip() == selected_team].copy()
team_data["_score_position_text"] = team_data[SCORE_ID_COLUMN].map(
    lambda value: score_profiles.get(storage_path_id(value) or "", {}).get("position", "Sem posicao")
)
filtered_data = team_data

with position_filter:
    score_position_data = team_data[team_data["_score_position_text"] != "Sem posicao"]
    position_options = ["Todas as posicoes", *normalized_options(score_position_data["_score_position_text"])]
    if len(position_options) > 1:
        selected_position = st.selectbox("Posicao principal", position_options, index=0)
        if selected_position != "Todas as posicoes":
            filtered_data = team_data[team_data["_score_position_text"] == selected_position].copy()
    else:
        st.selectbox("Posicao principal", ["Todas as posicoes"], index=0, disabled=True)

player_options_data = filtered_data.dropna(subset=[SCORE_ID_COLUMN]).copy()
player_options_data["_player_id_text"] = player_options_data[SCORE_ID_COLUMN].map(storage_path_id)
player_options_data["_player_name_text"] = player_options_data[player_column].map(lambda value: clean_text(value))
player_options_data = player_options_data.dropna(subset=["_player_id_text"])
player_options_data = player_options_data.sort_values("_player_name_text").drop_duplicates("_player_id_text")
player_labels = dict(zip(player_options_data["_player_id_text"], player_options_data["_player_name_text"]))
player_options = list(player_labels.keys())

with player_filter:
    selected_player_id = st.selectbox(
        "Atleta",
        player_options,
        format_func=lambda value: player_labels.get(value, value),
        index=0 if player_options else None,
    )
    selected_player = player_labels.get(selected_player_id, "") if selected_player_id else ""

if not selected_team or not selected_player_id:
    st.warning("Selecione um clube e um atleta.")
    st.stop()

player_rows = filtered_data[
    filtered_data[SCORE_ID_COLUMN].map(storage_path_id) == selected_player_id
].copy()
player_row = player_rows.iloc[0]
excluded_columns = {team_column, player_column}
numeric_columns = numeric_columns_for_player(player_rows, excluded_columns)
team_id = player_row["time_id"] if "time_id" in player_row.index else None
player_id = player_row[SCORE_ID_COLUMN] if SCORE_ID_COLUMN in player_row.index else None
team_logo, team_logo_mime = load_team_logo(team_id)
player_photo, player_photo_mime = load_player_photo(player_id)
team_logo_uri = image_data_uri(team_logo, team_logo_mime)
player_photo_uri = image_data_uri(player_photo, player_photo_mime)
team_logo_html = (
    f'<img src="{team_logo_uri}" alt="Escudo {html.escape(selected_team)}">'
    if team_logo_uri
    else ""
)
player_photo_html = (
    f'<img src="{player_photo_uri}" alt="Foto {html.escape(selected_player)}">'
    if player_photo_uri
    else '<div class="player-photo-placeholder">Foto indisponível</div>'
)
player_position = first_valid_text(
    player_row["_score_position_text"] if "_score_position_text" in player_row.index else None,
    player_row["posicao_principal_detalhada"] if "posicao_principal_detalhada" in player_row.index else None,
    player_row["posicao_jogador"] if "posicao_jogador" in player_row.index else None,
)
player_country = row_value(player_row, "pais")
player_height = format_height(player_row["altura_cm"]) if "altura_cm" in player_row.index else "-"
player_age = calculate_age(player_row["data_nascimento"]) if "data_nascimento" in player_row.index else "-"
player_birth_date = format_date(player_row["data_nascimento"]) if "data_nascimento" in player_row.index else "-"
player_foot = row_value(player_row, "pe_preferido")
player_contract = format_date(player_row["contrato_ate"]) if "contrato_ate" in player_row.index else "-"
cluster_value = load_player_score_cluster(player_id)

st.markdown(
    f"""
    <section class="team-hero">
        <div class="team-crest">{team_logo_html}</div>
        <div>
            <div class="eyebrow">Scout Tecnico Base BR</div>
            <div class="main-title">{html.escape(selected_team)}</div>
            <p class="subtitle">Repertorio, funcao e desempenho acumulado nas competicoes de base</p>
        </div>
    </section>
    <section>
        <div class="player-kicker">Relatorio tecnico</div>
        <h1 class="player-name">{html.escape(selected_player)}</h1>
        <p class="player-position">{html.escape(player_position)}</p>
    </section>
    <section class="player-board">
        <div class="player-photo">{player_photo_html}</div>
        <div class="bio-grid">
            <div class="bio-card">
                <div class="bio-label">Idade</div>
                <div class="bio-value">{html.escape(player_age)}</div>
            </div>
            <div class="bio-card">
                <div class="bio-label">Nascimento</div>
                <div class="bio-value">{html.escape(player_birth_date)}</div>
            </div>
            <div class="bio-card">
                <div class="bio-label">País</div>
                <div class="bio-value">{html.escape(player_country)}</div>
            </div>
            <div class="bio-card">
                <div class="bio-label">Pé preferido</div>
                <div class="bio-value">{html.escape(player_foot)}</div>
            </div>
            <div class="bio-card">
                <div class="bio-label">Altura</div>
                <div class="bio-value">{html.escape(player_height)}</div>
            </div>
            <div class="bio-card">
                <div class="bio-label">Contrato até</div>
                <div class="bio-value">{html.escape(player_contract)}</div>
            </div>
        </div>
        <div class="cluster-panel">
            <div class="cluster-label">Funcao tecnica</div>
            <div class="cluster-value">{html.escape(cluster_value)}</div>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

render_score_profile_section(player_id, selected_player, cluster_value)
