"""Cadastros: materiais, destinos/sondas e usuários."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import db
from ui import components as c
from ui.compat import botao, botao_form, tabela


def _desativar_ui(tabela_db: str, registros: list[dict], rotulo, chave: str) -> None:
    """Desativação lógica (o histórico continua apontando para o registro)."""
    if not registros:
        return
    with st.expander("Desativar um cadastro"):
        mapa = {r["id"]: r for r in registros}
        rid = st.selectbox("Cadastro", list(mapa), format_func=lambda i: rotulo(mapa[i]), key=f"{chave}_sel")
        ok = st.checkbox("Confirmo que este cadastro deixará de aparecer nas listas", key=f"{chave}_ok")
        if botao("Desativar", key=f"{chave}_btn", disabled=not ok):
            try:
                db.desativar(tabela_db, rid)
                c.flash("Cadastro desativado.")
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"Não foi possível desativar: {e}")


# ------------------------------------------------------------------ materiais
def materiais() -> None:
    c.cabecalho("📦 Cadastro de Materiais", "Cadastre e configure os materiais utilizados nas operações.")
    c.mostrar_flash()

    unidades = db.listar_unidades()
    mapa_un = {u["sigla"]: u["id"] for u in unidades}
    existentes = db.listar_materiais()
    codigos = {str(m.get("codigo", "")).upper() for m in existentes}

    with st.form("form_material", clear_on_submit=True):
        c1, c2 = st.columns(2)
        codigo = c1.text_input("Código do material *", placeholder="Ex.: MAT-0001")
        descricao = c2.text_input("Descrição do material *", placeholder="Ex.: Haste HQ")
        c3, c4 = st.columns(2)
        unidade = c3.selectbox("Unidade", list(mapa_un) or ["un"])
        categoria = c4.text_input("Categoria", placeholder="Ex.: Sondagem")
        c5, c6 = st.columns(2)
        minimo = c5.number_input("Estoque mínimo", min_value=0.0, value=0.0, step=1.0)
        maximo = c6.number_input("Estoque máximo (0 = sem limite)", min_value=0.0, value=0.0, step=1.0)
        st.caption("Controles especiais")
        k1, k2, k3 = st.columns(3)
        alto_valor = k1.checkbox("💰 Alto valor")
        exige_foto = k2.checkbox("📷 Exigir foto na retirada")
        serie = k3.checkbox("🔢 Controlar nº de série")
        enviar = botao_form("💾 Cadastrar material", type="primary")

    if enviar:
        if not codigo.strip() or not descricao.strip():
            st.error("Informe o código e a descrição do material.")
        elif codigo.strip().upper() in codigos:
            st.error(f"Já existe um material ativo com o código {codigo.strip().upper()}.")
        elif maximo > 0 and minimo > maximo:
            st.error("O estoque mínimo não pode ser maior que o estoque máximo.")
        else:
            try:
                novo = db.inserir("estoque_materiais", {
                    "codigo": codigo.strip().upper(), "descricao": descricao.strip(),
                    "unidade_id": mapa_un.get(unidade), "categoria": categoria.strip() or None,
                    "estoque_minimo": minimo, "estoque_maximo": maximo, "exige_foto": exige_foto,
                    "controla_numero_serie": serie, "alto_valor": alto_valor, "ativo": True,
                })
                if novo:
                    try:
                        db.inserir("estoque_saldos", {"material_id": novo[0]["id"], "quantidade": 0})
                    except Exception as e:  # noqa: BLE001
                        st.warning(f"Material criado, mas o saldo inicial não foi gravado: {e}")
                c.flash(f"Material '{descricao.strip()}' cadastrado com sucesso!")
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"Não foi possível cadastrar o material: {e}")

    st.divider()
    st.subheader("📋 Materiais cadastrados")
    lista = db.listar_materiais()
    if not lista:
        c.vazio("Nenhum material cadastrado.")
        return
    busca = st.text_input("🔎 Pesquisar", key="mat_busca")
    df = pd.DataFrame([{
        "Código": m.get("codigo"), "Descrição": m.get("descricao"),
        "Unid.": (m.get("estoque_unidades") or {}).get("sigla", "un"),
        "Categoria": m.get("categoria") or "", "Mínimo": m.get("estoque_minimo", 0),
        "Máximo": m.get("estoque_maximo", 0),
        "Alto valor": "SIM" if m.get("alto_valor") else "—",
        "Exige foto": "SIM" if m.get("exige_foto") else "—",
        "Nº série": "SIM" if m.get("controla_numero_serie") else "—",
    } for m in lista])
    if busca:
        df = df[df.astype(str).apply(lambda col: col.str.contains(busca, case=False, na=False)).any(axis=1)]
    tabela(df)
    _desativar_ui("estoque_materiais", lista, lambda m: f"{m.get('codigo')} · {m.get('descricao')}", "mat_des")


# ------------------------------------------------------------------ destinos
def destinos() -> None:
    c.cabecalho("🏗️ Destinos / Sondas", "Gerencie os locais e sondas que recebem materiais.")
    c.mostrar_flash()
    existentes = db.listar_destinos()
    tags = {str(d.get("tag", "")).upper() for d in existentes}

    with st.form("form_destino", clear_on_submit=True):
        c1, c2 = st.columns(2)
        tag = c1.text_input("TAG *", placeholder="Ex.: SDH-BF-004")
        desc = c2.text_input("Descrição", placeholder="Praça da sonda")
        enviar = botao_form("➕ Cadastrar destino", type="primary")

    if enviar:
        if not tag.strip():
            st.error("Informe a TAG.")
        elif tag.strip().upper() in tags:
            st.error(f"Já existe um destino ativo com a TAG {tag.strip().upper()}.")
        else:
            try:
                db.inserir("estoque_destinos", {"tag": tag.strip().upper(), "descricao": desc.strip() or None, "ativo": True})
                c.flash("Destino cadastrado.")
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"Erro ao cadastrar destino: {e}")

    st.divider()
    if existentes:
        tabela(pd.DataFrame(existentes)[[col for col in ("tag", "descricao") if col in existentes[0]]]
               .rename(columns={"tag": "TAG", "descricao": "Descrição"}))
        _desativar_ui("estoque_destinos", existentes, lambda d: d.get("tag", ""), "dest_des")
    else:
        c.vazio("Nenhum destino cadastrado.")


# ------------------------------------------------------------------ usuários
def usuarios() -> None:
    c.cabecalho("👥 Usuários", "Gerencie os responsáveis pelas movimentações.")
    c.mostrar_flash()
    existentes = db.listar_usuarios()
    logins = {str(u.get("usuario", "")).lower() for u in existentes}

    with st.form("form_usuario", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 1.3, 1.3])
        nome = c1.text_input("Nome completo *")
        login = c2.text_input("Usuário *", placeholder="Ex.: joao")
        perfil = c3.selectbox("Perfil", ["OPERADOR", "APROVADOR", "GESTOR", "ADMIN"])
        enviar = botao_form("➕ Cadastrar usuário", type="primary")

    if enviar:
        if not nome.strip() or not login.strip():
            st.error("Informe o nome e o usuário.")
        elif login.strip().lower() in logins:
            st.error("Já existe um usuário ativo com esse login.")
        else:
            try:
                db.inserir("estoque_usuarios", {"nome": nome.strip(), "usuario": login.strip().lower(),
                                                "perfil": perfil, "ativo": True})
                c.flash("Usuário cadastrado com sucesso.")
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"Erro ao cadastrar usuário: {e}")

    st.divider()
    if existentes:
        cols = [col for col in ("nome", "usuario", "perfil") if col in existentes[0]]
        tabela(pd.DataFrame(existentes)[cols].rename(columns={"nome": "Nome", "usuario": "Usuário", "perfil": "Perfil"}))
        _desativar_ui("estoque_usuarios", existentes, lambda u: f"{u.get('nome')} ({u.get('perfil')})", "usr_des")
    else:
        c.vazio("Nenhum usuário cadastrado.")
