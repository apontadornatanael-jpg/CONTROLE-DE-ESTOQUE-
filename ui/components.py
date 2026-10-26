"""Componentes HTML reutilizáveis. Todo texto dinâmico é escapado (evita HTML injetado)."""
from __future__ import annotations

from html import escape as esc

import streamlit as st


def cabecalho(titulo: str, subtitulo: str = "", badge: str | None = None) -> None:
    badge_html = f'<div class="badge">{esc(badge)}</div>' if badge else ""
    st.markdown(
        f'<div class="page-header"><div><div class="page-title">{esc(titulo)}</div>'
        f'<div class="page-sub">{esc(subtitulo)}</div></div>{badge_html}</div>',
        unsafe_allow_html=True,
    )


def secao(texto: str) -> None:
    st.markdown(f'<div class="sec">{esc(texto)}</div>', unsafe_allow_html=True)


def titulo_painel(titulo: str, subtitulo: str = "") -> None:
    st.markdown(
        f'<div class="panel-t">{esc(titulo)}</div><div class="panel-s">{esc(subtitulo)}</div>',
        unsafe_allow_html=True,
    )


def _delta_html(delta: float | None) -> str:
    if delta is None:
        return ""
    if abs(delta) < 0.5:
        return '<span class="delta flat">= igual</span>'
    classe, seta = ("up", "▲") if delta > 0 else ("down", "▼")
    return f'<span class="delta {classe}">{seta} {abs(delta):.0f}%</span>'


def kpi(icone: str, rotulo: str, valor, legenda: str = "", delta: float | None = None, tom: str = "") -> None:
    """Cartão de indicador. `tom`: '', 'good', 'warn' ou 'bad'. `delta` em %."""
    st.markdown(
        f'<div class="kpi {esc(tom)}"><div class="kpi-top"><span>{esc(rotulo)}</span>'
        f'<span class="kpi-ico">{esc(icone)}</span></div>'
        f'<div class="kpi-val">{esc(str(valor))}</div>'
        f'<div class="kpi-cap">{_delta_html(delta)}<span>{esc(legenda)}</span></div></div>',
        unsafe_allow_html=True,
    )


def alerta_estoque(descricao: str, saldo: float, unidade: str, minimo: float, zerado: bool) -> None:
    mn = f"{minimo:g} {unidade}" if minimo else "—"
    st.markdown(
        f'<div class="alert {"zero" if zerado else ""}">'
        f'<div class="n">{"⛔" if zerado else "⚠️"} {esc(descricao)}</div>'
        f'<div class="q">Saldo: {saldo:g} {esc(unidade)}</div>'
        f'<div class="m">Mínimo configurado: {esc(mn)}</div></div>',
        unsafe_allow_html=True,
    )


def flash(mensagem: str) -> None:
    """Guarda uma mensagem para aparecer depois do próximo st.rerun()."""
    st.session_state["_flash"] = mensagem


def mostrar_flash() -> None:
    mensagem = st.session_state.pop("_flash", None)
    if mensagem:
        st.success(mensagem)


def vazio(mensagem: str, icone: str = "📭") -> None:
    st.markdown(f'<div class="empty">{esc(icone)}<br><br>{esc(mensagem)}</div>', unsafe_allow_html=True)
