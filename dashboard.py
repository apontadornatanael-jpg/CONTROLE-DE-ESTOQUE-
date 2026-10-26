"""Dashboard: indicadores, tendências e alertas de estoque."""
from __future__ import annotations

from datetime import timedelta

import streamlit as st

from core import analytics, db, exports
from core.tempo import agora
from ui import charts, components as c
from ui.compat import baixar, botao, grafico, tabela

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def render(navegar) -> None:
    hoje = agora().date()
    c.cabecalho(
        "📊 Dashboard",
        "Visão geral do estoque, operações e rastreabilidade",
        badge=f"Atualizado às {agora().strftime('%H:%M')}",
    )

    # ------------------------------------------------------------ filtros
    f1, f2, f3 = st.columns([2.2, 2, 1])
    with f1:
        dias = st.radio(
            "Período", [7, 30, 90], format_func=lambda d: f"Últimos {d} dias",
            horizontal=True, key="dash_dias",
        )
    # carrega o dobro para comparar com o período anterior
    todos = db.carregar_movimentos(dias * 2)
    destinos_disp = ["Todos"] + sorted(todos["destino"].dropna().unique().tolist()) if not todos.empty else ["Todos"]
    with f2:
        destino = st.selectbox("Destino / sonda", destinos_disp, key="dash_destino")
    with f3:
        st.write("")
        if st.button("🔄 Atualizar", key="dash_refresh", help="Recarrega os dados do banco"):
            db.limpar_cache()
            st.rerun()

    todos = analytics.filtrar_destino(todos, destino)
    inicio = analytics.inicio_periodo(hoje, dias)
    ini_ant, fim_ant = inicio - timedelta(days=dias), inicio - timedelta(days=1)
    atual = analytics.filtrar_periodo(todos, inicio, hoje)
    anterior = analytics.filtrar_periodo(todos, ini_ant, fim_ant)
    k = analytics.kpis(atual, anterior)

    est = analytics.classificar_estoque(db.listar_estoque())
    sit = analytics.contagem_situacao(est)
    criticos_n = sit["Baixo"] + sit["Zerado"]

    # ---------------------------------------------------------------- KPIs
    cols = st.columns(6)
    with cols[0]:
        c.kpi("📤", "Retiradas", k["retiradas"], f"vs {dias} dias anteriores", k["delta_retiradas"])
    with cols[1]:
        c.kpi("📥", "Entradas", k["entradas"], f"vs {dias} dias anteriores", k["delta_entradas"])
    with cols[2]:
        c.kpi("⚠️", "Estoque crítico", criticos_n,
              f"{sit['Zerado']} zerado(s) · {sit['Baixo']} baixo(s)",
              tom="bad" if sit["Zerado"] else ("warn" if criticos_n else "good"))
    with cols[3]:
        c.kpi("🚨", "Emergenciais", k["emergenciais"], "retiradas no período",
              tom="warn" if k["emergenciais"] else "")
    with cols[4]:
        c.kpi("🧾", "Divergências", k["divergencias"], "registradas no período",
              tom="warn" if k["divergencias"] else "")
    with cols[5]:
        c.kpi("📦", "Materiais ativos", len(est), "no catálogo")

    st.write("")
    a1, a2, a3 = st.columns(3)
    with a1:
        _atalho("📤 Nova Retirada", "qa_ret", navegar, True)
    with a2:
        _atalho("📥 Nova Entrada", "qa_ent", navegar)
    with a3:
        _atalho("📋 Estoque Atual", "qa_est", navegar)

    # ---------------------------------------------------------------- abas
    aba_geral, aba_estoque, aba_recentes = st.tabs(["📈 Visão geral", "📦 Estoque", "🔄 Últimas movimentações"])

    with aba_geral:
        col_a, col_b = st.columns([1.7, 1])
        with col_a, st.container(border=True):
            c.titulo_painel("Movimentações por dia", "Entradas e retiradas distintas (cada operação conta uma vez)")
            serie = analytics.serie_diaria(todos, inicio, hoje)
            grafico(charts.serie_diaria(serie), key="g_serie")
        with col_b, st.container(border=True):
            c.titulo_painel("Retiradas por destino", "Participação de cada destino / sonda")
            dest = analytics.por_destino(atual)
            if dest.empty:
                c.vazio("Sem retiradas no período.")
            else:
                grafico(charts.por_destino(dest), key="g_destino")

        with st.container(border=True):
            c.titulo_painel(
                "Materiais mais retirados",
                "Ranking por número de retiradas; passe o mouse para ver a quantidade total",
            )
            top = analytics.top_materiais(atual, n=10)
            if top.empty:
                c.vazio("Sem retiradas no período.")
            else:
                grafico(charts.top_materiais(top), key="g_top")

    with aba_estoque:
        col_a, col_b = st.columns([1, 1.6])
        with col_a, st.container(border=True):
            c.titulo_painel("Situação do estoque", "Quantidade de materiais por situação")
            if est.empty:
                c.vazio("Nenhum material encontrado.")
            else:
                grafico(charts.situacao_estoque(sit), key="g_sit")
        with col_b, st.container(border=True):
            c.titulo_painel("Materiais que precisam de atenção", "Saldo atual comparado ao mínimo configurado")
            crit = analytics.estoque_critico(est, n=12)
            if crit.empty:
                st.success("✓ Nenhum material zerado ou abaixo do mínimo.")
            else:
                grafico(charts.criticos(crit), key="g_crit")
        if not est.empty:
            b1, b2, _ = st.columns([1, 1, 3])
            with b1:
                baixar("⬇️ Excel", exports.excel_bytes({"Estoque": est}),
                       f"estoque_{hoje:%Y%m%d}.xlsx", XLSX, key="dl_est_x")
            with b2:
                baixar("⬇️ PDF", exports.relatorio_estoque_pdf(est, agora()),
                       f"estoque_{hoje:%Y%m%d}.pdf", "application/pdf", key="dl_est_p")

    with aba_recentes:
        um = analytics.movimentos_unicos(atual)
        if um.empty:
            c.vazio("Nenhuma movimentação no período.")
        else:
            itens = atual.groupby("mov_id").size().rename("Itens")
            rec = um.merge(itens, on="mov_id").head(15)
            vis = rec.assign(**{"Data / hora": rec["data_hora"].dt.strftime("%d/%m/%Y %H:%M")})[
                ["numero", "Data / hora", "tipo", "destino", "Itens", "status"]
            ].rename(columns={"numero": "Movimento", "tipo": "Tipo", "destino": "Destino", "status": "Status"})
            tabela(vis)
            baixar(
                "⬇️ Exportar período (Excel)",
                exports.excel_bytes({
                    "Movimentações": atual.drop(columns=["dia", "material_id"]).rename(columns={
                        "mov_id": "ID", "numero": "Movimento", "tipo": "Tipo", "data_hora": "Data/hora",
                        "status": "Status", "destino": "Destino", "emergencial": "Emergencial",
                        "divergencia": "Divergência", "codigo": "Código", "descricao": "Material",
                        "unidade": "Unid.", "quantidade": "Quantidade"}),
                }),
                f"movimentacoes_{inicio:%Y%m%d}_{hoje:%Y%m%d}.xlsx", XLSX, key="dl_mov_x",
            )


def _atalho(destino: str, chave: str, navegar, primario: bool = False) -> None:
    botao(destino, key=chave, type="primary" if primario else "secondary", on_click=navegar, args=(destino,))
