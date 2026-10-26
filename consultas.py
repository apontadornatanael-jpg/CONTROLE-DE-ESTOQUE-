"""Consultas: estoque atual e histórico de movimentações."""
from __future__ import annotations

import streamlit as st

from core import analytics, db, exports
from core.tempo import agora
from ui import components as c
from ui.compat import baixar, tabela

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
ICONE_SITUACAO = {"OK": "🟢 OK", "Baixo": "🟡 Baixo", "Zerado": "🔴 Zerado", "Excesso": "🔵 Excesso"}


def estoque_atual() -> None:
    c.cabecalho("📋 Estoque Atual", "Consulte saldos, limites e disponibilidade dos materiais.")
    est = analytics.classificar_estoque(db.listar_estoque())
    if est.empty:
        c.vazio("Nenhum material encontrado.")
        return

    sit = analytics.contagem_situacao(est)
    cols = st.columns(4)
    for col, (nome, icone, tom) in zip(cols, [("OK", "🟢", "good"), ("Baixo", "🟡", "warn"),
                                              ("Zerado", "🔴", "bad"), ("Excesso", "🔵", "")]):
        with col:
            c.kpi(icone, nome, sit[nome], "materiais", tom=tom if sit[nome] else "")
    st.write("")

    f1, f2 = st.columns([2, 2])
    with f1:
        busca = st.text_input("🔎 Pesquisar material", key="est_busca")
    with f2:
        filtro = st.multiselect("Situação", list(ICONE_SITUACAO), default=[], key="est_sit",
                                placeholder="Todas")
    df = est
    if busca:
        df = df[df[["Código", "Descrição"]].apply(
            lambda col: col.astype(str).str.contains(busca, case=False, na=False)).any(axis=1)]
    if filtro:
        df = df[df["Situação"].isin(filtro)]

    vis = df.assign(Situação=df["Situação"].map(ICONE_SITUACAO))
    vis["Cobertura"] = vis["Cobertura"].map(lambda v: f"{v * 100:.0f}%" if v == v and v is not None else "—")
    tabela(vis)
    st.caption(f"{len(df)} de {len(est)} materiais · Cobertura = saldo ÷ mínimo")

    b1, b2, _ = st.columns([1, 1, 3])
    with b1:
        baixar("⬇️ Excel", exports.excel_bytes({"Estoque": df}), f"estoque_{agora():%Y%m%d}.xlsx", XLSX, key="est_x")
    with b2:
        baixar("⬇️ PDF", exports.relatorio_estoque_pdf(df, agora()), f"estoque_{agora():%Y%m%d}.pdf",
               "application/pdf", key="est_p")


def movimentacoes() -> None:
    c.cabecalho("🔄 Movimentações", "Histórico de entradas e retiradas registradas.")
    f1, f2, f3, f4 = st.columns([1.2, 1, 1.3, 1.5])
    with f1:
        dias = st.selectbox("Período", [7, 30, 90, 180, 365], index=1,
                            format_func=lambda d: f"Últimos {d} dias", key="mov_dias")
    df = db.carregar_movimentos(dias)
    if df.empty:
        c.vazio("Nenhuma movimentação no período.")
        return

    with f2:
        tipo = st.selectbox("Tipo", ["Todos"] + sorted(df["tipo"].dropna().unique().tolist()), key="mov_tipo")
    with f3:
        destino = st.selectbox("Destino", ["Todos"] + sorted(df["destino"].dropna().unique().tolist()), key="mov_dest")
    with f4:
        busca = st.text_input("🔎 Pesquisar", key="mov_busca", placeholder="nº, material, código…")

    if tipo != "Todos":
        df = df[df["tipo"] == tipo]
    df = analytics.filtrar_destino(df, destino)
    if busca:
        campos = df[["numero", "descricao", "codigo", "destino", "status"]].astype(str)
        df = df[campos.apply(lambda col: col.str.contains(busca, case=False, na=False)).any(axis=1)]

    st.caption(f"{df['mov_id'].nunique()} operação(ões) · {len(df)} linha(s) de item")
    vis = df.assign(**{"Data / hora": df["data_hora"].dt.strftime("%d/%m/%Y %H:%M")})[[
        "numero", "Data / hora", "tipo", "destino", "codigo", "descricao", "quantidade", "unidade",
        "status", "emergencial", "divergencia"]].rename(columns={
        "numero": "Movimento", "tipo": "Tipo", "destino": "Destino", "codigo": "Código",
        "descricao": "Material", "quantidade": "Qtd.", "unidade": "Unid.", "status": "Status",
        "emergencial": "Emergencial", "divergencia": "Divergência"})
    tabela(vis)
    baixar(
        "⬇️ Exportar (Excel)",
        exports.excel_bytes({"Movimentações": vis}),
        f"movimentacoes_{agora():%Y%m%d}.xlsx", XLSX, key="mov_x",
    )
