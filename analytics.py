"""Cálculos de KPIs e séries para o dashboard (pandas puro, testável)."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from core.tempo import TZ

COLUNAS_MOV = [
    "mov_id", "numero", "tipo", "data_hora", "dia", "status", "destino",
    "emergencial", "divergencia", "material_id", "codigo", "descricao",
    "unidade", "quantidade",
]

_REGEX_TZ = r"(?:Z|[+-]\d{2}(?::?\d{2})?)$"


# ----------------------------------------------------------------------
# Montagem do DataFrame de movimentos (um registro por item)
# ----------------------------------------------------------------------
def para_local(serie: pd.Series) -> pd.Series:
    """Converte textos de data/hora para o fuso local.

    Valores com offset (timestamptz) são convertidos; valores sem offset
    (timestamp) são assumidos como já estando no horário local.
    """
    texto = serie.astype("string")
    tem_tz = texto.str.contains(_REGEX_TZ, regex=True, na=False)
    com_tz = pd.to_datetime(
        texto.where(tem_tz), errors="coerce", format="ISO8601", utc=True
    ).dt.tz_convert(TZ)
    sem_tz = pd.to_datetime(
        texto.where(~tem_tz), errors="coerce", format="ISO8601"
    ).dt.tz_localize(TZ, nonexistent="shift_forward", ambiguous="NaT")
    return com_tz.fillna(sem_tz)


def _vazio() -> pd.DataFrame:
    df = pd.DataFrame(columns=COLUNAS_MOV)
    df["data_hora"] = pd.to_datetime(df["data_hora"], utc=True).dt.tz_convert(TZ)
    return df


def montar_movimentos(cabecalhos, itens, materiais, destinos) -> pd.DataFrame:
    """Une cabeçalhos + itens + materiais + destinos em um único DataFrame."""
    if not cabecalhos:
        return _vazio()

    cab = pd.DataFrame(cabecalhos).rename(
        columns={"id": "mov_id", "numero_movimentacao": "numero"}
    )
    for coluna, padrao in (
        ("status", None), ("retirada_emergencial", False),
        ("divergencia", False), ("destino_id", None), ("tipo", None),
    ):
        if coluna not in cab.columns:
            cab[coluna] = padrao

    cab["data_hora"] = para_local(cab["data_hora"])
    cab["dia"] = cab["data_hora"].dt.date
    cab["emergencial"] = cab["retirada_emergencial"].fillna(False).astype(bool)
    cab["divergencia"] = cab["divergencia"].fillna(False).astype(bool)

    mapa_destinos = {d["id"]: d.get("tag") for d in (destinos or [])}
    cab["destino"] = cab["destino_id"].map(mapa_destinos)

    cab = cab[
        ["mov_id", "numero", "tipo", "data_hora", "dia", "status",
         "destino", "emergencial", "divergencia"]
    ]

    it = pd.DataFrame(itens or [])
    if it.empty:
        out = cab.copy()
        for c in ("material_id", "codigo", "descricao", "unidade", "quantidade"):
            out[c] = None
        return out[COLUNAS_MOV]

    it = it.rename(columns={"movimentacao_id": "mov_id"})
    mat = pd.DataFrame(
        [
            {
                "material_id": m["id"],
                "codigo": m.get("codigo"),
                "descricao": m.get("descricao"),
                "unidade": (m.get("estoque_unidades") or {}).get("sigla"),
            }
            for m in (materiais or [])
        ],
        columns=["material_id", "codigo", "descricao", "unidade"],
    )
    it = it[["mov_id", "material_id", "quantidade"]].merge(
        mat, on="material_id", how="left"
    )
    it["quantidade"] = pd.to_numeric(it["quantidade"], errors="coerce").fillna(0.0)

    out = cab.merge(it, on="mov_id", how="left")
    return out[COLUNAS_MOV].sort_values("data_hora", ascending=False).reset_index(drop=True)


# ----------------------------------------------------------------------
# Filtros
# ----------------------------------------------------------------------
def movimentos_unicos(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop_duplicates("mov_id") if not df.empty else df


def filtrar_periodo(df: pd.DataFrame, inicio: date, fim: date) -> pd.DataFrame:
    if df.empty:
        return df
    return df[(df["dia"] >= inicio) & (df["dia"] <= fim)]


def filtrar_destino(df: pd.DataFrame, destino: str | None) -> pd.DataFrame:
    if df.empty or not destino or destino == "Todos":
        return df
    return df[df["destino"] == destino]


# ----------------------------------------------------------------------
# KPIs
# ----------------------------------------------------------------------
def variacao_pct(atual: float, anterior: float) -> float | None:
    if not anterior:
        return None
    return (atual - anterior) / anterior * 100.0


def _contagens(df: pd.DataFrame) -> dict:
    um = movimentos_unicos(df)
    if um.empty:
        return {"retiradas": 0, "entradas": 0, "total": 0, "emergenciais": 0, "divergencias": 0}
    return {
        "retiradas": int((um["tipo"] == "RETIRADA").sum()),
        "entradas": int((um["tipo"] == "ENTRADA").sum()),
        "total": int(len(um)),
        "emergenciais": int(((um["tipo"] == "RETIRADA") & um["emergencial"]).sum()),
        "divergencias": int(um["divergencia"].sum()),
    }


def kpis(atual: pd.DataFrame, anterior: pd.DataFrame) -> dict:
    a, b = _contagens(atual), _contagens(anterior)
    return {
        **a,
        "delta_retiradas": variacao_pct(a["retiradas"], b["retiradas"]),
        "delta_entradas": variacao_pct(a["entradas"], b["entradas"]),
        "delta_total": variacao_pct(a["total"], b["total"]),
    }


# ----------------------------------------------------------------------
# Séries e rankings
# ----------------------------------------------------------------------
def serie_diaria(df: pd.DataFrame, inicio: date, fim: date) -> pd.DataFrame:
    """Movimentações distintas por dia: colunas Dia, Entradas, Retiradas."""
    dias = pd.date_range(inicio, fim, freq="D")
    base = pd.DataFrame({"Dia": dias, "Entradas": 0, "Retiradas": 0})
    um = movimentos_unicos(filtrar_periodo(df, inicio, fim))
    if um.empty:
        return base
    cont = um.groupby(["dia", "tipo"]).size().unstack(fill_value=0)
    cont.index = pd.to_datetime(cont.index)
    cont = cont.reindex(dias, fill_value=0)
    base["Entradas"] = cont["ENTRADA"].to_numpy() if "ENTRADA" in cont else 0
    base["Retiradas"] = cont["RETIRADA"].to_numpy() if "RETIRADA" in cont else 0
    return base


def top_materiais(df: pd.DataFrame, n: int = 10, tipo: str = "RETIRADA") -> pd.DataFrame:
    d = df[(df["tipo"] == tipo) & df["material_id"].notna()] if not df.empty else df
    if d.empty:
        return pd.DataFrame(columns=["Material", "Movimentações", "Quantidade", "Unidade"])
    g = (
        d.groupby(["material_id", "codigo", "descricao", "unidade"], dropna=False)
        .agg(Movimentações=("mov_id", "nunique"), Quantidade=("quantidade", "sum"))
        .reset_index()
        .sort_values(["Movimentações", "Quantidade"], ascending=False)
        .head(n)
    )
    g["Material"] = g["descricao"].fillna(g["codigo"]).fillna("(sem descrição)")
    g["Unidade"] = g["unidade"].fillna("un")
    return g[["Material", "Movimentações", "Quantidade", "Unidade"]].reset_index(drop=True)


def por_destino(df: pd.DataFrame, tipo: str = "RETIRADA") -> pd.DataFrame:
    um = movimentos_unicos(df)
    um = um[um["tipo"] == tipo] if not um.empty else um
    if um.empty:
        return pd.DataFrame(columns=["Destino", "Movimentações"])
    g = (
        um.assign(Destino=um["destino"].fillna("Sem destino"))
        .groupby("Destino").size().rename("Movimentações")
        .reset_index().sort_values("Movimentações", ascending=False)
    )
    return g.reset_index(drop=True)


# ----------------------------------------------------------------------
# Estoque
# ----------------------------------------------------------------------
def _numero(valor) -> float:
    try:
        n = float(valor)
        return 0.0 if pd.isna(n) else n
    except (TypeError, ValueError):
        return 0.0


def situacao_estoque(qtd: float, minimo: float, maximo: float, flag_baixo=None) -> str:
    if qtd <= 0:
        return "Zerado"
    if (minimo > 0 and qtd <= minimo) or bool(flag_baixo):
        return "Baixo"
    if maximo > 0 and qtd > maximo:
        return "Excesso"
    return "OK"


def classificar_estoque(estoque: list[dict]) -> pd.DataFrame:
    """Normaliza a view v_estoque_atual e calcula situação e cobertura."""
    cols = ["Código", "Descrição", "Unidade", "Saldo", "Mínimo", "Máximo", "Situação", "Cobertura"]
    if not estoque:
        return pd.DataFrame(columns=cols)
    linhas = []
    for r in estoque:
        qtd = _numero(r.get("quantidade"))
        mn = _numero(r.get("estoque_minimo"))
        mx = _numero(r.get("estoque_maximo"))
        linhas.append(
            {
                "Código": r.get("codigo") or "",
                "Descrição": r.get("descricao") or "",
                "Unidade": r.get("unidade") or "un",
                "Saldo": qtd,
                "Mínimo": mn,
                "Máximo": mx,
                "Situação": situacao_estoque(qtd, mn, mx, r.get("estoque_baixo")),
                "Cobertura": (qtd / mn) if mn > 0 else None,
            }
        )
    return pd.DataFrame(linhas, columns=cols)


def contagem_situacao(df_estoque: pd.DataFrame) -> dict:
    ordem = ["OK", "Baixo", "Zerado", "Excesso"]
    if df_estoque.empty:
        return {k: 0 for k in ordem}
    c = df_estoque["Situação"].value_counts()
    return {k: int(c.get(k, 0)) for k in ordem}


def estoque_critico(df_estoque: pd.DataFrame, n: int = 12) -> pd.DataFrame:
    if df_estoque.empty:
        return df_estoque
    d = df_estoque[df_estoque["Situação"].isin(["Zerado", "Baixo"])].copy()
    d["_ord"] = d["Cobertura"].fillna(-1)
    return d.sort_values(["_ord", "Saldo"]).drop(columns="_ord").head(n).reset_index(drop=True)


def inicio_periodo(hoje: date, dias: int) -> date:
    return hoje - timedelta(days=dias - 1)
