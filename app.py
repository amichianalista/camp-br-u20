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
RAW_METRIC_TABLES_BY_SCORE_TABLE = {
    table: table.replace("fact.scores_players", "fact.raw_metrics_players")
    for table in SCORE_TABLES
}
SCORE_ID_COLUMN = "jogador_id"
SCORE_VALUE_PREFIX = "pontuacao_"
SCORE_PERCENTILE_PREFIX = "percentil_"
SCORE_PERCENTILE_ID_PREFIX = "score_percentil_id_"
SCORE_METADATA_COLUMNS = {
    "jogador_id",
    "posicao",
    "minutos_jogados",
    "persona",
    "ranking_percentil",
}
RAW_METRIC_METADATA_COLUMNS = {
    "jogador_id",
    "minutos_jogados",
    "posicao",
}
RAW_METRIC_GROUPS_BY_TABLE = {
    "fact.raw_metrics_players.atacantes": {
        "finalizacao": [
            "gols",
            "finalizacoes",
            "finalizacoes_no_alvo",
            "finalizacoes_fora",
            "finalizacoes_bloqueadas",
            "grandes_chances_perdidas",
            "percentual_conversao_gols",
            "gols_cabeca",
        ],
        "presenca_area": [
            "duelos_aereos_ganhos",
            "percentual_duelos_aereos_ganhos",
            "impedimentos",
        ],
        "criacao_apoio": [
            "assistencias",
            "passes_certos_terco_final",
            "passes_chave",
            "cruzamentos_certos",
            "faltas_sofridas",
        ],
        "quebrar_linhas": [
            "dribles_certos",
            "percentual_dribles_certos",
        ],
    },
    "fact.raw_metrics_players.defensores": {
        "qualidade_defensiva": [
            "cortes",
            "interceptacoes",
            "bloqueios_jogador_linha",
            "duelos_chao_ganhos",
            "duelos_totais_ganhos",
            "vezes_driblado",
            "faltas_cometidas",
            "erros_levaram_finalizacao",
            "penaltis_cometidos",
        ],
        "qualidade_aerea": [
            "duelos_aereos_ganhos",
            "percentual_duelos_aereos_ganhos",
            "gols_cabeca",
        ],
        "saida_de_bola": [
            "passes_certos",
            "passes_errados",
            "bolas_longas_certas",
            "passes_certos_campo_defesa",
            "desarmes_sofridos",
            "posses_perdidas",
        ],
    },
    "fact.raw_metrics_players.goleiros": {
        "qualidade_defesa": [
            "defesas",
            "jogos_sem_sofrer_gol",
            "finalizacoes_bloqueadas",
            "erros_levaram_finalizacao",
        ],
        "saida_de_jogo": [
            "passes_certos",
            "passes_errados",
            "bolas_longas_certas",
            "cortes",
            "duelos_totais_ganhos",
        ],
        "saida_aerea": [
            "cruzamentos_nao_agarrados",
            "duelos_aereos_ganhos",
            "percentual_duelos_aereos_ganhos",
        ],
    },
    "fact.raw_metrics_players.laterais": {
        "qualidade_defensiva": [
            "finalizacoes_bloqueadas",
            "cortes",
            "erros_levaram_finalizacao",
            "duelos_totais_ganhos",
            "vezes_driblado",
            "desarmes",
            "interceptacoes",
            "faltas_cometidas",
            "gols_sofridos_dentro_area",
        ],
        "apoio_construcao": [
            "passes_certos",
            "passes_errados",
            "bolas_longas_certas",
            "passes_certos_campo_defesa",
            "passes_certos_campo_ataque",
            "desarmes_sofridos",
            "posses_perdidas",
        ],
        "criacao_ofensiva": [
            "dribles_certos",
            "grandes_chances_criadas",
            "assistencias",
            "passes_certos_terco_final",
            "passes_chave",
            "cruzamentos_certos",
            "passes_para_assistencia",
        ],
        "finalizacao": [
            "gols",
            "finalizacoes",
            "penaltis_cobrados",
            "gols_pe_esquerdo",
            "gols_pe_direito",
            "impedimentos",
        ],
    },
    "fact.raw_metrics_players.meias": {
        "qualidade_defensiva": [
            "finalizacoes_bloqueadas",
            "cortes",
            "erros_levaram_finalizacao",
            "jogos_sem_sofrer_gol",
            "duelos_totais_ganhos",
            "duelos_aereos_ganhos",
            "percentual_duelos_totais_ganhos",
            "percentual_duelos_aereos_ganhos",
            "vezes_driblado",
            "faltas_cometidas",
            "bloqueios_jogador_linha",
        ],
        "construcao_jogo": [
            "passes_certos",
            "passes_errados",
            "bolas_longas_certas",
        ],
        "criacao": [
            "dribles_certos",
            "assistencias",
            "passes_certos_terco_final",
            "passes_chave",
            "passes_para_assistencia",
        ],
        "chegada_area": [
            "gols",
            "finalizacoes",
            "finalizacoes_no_alvo",
            "impedimentos",
        ],
    },
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


CLUSTER_DESCRIPTIONS = {
    ("goleiro", "goleiro paredao"): (
        "O goleiro completo. Destaca-se pela seguranca embaixo das traves, "
        "excelente tempo de saida aerea e otima reposicao de jogo."
    ),
    ("goleiro", "goleiro construtor"): (
        'O "11o jogador". Especialista em iniciar as jogadas, com o maior '
        "indice de participacao e qualidade na saida de bola com os pes."
    ),
    ("goleiro", "paredao aereo"): (
        "Dono da grande area. Domina o jogo aereo e mantem um nivel "
        "intermediario e seguro nas defesas e saidas de jogo."
    ),
    ("goleiro", "goleiro comum"): (
        "Perfil regular e sem picos tecnicos evidentes, apresentando maior "
        "dificuldade em cruzamentos e saidas aereas."
    ),
    ("defensor", "zagueiro completo"): (
        "Seguranca total. Une alta eficiencia nos desarmes, dominio nas "
        "disputas aereas e qualidade para comecar o jogo."
    ),
    ("defensor", "zagueiro construtor"): (
        "O motor da saida de tres. Lider absoluto em passes verticais e "
        "construcao de jogadas desde o campo de defesa."
    ),
    ("defensor", "zagueiro comum"): (
        "Perfil de composicao. Atua de forma mais discreta e regular, com "
        "menor destaque relativo nos fundamentos defensivos e de passe."
    ),
    ("lateral", "ala ofensivo"): (
        "Apoio constante. Combina criacao no ultimo terco do campo, suporte "
        "na transicao e bom equilibrio defensivo."
    ),
    ("lateral", "lateral construtor"): (
        "O articulador lateral. Atua quase como um meio-campista, liderando "
        "o volume de passes e a sustentacao do jogo."
    ),
    ("lateral", "lateral defensivo"): (
        'O "lateral-base". Foco total na consistencia defensiva, sendo o '
        "perfil mais dificil de ser batido no 1 contra 1."
    ),
    ("lateral", "lateral comum"): (
        "Perfil conservador. Menor participacao no apoio ofensivo e numeros "
        "discretos na fase de marcacao."
    ),
}


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

        .function-hero {{
            align-items: center;
            background: linear-gradient(135deg, rgba(8, 16, 22, 0.90), rgba(8, 16, 22, 0.58));
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 8px;
            box-shadow: 0 18px 54px rgba(0, 0, 0, 0.34);
            display: flex;
            justify-content: center;
            margin-bottom: 0.75rem;
            margin-top: 0.25rem;
            min-height: 138px;
            overflow: hidden;
            padding: 1.2rem;
            position: relative;
            text-align: center;
        }}

        .function-hero::before {{
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
            margin-bottom: 0.65rem;
        }}

        .ranking-heading {{
            align-items: baseline;
            display: flex;
            gap: 0.65rem;
        }}

        .ranking-heading-label {{
            color: rgba(203, 213, 225, 0.72);
            font-size: 0.82rem;
            font-weight: 900;
            text-transform: uppercase;
        }}

        .ranking-heading-value {{
            color: #f8fafc;
            font-size: clamp(1.85rem, 3.2vw, 2.65rem);
            font-weight: 900;
            line-height: 1;
        }}

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

        .score-support-panel::before {{
            background: linear-gradient(90deg, #22c55e, #facc15, #38bdf8);
            content: "";
            height: 3px;
            left: 0;
            position: absolute;
            right: 0;
            top: 0;
        }}

        div[data-testid="stPlotlyChart"] {{
            background:
                linear-gradient(145deg, rgba(8, 16, 22, 0.94), rgba(7, 13, 18, 0.74));
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 8px;
            box-shadow: 0 16px 38px rgba(0, 0, 0, 0.26);
            margin: 0 auto;
            max-width: 640px;
            min-height: 365px;
            overflow: hidden;
            padding: 0.5rem;
        }}

        .score-support-panel {{
            margin-top: 0.72rem;
            padding: 0.88rem;
        }}

        .score-support-strip {{
            display: grid;
            gap: 0.62rem;
            grid-template-columns: repeat(auto-fit, minmax(185px, 1fr));
        }}

        .score-support-card {{
            background: rgba(255, 255, 255, 0.055);
            border: 1px solid rgba(255, 255, 255, 0.09);
            border-radius: 8px;
            display: grid;
            gap: 0.72rem;
            grid-template-columns: minmax(0, 1fr);
            min-height: 112px;
            padding: 0.7rem;
        }}

        .score-support-category {{
            color: rgba(226, 232, 240, 0.88);
            font-size: 0.82rem;
            font-weight: 900;
            line-height: 1.12;
        }}

        .score-support-metrics {{
            display: grid;
            gap: 0.45rem;
            grid-template-columns: minmax(0, 1fr);
        }}

        .score-support-label {{
            color: rgba(203, 213, 225, 0.66);
            font-size: 0.58rem;
            font-weight: 900;
            text-transform: uppercase;
        }}

        .score-support-value {{
            color: #ffffff;
            font-size: clamp(1.55rem, 2.2vw, 2.15rem);
            font-weight: 900;
            line-height: 0.98;
            text-shadow: 0 10px 24px rgba(34, 197, 94, 0.22);
        }}

        .raw-metrics-panel {{
            background:
                radial-gradient(circle at 82% 10%, rgba(56, 189, 248, 0.12), transparent 18rem),
                linear-gradient(145deg, rgba(8, 16, 22, 0.95), rgba(7, 13, 18, 0.76));
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 8px;
            box-shadow: 0 16px 38px rgba(0, 0, 0, 0.22);
            margin-top: 0.72rem;
            overflow: hidden;
            padding: 1.2rem;
            position: relative;
        }}

        .raw-metrics-panel::before {{
            background: linear-gradient(90deg, #22c55e, #facc15, #38bdf8);
            content: "";
            height: 3px;
            left: 0;
            position: absolute;
            right: 0;
            top: 0;
        }}

        .raw-metrics-heading {{
            align-items: flex-start;
            display: flex;
            gap: 0.6rem;
            justify-content: space-between;
            margin-bottom: 1rem;
        }}

        .raw-metrics-title {{
            color: #f8fafc;
            font-size: clamp(1.65rem, 3.6vw, 3rem);
            font-weight: 900;
            line-height: 1;
            margin: 0;
        }}

        .raw-metrics-subtitle {{
            color: rgba(226, 232, 240, 0.64);
            font-size: 0.82rem;
            font-weight: 700;
            margin-top: 0.35rem;
        }}

        .raw-metrics-position {{
            background: rgba(34, 197, 94, 0.11);
            border: 1px solid rgba(34, 197, 94, 0.26);
            border-radius: 999px;
            color: rgba(34, 197, 94, 0.95);
            font-size: 0.72rem;
            font-weight: 900;
            padding: 0.32rem 0.56rem;
            text-transform: uppercase;
            white-space: nowrap;
        }}

        .raw-score-group-grid {{
            display: grid;
            gap: 0.72rem;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        }}

        .raw-score-group {{
            background:
                linear-gradient(160deg, rgba(15, 23, 42, 0.84), rgba(6, 13, 18, 0.66));
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 8px;
            min-height: 156px;
            overflow: hidden;
            padding: 0.78rem;
            position: relative;
        }}

        .raw-score-group::before {{
            background: linear-gradient(180deg, #22c55e, #facc15, #38bdf8);
            bottom: 0.8rem;
            content: "";
            left: 0;
            position: absolute;
            top: 0.8rem;
            width: 3px;
        }}

        .raw-score-header {{
            align-items: flex-start;
            display: flex;
            gap: 0.7rem;
            justify-content: space-between;
            margin-bottom: 0.72rem;
            padding-left: 0.18rem;
        }}

        .raw-score-kicker {{
            color: rgba(34, 197, 94, 0.88);
            font-size: 0.58rem;
            font-weight: 900;
            margin-bottom: 0.2rem;
            text-transform: uppercase;
        }}

        .raw-score-name {{
            color: #f8fafc;
            font-size: 1rem;
            font-weight: 900;
            line-height: 1.08;
            margin: 0;
        }}

        .raw-score-percentile {{
            background: rgba(250, 204, 21, 0.10);
            border: 1px solid rgba(250, 204, 21, 0.24);
            border-radius: 999px;
            color: #fde68a;
            font-size: 0.78rem;
            font-weight: 900;
            padding: 0.28rem 0.5rem;
            white-space: nowrap;
        }}

        .raw-score-metrics {{
            display: grid;
            gap: 0.42rem;
        }}

        .raw-score-metric-row {{
            align-items: center;
            background: rgba(255, 255, 255, 0.052);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            display: grid;
            gap: 0.52rem;
            grid-template-columns: minmax(0, 1fr) auto;
            min-height: 42px;
            padding: 0.46rem 0.54rem;
        }}

        .raw-metric-label {{
            color: rgba(203, 213, 225, 0.68);
            font-size: 0.68rem;
            font-weight: 900;
            line-height: 1.12;
            text-transform: uppercase;
        }}

        .raw-metric-value {{
            color: #f8fafc;
            font-size: 0.96rem;
            font-weight: 900;
            line-height: 1;
            white-space: nowrap;
        }}

        .raw-score-empty {{
            color: rgba(226, 232, 240, 0.56);
            font-size: 0.78rem;
            font-weight: 800;
            padding: 0.35rem 0.2rem 0;
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
            box-sizing: border-box;
            margin-top: 0.1rem;
            margin-bottom: 0.05rem;
            min-height: 104px;
            padding: 1.02rem 3.4rem 1rem 0.8rem;
            position: relative;
            width: calc(100% + 3.1rem);
        }}

        .cluster-close-anchor {{
            height: 0;
            width: 0;
        }}

        .cluster-close-visual {{
            align-items: center;
            background: transparent;
            border: 1px solid rgba(255, 255, 255, 0.20);
            border-radius: 999px;
            color: #f8fafc;
            display: flex;
            font-size: 1rem;
            font-weight: 800;
            height: 2rem;
            justify-content: center;
            position: absolute;
            right: 0.75rem;
            top: 0.75rem;
            width: 2rem;
        }}

        div[data-testid="column"]:has(.cluster-close-anchor) {{
            position: relative;
            z-index: 5;
        }}

        div[data-testid="column"]:has(.cluster-close-anchor) div[data-testid="stButton"] {{
            position: relative;
            transform: translate(-2.35rem, 0.88rem);
            width: 2rem;
        }}

        div[data-testid="column"]:has(.cluster-close-anchor) div[data-testid="stButton"] > button {{
            background: transparent !important;
            border-color: transparent !important;
            border-radius: 999px;
            box-shadow: none;
            color: transparent !important;
            font-size: 1rem;
            font-weight: 800;
            height: 2rem;
            min-height: 2rem;
            opacity: 0;
            padding: 0;
            width: 2rem !important;
        }}

        div[data-testid="column"]:has(.cluster-close-anchor) div[data-testid="stButton"] > button:hover {{
            background: transparent !important;
            border-color: transparent !important;
            color: transparent !important;
            opacity: 0;
            transform: none;
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

        .cluster-description {{
            color: rgba(226, 232, 240, 0.72);
            font-size: 0.84rem;
            font-weight: 700;
            line-height: 1.35;
            margin: 0.5rem 0 0 0;
            max-width: 860px;
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
            grid-template-columns: repeat(4, minmax(0, 1fr));
            margin-top: 0.4rem;
            max-width: 820px;
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

            .raw-metrics-heading {{
                align-items: flex-start;
                flex-direction: column;
            }}

            .raw-score-group-grid {{
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


def is_internal_id_field(column: str) -> bool:
    normalized = column.strip().lower()
    parts = [part for part in normalized.split("_") if part]
    return "id" in parts


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


def normalized_player_id_for_query(player_id: object) -> object | None:
    path_id = storage_path_id(player_id)
    if not path_id:
        return None

    try:
        return int(path_id)
    except ValueError:
        return path_id


def fetch_player_rows_from_table(schema: str, table: str, player_id: object) -> list[dict]:
    normalized_player_id = normalized_player_id_for_query(player_id)
    if normalized_player_id is None:
        return []

    if get_database_url():
        return fetch_rows_from_database(schema, table, SCORE_ID_COLUMN, normalized_player_id)

    return (
        get_supabase_client()
        .schema(schema)
        .table(table)
        .select("*")
        .eq(SCORE_ID_COLUMN, normalized_player_id)
        .execute()
        .data
        or []
    )


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
def load_player_score_rows_with_table(player_id: object) -> tuple[list[dict], str | None]:
    schema = get_score_schema()

    for table in SCORE_TABLES:
        try:
            rows = fetch_player_rows_from_table(schema, table, player_id)
            if rows:
                return rows, table
        except Exception:  # noqa: BLE001
            continue

    return [], None


@st.cache_data(ttl=300, show_spinner=False)
def load_player_score_rows(player_id: object) -> list[dict]:
    rows, _table = load_player_score_rows_with_table(player_id)
    return rows


def wide_score_categories(score_rows: list[dict]) -> list[dict]:
    categories = []
    for row in score_rows:
        for column, value in row.items():
            if not column.startswith(SCORE_VALUE_PREFIX) or pd.isna(value):
                continue

            suffix = column.removeprefix(SCORE_VALUE_PREFIX)
            if is_internal_id_field(suffix):
                continue

            percentile = row.get(f"{SCORE_PERCENTILE_PREFIX}{suffix}")
            categories.append(
                {
                    "name": score_category_name(suffix),
                    "suffix": suffix,
                    "score": value,
                    "percentile": percentile,
                    "score_id": row.get(f"{SCORE_PERCENTILE_ID_PREFIX}{suffix}"),
                }
            )
    return categories


def old_score_categories(score_rows: list[dict]) -> list[dict]:
    grouped: dict[str, list[float]] = {}
    for row in score_rows:
        if pd.isna(row.get("valor")):
            continue

        raw_category = str(row.get("categoria", "")).strip()
        if is_internal_id_field(raw_category):
            continue

        category = clean_text(row.get("categoria"), "Sem categoria")
        try:
            grouped.setdefault(category, []).append(float(row.get("valor")))
        except (TypeError, ValueError):
            continue

    return [
        {
            "name": category,
            "suffix": None,
            "score": float(np.mean(values)),
            "percentile": None,
            "score_id": None,
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
    for category in score_categories(score_rows):
        percentile = category.get("percentile")
        if not pd.isna(percentile):
            details.append(
                {
                    "name": category["name"],
                    "value": format_percentile(percentile),
                }
            )

    return details[:12]


@st.cache_data(ttl=300, show_spinner=False)
def load_player_raw_metric_rows_from_table(player_id: object, score_table: str | None) -> list[dict]:
    if not score_table:
        return []

    metric_table = RAW_METRIC_TABLES_BY_SCORE_TABLE.get(score_table)
    if not metric_table:
        return []

    try:
        return fetch_player_rows_from_table(get_score_schema(), metric_table, player_id)
    except Exception:  # noqa: BLE001
        return []


@st.cache_data(ttl=300, show_spinner=False)
def load_player_raw_metric_rows(player_id: object) -> list[dict]:
    _score_rows, score_table = load_player_score_rows_with_table(player_id)
    return load_player_raw_metric_rows_from_table(player_id, score_table)


def format_raw_metric_value(value: object) -> str:
    if pd.isna(value):
        return "-"

    try:
        number = float(value)
    except (TypeError, ValueError):
        return clean_text(value)

    if number.is_integer():
        return f"{int(number):,}".replace(",", ".")

    return f"{number:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def score_id_suffix_from_column(column: str) -> str | None:
    if not column.startswith(SCORE_PERCENTILE_ID_PREFIX):
        return None

    suffix = column.removeprefix(SCORE_PERCENTILE_ID_PREFIX).strip()
    return suffix or None


def raw_metric_items(row: dict) -> dict[str, object]:
    items = {}
    for column, value in row.items():
        if column in RAW_METRIC_METADATA_COLUMNS or is_internal_id_field(column) or pd.isna(value):
            continue
        items[column] = value
    return items


def raw_metric_score_suffixes(row: dict, categories: list[dict]) -> list[str]:
    suffixes = []
    for category in categories:
        suffix = category.get("suffix")
        if suffix:
            suffixes.append(str(suffix))

    for column in row:
        suffix = score_id_suffix_from_column(column)
        if suffix:
            suffixes.append(suffix)

    return list(dict.fromkeys(suffixes))


def raw_metric_groups(
    metric_rows: list[dict],
    score_rows: list[dict],
    score_table: str | None,
) -> tuple[str, list[dict]]:
    if not metric_rows:
        return "-", []

    row = metric_rows[0]
    position = clean_text(row.get("posicao"), "Posicao nao informada")
    metric_table = RAW_METRIC_TABLES_BY_SCORE_TABLE.get(score_table or "", "")
    configured_groups = RAW_METRIC_GROUPS_BY_TABLE.get(metric_table, {})
    categories = score_categories(score_rows)
    categories_by_suffix = {
        str(category.get("suffix")): category
        for category in categories
        if category.get("suffix")
    }
    available_metrics = raw_metric_items(row)
    used_metrics = set()
    groups = []

    for suffix in raw_metric_score_suffixes(row, categories):
        metric_columns = [
            column
            for column in configured_groups.get(suffix, [])
            if column in available_metrics
        ]
        if not metric_columns:
            continue

        used_metrics.update(metric_columns)
        category = categories_by_suffix.get(suffix, {})
        score_id = category.get("score_id") or row.get(f"{SCORE_PERCENTILE_ID_PREFIX}{suffix}")
        groups.append(
            {
                "name": category.get("name") or score_category_name(suffix),
                "percentile": category.get("percentile"),
                "score_id": score_id,
                "metrics": [
                    {"name": humanize_key(column), "value": available_metrics[column]}
                    for column in metric_columns
                ],
            }
        )

    remaining_metrics = [
        {"name": humanize_key(column), "value": value}
        for column, value in available_metrics.items()
        if column not in used_metrics
    ]
    if remaining_metrics:
        groups.append(
            {
                "name": "Outras metricas",
                "percentile": None,
                "score_id": None,
                "metrics": remaining_metrics,
            }
        )

    return position, groups


def raw_metric_group_html(group: dict) -> str:
    percentile = format_percentile(group.get("percentile"))
    percentile_html = (
        f'<div class="raw-score-percentile">{html.escape(percentile)}</div>'
        if percentile != "-"
        else ""
    )
    raw_score_id = group.get("score_id")
    score_id = "" if pd.isna(raw_score_id) else str(raw_score_id).strip()
    score_id_attr = f' data-score-id="{html.escape(score_id, quote=True)}"' if score_id else ""
    metrics_html = "".join(
        '<div class="raw-score-metric-row">'
        f'<div class="raw-metric-label">{html.escape(metric["name"])}</div>'
        f'<div class="raw-metric-value">{html.escape(format_raw_metric_value(metric["value"]))}</div>'
        "</div>"
        for metric in group.get("metrics", [])
    )
    if not metrics_html:
        metrics_html = '<div class="raw-score-empty">Sem metricas</div>'

    return (
        f'<article class="raw-score-group"{score_id_attr}>'
        '<div class="raw-score-header">'
        "<div>"
        '<div class="raw-score-kicker">Score</div>'
        f'<h3 class="raw-score-name">{html.escape(clean_text(group.get("name"), "Sem categoria"))}</h3>'
        "</div>"
        f"{percentile_html}"
        "</div>"
        f'<div class="raw-score-metrics">{metrics_html}</div>'
        "</article>"
    )


def raw_metric_cards_html(
    metric_rows: list[dict],
    score_rows: list[dict] | None = None,
    score_table: str | None = None,
) -> str:
    if not metric_rows:
        return ""

    position, groups = raw_metric_groups(metric_rows, score_rows or [], score_table)
    cards_html = [raw_metric_group_html(group) for group in groups]

    if not cards_html:
        return ""

    return (
        '<section class="raw-metrics-panel">'
        '<div class="raw-metrics-heading">'
        '<h2 class="raw-metrics-title">Números na temporada</h2>'
        f'<div class="raw-metrics-position">{html.escape(position)}</div>'
        "</div>"
        f'<div class="raw-score-group-grid">{"".join(cards_html)}</div>'
        "</section>"
    )


def score_table_html(score_rows: list[dict], categories: list[dict]) -> str:
    cards_html = []

    for category in categories:
        cards_html.append(
            '<article class="score-support-card">'
            f'<div class="score-support-category">{html.escape(category["name"])}</div>'
            '<div class="score-support-metrics">'
            '<div>'
            f'<div class="score-support-value">{html.escape(format_percentile(category.get("percentile")))}</div>'
            "</div>"
            "</div>"
            "</article>"
        )

    if not cards_html:
        cards_html.append(
            '<article class="score-support-card">'
            '<div class="score-support-category">Sem categoria</div>'
            '<div class="score-support-metrics">'
            '<div><div class="score-support-value">-</div></div>'
            "</div>"
            "</article>"
        )

    return (
        '<section class="score-support-panel">'
        f'<div class="score-support-strip">{"".join(cards_html)}</div>'
        "</section>"
    )


def radar_axis_scale(values: list[float]) -> tuple[int, list[int]]:
    if not values:
        return 100, [20, 40, 60, 80, 100]

    max_value = max(values)
    axis_max = int(np.ceil(max(max_value * 1.25, 20) / 10) * 10)
    axis_max = min(100, max(20, axis_max))
    step = max(5, int(np.ceil(axis_max / 5 / 5) * 5))
    tickvals = list(range(step, axis_max + 1, step))

    return axis_max, tickvals


def radar_text_positions(count: int) -> list[str]:
    if count <= 0:
        return []

    positions = []
    for index in range(count):
        angle = (index / count) * 360
        if 45 <= angle < 135:
            positions.append("top center")
        elif 135 <= angle < 225:
            positions.append("middle left")
        elif 225 <= angle < 315:
            positions.append("bottom center")
        else:
            positions.append("middle right")

    return positions


def score_radar_figure(categories: list[dict]) -> go.Figure:
    labels = []
    values = []
    value_labels = []
    for category in categories:
        percentile = category.get("percentile")
        if pd.isna(percentile):
            continue

        try:
            percentile_number = float(percentile)
        except (TypeError, ValueError):
            continue

        labels.append(category["name"])
        clipped_percentile = max(0, min(100, percentile_number))
        values.append(clipped_percentile)
        value_labels.append(format_percentile(clipped_percentile))

    axis_max, tickvals = radar_axis_scale(values)
    text_positions = radar_text_positions(len(values))

    if labels and values:
        labels = [*labels, labels[0]]
        values = [*values, values[0]]
        value_labels = [*value_labels, value_labels[0]]
        text_positions = [*text_positions, text_positions[0]]

    figure = go.Figure()
    figure.add_trace(
        go.Scatterpolar(
            r=values,
            theta=labels,
            fill="toself",
            fillcolor="rgba(34, 197, 94, 0.10)",
            hoverinfo="skip",
            line={"color": "rgba(34, 197, 94, 0.18)", "width": 12},
            marker={"size": 0},
            mode="lines",
            name="Area",
        )
    )
    figure.add_trace(
        go.Scatterpolar(
            r=values,
            theta=labels,
            fill="toself",
            fillcolor="rgba(34, 197, 94, 0.34)",
            line={"color": "#22c55e", "width": 4},
            marker={"color": "#facc15", "size": 12, "line": {"color": "#052e16", "width": 2}},
            hovertemplate="%{theta}<br>Percentil %{r:.1f}%<extra></extra>",
            mode="lines+markers+text",
            name="Percentil",
            text=value_labels,
            textfont={"color": "#f8fafc", "size": 13},
            textposition=text_positions,
        )
    )
    figure.update_layout(
        height=390,
        hoverlabel={
            "bgcolor": "rgba(7, 13, 18, 0.96)",
            "bordercolor": "rgba(34, 197, 94, 0.45)",
            "font": {"color": "#f8fafc", "size": 13},
        },
        margin={"l": 72, "r": 72, "t": 40, "b": 42},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        polar={
            "bgcolor": "rgba(2, 6, 23, 0.06)",
            "domain": {"x": [0.08, 0.92], "y": [0.08, 0.92]},
            "radialaxis": {
                "range": [0, axis_max],
                "showline": False,
                "showticklabels": False,
                "ticks": "",
                "tickvals": tickvals,
                "gridcolor": "rgba(148, 163, 184, 0.22)",
                "linecolor": "rgba(255, 255, 255, 0)",
            },
            "angularaxis": {
                "tickfont": {"color": "#f8fafc", "size": 13},
                "gridcolor": "rgba(56, 189, 248, 0.16)",
                "linecolor": "rgba(34, 197, 94, 0.24)",
            },
        },
    )
    return figure


def render_score_profile_section(player_id: object) -> None:
    score_rows, score_table = load_player_score_rows_with_table(player_id)
    categories = score_categories(score_rows)
    radar_categories = [category for category in categories if not pd.isna(category.get("percentile"))]
    first_row = score_rows[0] if score_rows else {}
    ranking = format_rank(first_row.get("ranking_percentil"))

    st.markdown(
        f"""
        <section class="score-style-section">
            <div class="score-style-heading">
                <div>
                    <div class="player-kicker">Estilo de jogo</div>
                    <div class="ranking-heading">
                        <div class="ranking-heading-label">Posicao no ranking</div>
                        <div class="ranking-heading-value">{html.escape(ranking)}</div>
                    </div>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if not score_rows or not radar_categories:
        st.warning("Nao encontrei percentis de score para desenhar o radar desse jogador.")
        return

    st.markdown(score_table_html(score_rows, categories), unsafe_allow_html=True)
    _left_spacer, radar_column, _right_spacer = st.columns([0.14, 0.72, 0.14])
    with radar_column:
        st.plotly_chart(
            score_radar_figure(categories),
            use_container_width=True,
            config={"displayModeBar": False, "responsive": True},
        )
    raw_metrics_html = raw_metric_cards_html(
        load_player_raw_metric_rows_from_table(player_id, score_table),
        score_rows,
        score_table,
    )
    if raw_metrics_html:
        st.markdown(raw_metrics_html, unsafe_allow_html=True)
    else:
        st.warning("Nao encontrei metricas brutas para a posicao desse jogador.")


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


def cluster_description_text(function_label: object, cluster_name: object) -> str:
    return CLUSTER_DESCRIPTIONS.get(
        (normalize_search_text(function_label), normalize_search_text(cluster_name)),
        "",
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
    minutes_value = clean_text(player_info.get("minutes"), "-")
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
        ("Minutos jogados", minutes_value),
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

    st.markdown(
        f"""
        <section class="dialog-bio-shell">
            <div class="dialog-raw-title">
                <div class="player-kicker">Scores</div>
            </div>
            <div class="dialog-bio-grid">{score_details_html}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    score_rows, score_table = load_player_score_rows_with_table(player_id)
    raw_metrics_html = raw_metric_cards_html(
        load_player_raw_metric_rows_from_table(player_id, score_table),
        score_rows,
        score_table,
    )
    if raw_metrics_html:
        st.markdown(raw_metrics_html, unsafe_allow_html=True)


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
    cluster_description = cluster_description_text(selected_function, selected_cluster_name)
    cluster_description_html = (
        f'<p class="cluster-description">{html.escape(cluster_description)}</p>'
        if cluster_description
        else ""
    )
    title_column, close_column = st.columns([0.965, 0.035], gap="small")
    with title_column:
        st.markdown(
            f"""
            <section class="selected-cluster">
                <span class="cluster-close-visual">×</span>
                <div class="player-kicker">Cluster selecionado</div>
                <div class="player-list-title">{html.escape(selected_function)} | {html.escape(selected_cluster_name)}</div>
                {cluster_description_html}
            </section>
            """,
            unsafe_allow_html=True,
        )
    with close_column:
        st.markdown('<div class="cluster-close-anchor"></div>', unsafe_allow_html=True)
        if st.button("×", key=f"close_cluster_{key_fragment(selected_function)}", help="Fechar cluster"):
            st.session_state.pop("perfil_funcao_cluster", None)
            st.rerun()

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
                    "minutes": (
                        format_raw_metric_value(row["minutos_jogados"])
                        if "minutos_jogados" in row.index
                        else "-"
                    ),
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
        <section class="function-hero">
            <div class="main-title">Perfil por Função</div>
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
player_minutes = (
    format_raw_metric_value(player_row["minutos_jogados"])
    if "minutos_jogados" in player_row.index
    else "-"
)
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
                <div class="bio-label">Minutos jogados</div>
                <div class="bio-value">{html.escape(player_minutes)}</div>
            </div>
        </div>
        <div class="cluster-panel">
            <div class="cluster-label">Tipo de jogador</div>
            <div class="cluster-value">{html.escape(cluster_value)}</div>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

render_score_profile_section(player_id)
