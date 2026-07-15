from __future__ import annotations

import base64
import html
import os
from datetime import date
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client


ROOT_DIR = Path(__file__).parent
BACKGROUND_PATH = ROOT_DIR / "assets" / "background.png"
TEAM_LOGO_BUCKET = "camp-br-u20-player-images"
TEAM_LOGO_FOLDER = "teams"
PLAYER_IMAGE_FOLDER = "players"
SCORE_SCHEMA = "camp-br-u20"
METRICS_TABLES = [
    "fact.metrics_players.atacantes",
    "fact.metrics_players.defensores",
    "fact.metrics_players.goleiros",
    "fact.metrics_players.laterais",
    "fact.metrics_players.meias",
]
IMAGE_MIME_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}

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
            padding-top: 0.7rem;
            padding-bottom: 1.25rem;
            max-width: 1240px;
        }}

        .team-hero {{
            background: linear-gradient(135deg, rgba(8, 16, 22, 0.90), rgba(8, 16, 22, 0.58));
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 8px;
            box-shadow: 0 18px 54px rgba(0, 0, 0, 0.34);
            display: grid;
            grid-template-columns: 96px minmax(0, 1fr);
            gap: 0.95rem;
            margin-bottom: 0.75rem;
            overflow: hidden;
            padding: 0.8rem 1rem;
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
            height: 88px;
            justify-content: center;
            padding: 0.65rem;
            width: 88px;
        }}

        .team-crest img {{
            max-height: 68px;
            max-width: 68px;
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
            margin: 0.55rem 0 0.18rem 0;
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
            gap: 0.8rem;
            grid-template-columns: minmax(170px, 220px) minmax(0, 1fr) minmax(190px, 250px);
            overflow: hidden;
            padding: 0.75rem;
        }}

        .player-photo {{
            align-items: flex-end;
            background: linear-gradient(180deg, rgba(15, 23, 42, 0.32), rgba(2, 6, 23, 0.84));
            border: 1px solid rgba(255, 255, 255, 0.13);
            border-radius: 8px;
            display: flex;
            justify-content: center;
            min-height: 245px;
            overflow: hidden;
        }}

        .player-photo img {{
            display: block;
            height: 245px;
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
            gap: 0.55rem;
            grid-auto-rows: minmax(72px, auto);
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }}

        .bio-card {{
            background: rgba(255, 255, 255, 0.075);
            border: 1px solid rgba(255, 255, 255, 0.13);
            border-radius: 8px;
            min-height: 72px;
            padding: 0.62rem 0.72rem;
        }}

        .bio-label {{
            color: rgba(203, 213, 225, 0.72);
            font-size: 0.66rem;
            font-weight: 700;
            margin-bottom: 0.28rem;
            text-transform: uppercase;
        }}

        .bio-value {{
            color: #f8fafc;
            font-size: clamp(0.98rem, 1.3vw, 1.28rem);
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
            min-height: 245px;
            padding: 1rem;
        }}

        .cluster-label {{
            color: rgba(203, 213, 225, 0.72);
            font-size: 0.66rem;
            font-weight: 800;
            margin-bottom: 0.4rem;
            text-transform: uppercase;
        }}

        .cluster-value {{
            color: #f8fafc;
            font-size: clamp(1.6rem, 2.7vw, 2.35rem);
            font-weight: 900;
            line-height: 0.98;
            margin-bottom: 0.35rem;
        }}

        .cluster-source {{
            color: rgba(248, 250, 252, 0.62);
            font-size: 0.78rem;
            font-weight: 700;
            margin-bottom: 0;
        }}

        .performance-section {{
            margin-top: 0.9rem;
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
            gap: 0.75rem;
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }}

        .performance-card {{
            background:
                linear-gradient(160deg, rgba(15, 23, 42, 0.86), rgba(7, 13, 18, 0.72));
            border: 1px solid rgba(255, 255, 255, 0.13);
            border-radius: 8px;
            overflow: hidden;
            padding: 0.85rem;
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
def load_player_performance(player_id: object) -> list[dict]:
    path_id = storage_path_id(player_id)
    if not path_id:
        return []

    try:
        normalized_player_id = int(path_id)
    except ValueError:
        normalized_player_id = path_id

    client = get_supabase_client()
    metric_rows = []

    for table in METRICS_TABLES:
        try:
            rows = (
                client.schema(SCORE_SCHEMA)
                .table(table)
                .select("*")
                .eq("player_id", normalized_player_id)
                .execute()
                .data
                or []
            )
            if rows:
                metric_rows = rows
                break
        except Exception:  # noqa: BLE001
            continue

    if not metric_rows:
        return []

    metric_defs = (
        client.schema(SCORE_SCHEMA)
        .table("dim.metrics")
        .select("metrica_id,nome_metrica,categoria_id,chave_categoria,nome_categoria,ordem_exibicao,tipo_valor,eh_percentual")
        .execute()
        .data
        or []
    )

    metric_defs_by_id = {row["metrica_id"]: row for row in metric_defs}
    grouped: dict[str, dict] = {}

    for metric in metric_rows:
        if pd.isna(metric.get("valor")):
            continue

        definition = metric_defs_by_id.get(metric.get("metrica_id"), {})
        category_key = (
            metric.get("categoria")
            or definition.get("chave_categoria")
            or metric.get("categoria_id")
        )
        if not category_key:
            continue

        category_key = str(category_key)
        category = grouped.setdefault(
            category_key,
            {
                "name": definition.get("nome_categoria")
                or humanize_key(str(metric.get("categoria") or category_key)),
                "metrics": [],
                "order": definition.get("ordem_exibicao")
                or metric.get("categoria_id")
                or 999,
                "percentiles": [],
            },
        )

        category["order"] = min(
            category["order"],
            definition.get("ordem_exibicao") or metric.get("categoria_id") or 999,
        )
        category["metrics"].append(
            {
                "name": definition.get("nome_metrica")
                or humanize_key(str(metric.get("coluna_metrica") or "")),
                "value": format_metric_value(metric.get("valor"), definition.get("eh_percentual")),
                "order": definition.get("ordem_exibicao") or 999,
            }
        )
        if not pd.isna(metric.get("percentil")):
            try:
                category["percentiles"].append(float(metric.get("percentil")))
            except (TypeError, ValueError):
                pass

    cards = []
    for category in grouped.values():
        percentiles = category.pop("percentiles")
        percentile = float(np.mean(percentiles)) if percentiles else 0.0
        cards.append(
            {
                "name": category["name"],
                "percentile": max(0, min(100, percentile)),
                "metrics": sorted(category["metrics"], key=lambda item: item["order"])[:5],
                "order": category["order"],
            }
        )

    return sorted(cards, key=lambda item: item["order"])


def numeric_columns_for_player(df: pd.DataFrame, excluded: set[str]) -> list[str]:
    numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()
    return [
        column
        for column in numeric_columns
        if column not in excluded and not column.lower().endswith("_id") and column.lower() != "id"
    ]


def render_performance_cards(cards: list[dict]) -> str:
    if not cards:
        return ""

    card_html = []
    for card in cards:
        percentile = card["percentile"]
        metrics = card["metrics"]
        metric_rows = "".join(
            '<div class="metric-row">'
            f'<div class="metric-name">{html.escape(metric["name"])}</div>'
            f'<div class="metric-value">{html.escape(metric["value"])}</div>'
            "</div>"
            for metric in metrics
        )
        if not metric_rows:
            metric_rows = (
                '<div class="metric-row">'
                '<div class="metric-name">Metricas brutas</div>'
                '<div class="metric-value">-</div>'
                "</div>"
            )

        card_html.append(
            '<article class="performance-card">'
            '<div class="performance-top">'
            f'<div class="percent-gauge" style="--pct: {percentile:.2f}">'
            f'<div class="percent-number">{percentile:.0f}</div>'
            "</div>"
            "<div>"
            '<div class="performance-label">Percentil</div>'
            f'<div class="performance-name">{html.escape(card["name"])}</div>'
            f'<div class="percent-bar" style="--pct: {percentile:.2f}">'
            '<div class="percent-fill"></div>'
            "</div>"
            "</div>"
            "</div>"
            f'<div class="metric-list">{metric_rows}</div>'
            "</article>"
        )

    return (
        '<section class="performance-section">'
        '<div class="section-header">'
        "<div>"
        '<div class="player-kicker">Performance por categoria</div>'
        '<h2 class="section-title">Percentis e metricas brutas</h2>'
        "</div>"
        '<p class="section-note">Score em percentil no topo; metricas da categoria abaixo</p>'
        "</div>"
        f'<div class="performance-grid">{"".join(card_html)}</div>'
        "</section>"
    )


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
player_id = player_row["jogador_id"] if "jogador_id" in player_row.index else None
team_logo = load_team_logo(team_id)
player_photo, player_photo_mime = load_player_photo(player_id)
performance_cards = load_player_performance(player_id)
team_logo_uri = image_data_uri(team_logo)
player_photo_uri = image_data_uri(player_photo, player_photo_mime)
team_logo_html = (
    f'<img src="{team_logo_uri}" alt="Escudo {html.escape(selected_team)}">'
    if team_logo_uri
    else ""
)
player_photo_html = (
    f'<img src="{player_photo_uri}" alt="Foto {html.escape(selected_player)}">'
    if player_photo_uri
    else '<div class="player-photo-placeholder">Foto indisponivel</div>'
)
player_position = first_valid_text(
    player_row["posicao_principal_detalhada"] if "posicao_principal_detalhada" in player_row.index else None,
    player_row["posicao_jogador"] if "posicao_jogador" in player_row.index else None,
)
player_country = row_value(player_row, "pais")
player_height = format_height(player_row["altura_cm"]) if "altura_cm" in player_row.index else "-"
player_age = calculate_age(player_row["data_nascimento"]) if "data_nascimento" in player_row.index else "-"
player_birth_date = format_date(player_row["data_nascimento"]) if "data_nascimento" in player_row.index else "-"
player_foot = row_value(player_row, "pe_preferido")
player_contract = format_date(player_row["contrato_ate"]) if "contrato_ate" in player_row.index else "-"
cluster_value = row_value(player_row, "cluster", "Sem cluster")
cluster_source = clean_text(player_position, "Grupo nao identificado")

st.markdown(
    f"""
    <section class="team-hero">
        <div class="team-crest">{team_logo_html}</div>
        <div>
            <div class="eyebrow">Campeonato Brasileiro Sub-20 2026</div>
            <div class="main-title">{html.escape(selected_team)}</div>
            <p class="subtitle">Perfil biografico do jogador e acompanhamento individual</p>
        </div>
    </section>
    <section>
        <div class="player-kicker">Jogador selecionado</div>
        <h1 class="player-name">{html.escape(selected_player)}</h1>
        <p class="player-position">{html.escape(player_position)}</p>
    </section>
    <section class="player-board">
        <div class="player-photo">{player_photo_html}</div>
        <div class="bio-grid">
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
            <div class="bio-card">
                <div class="bio-label">Nascimento</div>
                <div class="bio-value">{html.escape(player_birth_date)}</div>
            </div>
        </div>
        <div class="cluster-panel">
            <div class="cluster-label">Cluster</div>
            <div class="cluster-value">{html.escape(cluster_value)}</div>
            <div class="cluster-source">Grupo: {html.escape(cluster_source)}</div>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

performance_html = render_performance_cards(performance_cards)
if performance_html:
    st.markdown(performance_html, unsafe_allow_html=True)
