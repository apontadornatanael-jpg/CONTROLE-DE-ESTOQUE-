"""Nova Retirada e Nova Entrada (mesmo formulário, regras diferentes)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import db, exports
from core.config import PERFIS_APROVADORES, segredo
from core.services import (
    ErroNegocio, enviar_anexos, mensagem_whatsapp,
    registrar_movimentacao, validar_movimentacao,
)
from core.tempo import agora
from ui import components as c
from ui.compat import baixar, botao, tabela


def _unidade(material: dict) -> str:
    return (material.get("estoque_unidades") or {}).get("sigla") or "un"


# ------------------------------------------------------------------ callbacks
def _adicionar(p: str) -> None:
    st.session_state[f"{p}_n"] += 1


def _remover(p: str) -> None:
    if st.session_state[f"{p}_n"] > 1:
        st.session_state[f"{p}_n"] -= 1


def _nova(p: str) -> None:
    """Descarta o recibo e abre um formulário limpo (nova versão das chaves)."""
    ss = st.session_state
    ss[f"{p}_versao"] += 1
    ss[f"{p}_n"] = 1
    ss.pop(f"{p}_ultimo", None)


# ------------------------------------------------------------------ recibo
def _painel_sucesso(p: str, rec: dict) -> None:
    rotulo = "Retirada" if rec["tipo"] == "RETIRADA" else "Entrada"
    st.success(f"✅ {rotulo} {rec['numero']} registrada com sucesso!")
    for aviso in rec.get("avisos", []):
        st.warning(aviso)

    with st.container(border=True):
        c.titulo_painel("📱 Mensagem pronta para o grupo", "Copie e envie no WhatsApp")
        st.text_area(
            "Mensagem", value=rec["mensagem"], height=330,
            label_visibility="collapsed", key=f"{p}_msg_{rec['numero']}",
        )
    col1, col2, _ = st.columns([1.3, 1.3, 3])
    with col1:
        baixar("⬇️ Comprovante (PDF)", exports.comprovante_pdf(rec["registro"]),
               f"comprovante_{rec['numero']}.pdf", "application/pdf", key=f"{p}_pdf_{rec['numero']}")
    with col2:
        botao("➕ Registrar outra", type="primary", key=f"{p}_outra", on_click=_nova, args=(p,))


# ------------------------------------------------------------------ envio
def _enviar(tipo, p, itens, *, destino_id, destino_tag, finalidade, emergencial,
            resp_id, resp_nome, aprov_id, aprov_nome, divergencia, desc_div) -> None:
    eh_ret = tipo == "RETIRADA"
    erros = []
    if eh_ret and not finalidade.strip():
        erros.append("Informe a finalidade da aplicação.")
    if divergencia and not desc_div.strip():
        erros.append("Descreva a divergência.")

    # saldo lido AGORA (não do cache): outra pessoa pode ter retirado antes
    frescos = db.saldos_frescos([it["material"]["id"] for it in itens])
    erros += validar_movimentacao(tipo, itens, frescos)
    if erros:
        for e in erros:
            st.error(e)
        return

    momento = agora()
    cabecalho = {
        "data_hora": momento,
        "destino_id": destino_id,
        "finalidade": finalidade.strip() or None,
        "retirado_por_id": resp_id,
        "aprovado_por_id": aprov_id,
        "status": "CONCLUIDA",
        "retirada_emergencial": bool(emergencial),
        "divergencia": bool(divergencia),
        "observacoes": desc_div.strip() if divergencia else None,
        "_dia": momento.date(),
    }
    usar_rpc = str(segredo("USE_RPC", "")).lower() in ("1", "true", "sim")
    try:
        with st.spinner("Registrando..."):
            res = registrar_movimentacao(
                db.get_client(), tipo=tipo, cabecalho=cabecalho, itens=itens,
                divergencia_txt=desc_div.strip() if divergencia else None,
                usuario_id=resp_id, usar_rpc=usar_rpc,
            )
    except ErroNegocio as e:
        st.error(str(e))
        return
    except Exception as e:  # noqa: BLE001
        st.error(f"Erro inesperado ao registrar: {e}")
        return

    anexos = [
        {"item_id": res["item_ids"][i], "nome": it["foto"].name,
         "conteudo": it["foto"].getvalue(), "tipo": it["foto"].type}
        for i, it in enumerate(itens)
        if it.get("foto") and i < len(res["item_ids"])
    ]
    avisos = enviar_anexos(db.get_client(), res["id"], anexos, resp_id) if anexos else []
    db.limpar_cache()

    lista = [
        {"descricao": it["material"]["descricao"], "quantidade": it["quantidade"],
         "unidade": _unidade(it["material"]), "numero_serie": it.get("numero_serie")}
        for it in itens
    ]
    st.session_state[f"{p}_ultimo"] = {
        "numero": res["numero"], "tipo": tipo, "avisos": avisos,
        "mensagem": mensagem_whatsapp(
            numero=res["numero"], data_hora=momento, tipo=tipo, destino=destino_tag, itens=lista,
            finalidade=finalidade.strip() or "—", responsavel=resp_nome, aprovador=aprov_nome,
            emergencial=emergencial,
        ),
        "registro": {
            "numero": res["numero"], "tipo": tipo, "data_hora": momento, "destino": destino_tag,
            "itens": lista, "finalidade": finalidade.strip(), "responsavel": resp_nome,
            "aprovador": aprov_nome, "emergencial": emergencial,
            "divergencia": desc_div.strip() if divergencia else None,
        },
    }
    st.rerun()


# ------------------------------------------------------------------ página
def render(tipo: str) -> None:
    eh_ret = tipo == "RETIRADA"
    p = tipo.lower()
    ss = st.session_state
    ss.setdefault(f"{p}_versao", 0)
    ss.setdefault(f"{p}_n", 1)

    c.cabecalho(
        "📤 Nova Retirada" if eh_ret else "📥 Nova Entrada",
        "Registre uma saída de materiais com rastreabilidade completa."
        if eh_ret else "Registre o recebimento de materiais no estoque.",
    )

    if ss.get(f"{p}_ultimo"):
        _painel_sucesso(p, ss[f"{p}_ultimo"])
        return

    materiais = db.listar_materiais()
    destinos = db.listar_destinos()
    usuarios = db.listar_usuarios()
    saldos = db.listar_saldos()

    if not materiais:
        st.warning("Cadastre pelo menos um material antes de registrar movimentações.")
        return
    if eh_ret and not destinos:
        st.warning("Cadastre pelo menos um destino / sonda antes de registrar retiradas.")
        return
    if not usuarios:
        st.warning("Cadastre pelo menos um usuário responsável antes de registrar movimentações.")
        return

    def k(nome: str) -> str:  # chaves versionadas: "Registrar outra" zera o formulário
        return f"{p}_{ss[f'{p}_versao']}_{nome}"

    mapa_mat = {m["id"]: m for m in materiais}
    nomes_usuarios = {u["id"]: u["nome"] for u in usuarios}

    # ------------------------------------------------------ 1. dados gerais
    with st.container(border=True):
        c.secao("1 · Dados da movimentação")
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Data e hora", value=agora().strftime("%d/%m/%Y %H:%M"), disabled=True,
                          help="O número e o horário definitivos são gerados ao confirmar.")
        destino_id, destino_tag = None, None
        if eh_ret:
            with col2:
                mapa_dest = {d["id"]: d for d in destinos}
                destino_id = st.selectbox(
                    "Destino da retirada *", list(mapa_dest), key=k("destino"),
                    format_func=lambda i: mapa_dest[i]["tag"] + (
                        f" — {mapa_dest[i]['descricao']}" if mapa_dest[i].get("descricao") else ""),
                )
                destino_tag = mapa_dest[destino_id]["tag"]
            finalidade = st.text_area(
                "Finalidade da aplicação *", key=k("fin"),
                placeholder="Informe onde e para qual finalidade os materiais serão utilizados.",
            )
            emergencial = st.checkbox("🚨 Retirada emergencial", key=k("emerg"))
        else:
            with col2:
                finalidade = st.text_input("Origem / observação (opcional)", key=k("fin"),
                                           placeholder="Ex.: NF 1234 — Fornecedor X")
            emergencial = False

    # ------------------------------------------------------ 2. itens
    itens: list[dict] = []
    c.secao("2 · Materiais")
    for i in range(ss[f"{p}_n"]):
        with st.container(border=True):
            st.markdown(f"**Item {i + 1}**")
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                mid = st.selectbox(
                    "Material", list(mapa_mat), key=k(f"mat{i}"),
                    format_func=lambda x: f"{mapa_mat[x].get('codigo') or '—'} · {mapa_mat[x]['descricao']}",
                )
            m = mapa_mat[mid]
            un = _unidade(m)
            with c2:
                qtd = st.number_input("Quantidade", min_value=0.01, value=1.0, step=1.0, key=k(f"qtd{i}"))
            with c3:
                st.text_input("Unidade", value=un, disabled=True)  # sem key: acompanha o material

            d1, d2 = st.columns(2)
            with d1:
                serie = st.text_input(
                    "Número de série", key=k(f"serie{i}"),
                    placeholder="Obrigatório para este material" if m.get("controla_numero_serie") else "Opcional",
                )
            with d2:
                obs = st.text_input("Observação do item", key=k(f"obs{i}"))

            saldo = saldos.get(mid, 0.0)
            marcas = [t for ok, t in (
                (m.get("alto_valor"), "💰 alto valor"),
                (m.get("exige_foto"), "📷 exige foto"),
                (m.get("controla_numero_serie"), "🔢 exige nº de série"),
            ) if ok]
            st.caption(f"Estoque disponível: **{saldo:g} {un}**" + (f"  ·  {' · '.join(marcas)}" if marcas else ""))
            if eh_ret and qtd > saldo:
                st.warning(f"Quantidade acima do saldo disponível ({saldo:g} {un}).")

            foto = None
            if eh_ret and (m.get("exige_foto") or m.get("alto_valor")):
                foto = st.file_uploader(
                    "📷 Fotografia do item" + (" (obrigatória)" if m.get("exige_foto") else " (recomendada)"),
                    type=["jpg", "jpeg", "png", "webp"], key=k(f"foto{i}"),
                )
            itens.append({"material": m, "quantidade": float(qtd), "numero_serie": serie.strip(),
                          "observacao": obs.strip(), "foto": foto})

    b1, b2, _ = st.columns([1, 1, 3])
    with b1:
        botao("➕ Adicionar item", key=k("add"), on_click=_adicionar, args=(p,))
    with b2:
        if ss[f"{p}_n"] > 1:
            botao("➖ Remover último", key=k("rem"), on_click=_remover, args=(p,))

    # ------------------------------------------------------ 3. responsáveis
    with st.container(border=True):
        c.secao("3 · Responsáveis")
        col1, col2 = st.columns(2)
        with col1:
            resp_id = st.selectbox("Retirado por *" if eh_ret else "Recebido por *",
                                   list(nomes_usuarios), format_func=nomes_usuarios.get, key=k("resp"))
        aprov_id = None
        if eh_ret:
            aprovadores = [u["id"] for u in usuarios if u.get("perfil") in PERFIS_APROVADORES] or list(nomes_usuarios)
            with col2:
                aprov_id = st.selectbox("Aprovado por *", aprovadores, format_func=nomes_usuarios.get, key=k("aprov"))

    # ------------------------------------------------------ 4. conferência
    with st.container(border=True):
        c.secao("4 · Conferência")
        divergencia = st.checkbox("Existe divergência de quantidade ou material?", key=k("div"))
        desc_div = ""
        if divergencia:
            desc_div = st.text_area(
                "Descreva a divergência *", key=k("divtxt"),
                placeholder="Informe a quantidade informada, a quantidade conferida e/ou o material divergente.",
            )

        # resumo: o "saldo após" soma todas as linhas do mesmo material
        total_por_mat: dict = {}
        for it in itens:
            total_por_mat[it["material"]["id"]] = total_por_mat.get(it["material"]["id"], 0.0) + it["quantidade"]
        sinal = -1 if eh_ret else 1
        resumo = pd.DataFrame([
            {
                "Material": it["material"]["descricao"],
                "Quantidade": it["quantidade"],
                "Unid.": _unidade(it["material"]),
                "Saldo atual": saldos.get(it["material"]["id"], 0.0),
                "Saldo após": saldos.get(it["material"]["id"], 0.0) + sinal * total_por_mat[it["material"]["id"]],
            }
            for it in itens
        ])
        tabela(resumo)
        if eh_ret and (resumo["Saldo após"] < 0).any():
            st.error("Há itens que deixariam o estoque negativo. Ajuste as quantidades.")

    if botao("✅ CONFIRMAR E REGISTRAR " + ("RETIRADA" if eh_ret else "ENTRADA"),
             type="primary", key=k("enviar")):
        _enviar(
            tipo, p, itens, destino_id=destino_id, destino_tag=destino_tag, finalidade=finalidade,
            emergencial=emergencial, resp_id=resp_id, resp_nome=nomes_usuarios[resp_id],
            aprov_id=aprov_id, aprov_nome=nomes_usuarios.get(aprov_id), divergencia=divergencia,
            desc_div=desc_div,
        )
