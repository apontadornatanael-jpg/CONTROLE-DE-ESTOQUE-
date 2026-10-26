"""Gráficos Plotly do dashboard. Cada função recebe um DataFrame e devolve uma Figure."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

AZUL = "#18324a"
AZUL_2 = "#3b7ea1"
VERDE = "#2f9e6b"
AMBAR = "#d99a19"
VERMELHO = "#d9534f"
CINZA = "#94a3b8"
COR_SITUACAO = {"OK": VERDE, "Baixo": AMBAR, "Zerado": VERMELHO, "Excesso": AZUL_2}


def _base(fig: go.Figure, altura: int = 300) -> go.Figure:
    fig.update_layout(
        height=altura,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="sans-serif", size=12, color="#1f2937"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hoverlabel=dict(bgcolor="white"),
    )
    fig.update_xaxes(showgrid=False, linecolor="#e5e7eb")
    fig.update_yaxes(gridcolor="#eef1f4", zeroline=False)
    return fig


def serie_diaria(df: pd.DataFrame) -> go.Figure:
    """Entradas (verde) e retiradas (azul) por dia."""
    fig = go.Figure()
    fig.add_bar(x=df["Dia"], y=df["Retiradas"], name="Retiradas", marker_color=AZUL,
                hovertemplate="%{x|%d/%m}: %{y} retirada(s)<extra></extra>")
    fig.add_bar(x=df["Dia"], y=df["Entradas"], name="Entradas", marker_color=VERDE,
                hovertemplate="%{x|%d/%m}: %{y} entrada(s)<extra></extra>")
    fig.update_layout(barmode="group", bargap=0.25)
    fig.update_xaxes(tickformat="%d/%m", dtick="D1" if len(df) <= 14 else None)
    fig.update_yaxes(dtick=1 if (df[["Retiradas", "Entradas"]].to_numpy().max() if len(df) else 0) <= 5 else None, rangemode="tozero")
    return _base(fig, 300)


def top_materiais(df: pd.DataFrame) -> go.Figure:
    """Ranking horizontal por número de retiradas; a quantidade aparece no hover."""
    d = df.iloc[::-1]  # maior no topo
    fig = go.Figure(
        go.Bar(
            x=d["Movimentações"], y=d["Material"], orientation="h", marker_color=AZUL_2,
            customdata=d[["Quantidade", "Unidade"]].to_numpy(),
            hovertemplate="%{y}<br>%{x} retirada(s) · total %{customdata[0]:g} %{customdata[1]}<extra></extra>",
            text=d["Movimentações"], textposition="outside", cliponaxis=False,
        )
    )
    fig.update_xaxes(showticklabels=False, showgrid=False)
    fig.update_yaxes(showgrid=False, automargin=True)
    return _base(fig, max(240, 34 * len(d) + 40))


def por_destino(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Pie(
            labels=df["Destino"], values=df["Movimentações"], hole=0.62, sort=False,
            marker=dict(colors=[AZUL, AZUL_2, VERDE, AMBAR, "#8b5cf6", "#ec4899", CINZA]),
            textinfo="percent", hovertemplate="%{label}: %{value} retirada(s)<extra></extra>",
        )
    )
    fig.update_layout(showlegend=True, legend=dict(orientation="v", x=1.02, y=0.5))
    return _base(fig, 280)


def situacao_estoque(contagem: dict) -> go.Figure:
    itens = [(k, v) for k, v in contagem.items() if v > 0]
    fig = go.Figure(
        go.Pie(
            labels=[k for k, _ in itens], values=[v for _, v in itens], hole=0.62, sort=False,
            marker=dict(colors=[COR_SITUACAO[k] for k, _ in itens]),
            textinfo="value", hovertemplate="%{label}: %{value} material(is)<extra></extra>",
        )
    )
    total = sum(v for _, v in itens)
    fig.add_annotation(text=f"<b>{total}</b><br>materiais", showarrow=False, font=dict(size=15))
    fig.update_layout(legend=dict(orientation="v", x=1.02, y=0.5))
    return _base(fig, 280)


def criticos(df: pd.DataFrame) -> go.Figure:
    """Saldo atual x mínimo dos materiais críticos (barras horizontais)."""
    d = df.iloc[::-1]
    cores = [COR_SITUACAO.get(s, AMBAR) for s in d["Situação"]]
    fig = go.Figure()
    fig.add_bar(y=d["Descrição"], x=d["Mínimo"], orientation="h", name="Mínimo",
                marker_color="#e2e8f0", hovertemplate="%{y}<br>mínimo %{x:g}<extra></extra>")
    fig.add_bar(y=d["Descrição"], x=d["Saldo"], orientation="h", name="Saldo",
                marker_color=cores, hovertemplate="%{y}<br>saldo %{x:g}<extra></extra>")
    fig.update_layout(barmode="overlay")
    fig.update_yaxes(showgrid=False, automargin=True)
    return _base(fig, max(240, 32 * len(d) + 60))
