
import os
from datetime import datetime
import pandas as pd
import streamlit as st
from supabase import create_client, Client


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Controle de Estoque",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# SUPABASE
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase não configurado.")
    st.info(
        "Configure SUPABASE_URL e SUPABASE_KEY no ambiente do Colab "
        "antes de iniciar o aplicativo."
    )
    st.stop()

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# ============================================================
# ESTILO
# ============================================================

st.markdown(
    """
    <style>
        .main {
            padding-top: 1rem;
        }

        .block-container {
            max-width: 1400px;
            padding-top: 1rem;
        }

        .estoque-card {
            padding: 18px;
            border-radius: 12px;
            border: 1px solid #dddddd;
            background: #fafafa;
        }

        .titulo {
            font-size: 30px;
            font-weight: 700;
        }

        .subtitulo {
            color: #666;
            font-size: 16px;
        }

        div[data-testid="stMetric"] {
            border: 1px solid #dddddd;
            padding: 12px;
            border-radius: 10px;
            background: #fafafa;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def buscar_destinos():
    try:
        response = (
            supabase
            .table("estoque_destinos")
            .select("*")
            .eq("ativo", True)
            .order("tag")
            .execute()
        )
        return response.data or []
    except Exception as e:
        st.error(f"Erro ao buscar destinos: {e}")
        return []


def buscar_unidades():
    try:
        response = (
            supabase
            .table("estoque_unidades")
            .select("*")
            .eq("ativo", True)
            .order("sigla")
            .execute()
        )
        return response.data or []
    except Exception as e:
        st.error(f"Erro ao buscar unidades: {e}")
        return []


def buscar_materiais():
    try:
        response = (
            supabase
            .table("estoque_materiais")
            .select(
                """
                *,
                estoque_unidades (
                    id,
                    sigla,
                    descricao
                )
                """
            )
            .eq("ativo", True)
            .order("descricao")
            .execute()
        )
        return response.data or []
    except Exception as e:
        st.error(f"Erro ao buscar materiais: {e}")
        return []


def buscar_usuarios():
    try:
        response = (
            supabase
            .table("estoque_usuarios")
            .select("*")
            .eq("ativo", True)
            .order("nome")
            .execute()
        )
        return response.data or []
    except Exception as e:
        st.error(f"Erro ao buscar usuários: {e}")
        return []


def buscar_estoque():
    try:
        response = (
            supabase
            .table("v_estoque_atual")
            .select("*")
            .order("descricao")
            .execute()
        )
        return response.data or []
    except Exception as e:
        st.error(f"Erro ao consultar estoque: {e}")
        return []


def buscar_movimentacoes():
    try:
        response = (
            supabase
            .table("v_historico_movimentacoes")
            .select("*")
            .order("data_hora", desc=True)
            .limit(500)
            .execute()
        )
        return response.data or []
    except Exception as e:
        st.error(f"Erro ao consultar movimentações: {e}")
        return []


def obter_saldo(material_id):
    try:
        response = (
            supabase
            .table("estoque_saldos")
            .select("quantidade")
            .eq("material_id", material_id)
            .limit(1)
            .execute()
        )

        if response.data:
            return float(response.data[0]["quantidade"] or 0)

        return 0.0

    except Exception:
        return 0.0


def criar_saldo_se_nao_existir(material_id):
    existente = (
        supabase
        .table("estoque_saldos")
        .select("id, quantidade")
        .eq("material_id", material_id)
        .limit(1)
        .execute()
    )

    if not existente.data:
        supabase.table("estoque_saldos").insert(
            {
                "material_id": material_id,
                "quantidade": 0
            }
        ).execute()


def atualizar_saldo(material_id, variacao):
    criar_saldo_se_nao_existir(material_id)

    atual = obter_saldo(material_id)
    novo = atual + float(variacao)

    if novo < 0:
        raise ValueError(
            f"Estoque insuficiente. Saldo atual: {atual}"
        )

    (
        supabase
        .table("estoque_saldos")
        .update(
            {
                "quantidade": novo,
                "atualizado_em": datetime.now().isoformat()
            }
        )
        .eq("material_id", material_id)
        .execute()
    )

    return novo


def gerar_numero_movimentacao():
    """
    Gera número no formato:

    MOV-AAAAMMDD-XXX
    """

    hoje = datetime.now().strftime("%Y%m%d")

    try:
        response = (
            supabase
            .table("estoque_movimentacoes")
            .select("numero_movimentacao")
            .like(
                "numero_movimentacao",
                f"MOV-{hoje}-%"
            )
            .order("numero_movimentacao", desc=True)
            .limit(1)
            .execute()
        )

        ultimo = 0

        if response.data:
            numero = response.data[0]["numero_movimentacao"]
            try:
                ultimo = int(numero.split("-")[-1])
            except Exception:
                ultimo = 0

        proximo = ultimo + 1

        return f"MOV-{hoje}-{proximo:03d}"

    except Exception:
        return f"MOV-{hoje}-001"


def unidade_do_material(material):
    unidade = material.get("estoque_unidades")

    if unidade:
        return unidade.get("sigla", "un")

    return "un"


def criar_mensagem_whatsapp(
    numero,
    data_hora,
    destino,
    itens,
    finalidade,
    retirado_por,
    aprovado_por,
    emergencial=False
):
    linhas = []

    linhas.append("📤 RETIRADA DE MATERIAL")
    linhas.append("")
    linhas.append(f"Movimentação: {numero}")
    linhas.append(
        f"Data e hora: {data_hora.strftime('%d/%m/%Y %H:%M')}"
    )
    linhas.append("")
    linhas.append(f"Destino: {destino}")

    if emergencial:
        linhas.append("⚠️ RETIRADA EMERGENCIAL")

    linhas.append("")
    linhas.append("Item(ns) e quantidade(s):")

    for i, item in enumerate(itens, start=1):
        linhas.append(
            f"{i}. {item['descricao']} – "
            f"{item['quantidade']:g} – "
            f"{item['unidade']}"
        )

    linhas.append("")
    linhas.append(
        f"Finalidade da aplicação: {finalidade}"
    )
    linhas.append(
        f"Retirado por: {retirado_por}"
    )
    linhas.append(
        f"Aprovado por: {aprovado_por}"
    )

    return "\n".join(linhas)


# ============================================================
# MENU
# ============================================================

st.sidebar.markdown("## 📦 CONTROLE DE ESTOQUE")

pagina = st.sidebar.radio(
    "Menu",
    [
        "📊 Dashboard",
        "📤 Nova Retirada",
        "📦 Cadastro de Materiais",
        "📋 Estoque Atual",
        "🔄 Movimentações",
        "🏗️ Destinos / Sondas",
        "👥 Usuários"
    ]
)

st.sidebar.divider()

st.sidebar.caption(
    "Sistema independente do DDH"
)

st.sidebar.caption(
    "Controle de movimentação e rastreabilidade de materiais"
)


# ============================================================
# DASHBOARD
# ============================================================

if pagina == "📊 Dashboard":

    st.markdown(
        '<div class="titulo">📦 Controle de Estoque</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitulo">'
        'Controle de movimentação de materiais'
        '</div>',
        unsafe_allow_html=True
    )

    st.divider()

    estoque = buscar_estoque()
    movimentos = buscar_movimentacoes()

    df_estoque = pd.DataFrame(estoque)
    df_mov = pd.DataFrame(movimentos)

    total_materiais = len(df_estoque)

    estoque_baixo = 0

    if not df_estoque.empty and "estoque_baixo" in df_estoque.columns:
        estoque_baixo = int(
            df_estoque["estoque_baixo"]
            .fillna(False)
            .astype(bool)
            .sum()
        )

    hoje = datetime.now().date()

    retiradas_hoje = 0
    entradas_hoje = 0

    if not df_mov.empty and "data_hora" in df_mov.columns:

        datas = pd.to_datetime(
            df_mov["data_hora"],
            errors="coerce"
        ).dt.date

        hoje_df = df_mov[datas == hoje]

        if "tipo" in hoje_df.columns:
            retiradas_hoje = int(
                (hoje_df["tipo"] == "RETIRADA").sum()
            )

            entradas_hoje = int(
                (hoje_df["tipo"] == "ENTRADA").sum()
            )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "📦 Materiais cadastrados",
            total_materiais
        )

    with c2:
        st.metric(
            "📤 Retiradas hoje",
            retiradas_hoje
        )

    with c3:
        st.metric(
            "📥 Entradas hoje",
            entradas_hoje
        )

    with c4:
        st.metric(
            "⚠️ Estoque baixo",
            estoque_baixo
        )

    st.divider()

    st.subheader("📋 Últimas movimentações")

    if df_mov.empty:
        st.info("Nenhuma movimentação registrada.")
    else:

        colunas = [
            c for c in [
                "numero_movimentacao",
                "data_hora",
                "tipo",
                "destino_tag",
                "material_descricao",
                "quantidade",
                "unidade_sigla",
                "status"
            ]
            if c in df_mov.columns
        ]

        st.dataframe(
            df_mov[colunas].head(15),
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# CADASTRO DE MATERIAIS
# ============================================================

elif pagina == "📦 Cadastro de Materiais":

    st.title("📦 Cadastro de Materiais")

    st.write(
        "Cadastre os materiais que poderão ser utilizados nas "
        "movimentações do estoque."
    )

    unidades = buscar_unidades()

    mapa_unidades = {
        u["sigla"]: u["id"]
        for u in unidades
    }

    with st.form("form_material", clear_on_submit=True):

        c1, c2 = st.columns(2)

        with c1:
            codigo = st.text_input(
                "Código do material",
                placeholder="Ex.: MAT-0001"
            )

        with c2:
            descricao = st.text_input(
                "Descrição do material",
                placeholder="Ex.: Haste HQ"
            )

        c3, c4 = st.columns(2)

        with c3:
            unidade = st.selectbox(
                "Unidade",
                list(mapa_unidades.keys())
                if mapa_unidades
                else ["un"]
            )

        with c4:
            categoria = st.text_input(
                "Categoria",
                placeholder="Ex.: Sondagem"
            )

        c5, c6 = st.columns(2)

        with c5:
            estoque_minimo = st.number_input(
                "Estoque mínimo",
                min_value=0.0,
                value=0.0,
                step=1.0
            )

        with c6:
            estoque_maximo = st.number_input(
                "Estoque máximo",
                min_value=0.0,
                value=0.0,
                step=1.0
            )

        st.markdown("### Controles especiais")

        alto_valor = st.checkbox(
            "💰 Material de alto valor"
        )

        exige_foto = st.checkbox(
            "📷 Exigir fotografia na retirada"
        )

        controla_numero_serie = st.checkbox(
            "🔢 Controlar número de série"
        )

        salvar = st.form_submit_button(
            "💾 Cadastrar material",
            type="primary",
            use_container_width=True
        )

    if salvar:

        if not codigo.strip():
            st.error("Informe o código do material.")

        elif not descricao.strip():
            st.error("Informe a descrição do material.")

        elif estoque_maximo > 0 and estoque_minimo > estoque_maximo:
            st.error(
                "O estoque mínimo não pode ser maior que o estoque máximo."
            )

        else:

            try:

                material = {
                    "codigo": codigo.strip().upper(),
                    "descricao": descricao.strip(),
                    "unidade_id": mapa_unidades.get(unidade),
                    "categoria": categoria.strip() or None,
                    "estoque_minimo": estoque_minimo,
                    "estoque_maximo": estoque_maximo,
                    "exige_foto": exige_foto,
                    "controla_numero_serie": controla_numero_serie,
                    "alto_valor": alto_valor,
                    "ativo": True
                }

                resultado = (
                    supabase
                    .table("estoque_materiais")
                    .insert(material)
                    .execute()
                )

                if resultado.data:

                    material_id = resultado.data[0]["id"]

                    supabase.table(
                        "estoque_saldos"
                    ).insert(
                        {
                            "material_id": material_id,
                            "quantidade": 0
                        }
                    ).execute()

                    st.success(
                        f"Material '{descricao}' cadastrado com sucesso!"
                    )

                    st.rerun()

            except Exception as e:
                st.error(
                    f"Não foi possível cadastrar o material: {e}"
                )

    st.divider()

    st.subheader("📋 Materiais cadastrados")

    materiais = buscar_materiais()

    if materiais:

        dados = []

        for m in materiais:

            dados.append(
                {
                    "Código": m.get("codigo"),
                    "Descrição": m.get("descricao"),
                    "Unidade": unidade_do_material(m),
                    "Categoria": m.get("categoria") or "",
                    "Estoque mínimo": m.get("estoque_minimo", 0),
                    "Estoque máximo": m.get("estoque_maximo", 0),
                    "Alto valor": "SIM" if m.get("alto_valor") else "NÃO",
                    "Exige foto": "SIM" if m.get("exige_foto") else "NÃO",
                    "Nº série": "SIM"
                    if m.get("controla_numero_serie")
                    else "NÃO"
                }
            )

        st.dataframe(
            pd.DataFrame(dados),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("Nenhum material cadastrado.")


# ============================================================
# NOVA RETIRADA
# ============================================================

elif pagina == "📤 Nova Retirada":

    st.title("📤 Nova Retirada")

    st.info(
        "Todos os itens desta tela serão registrados em uma única "
        "movimentação."
    )

    materiais = buscar_materiais()
    destinos = buscar_destinos()
    usuarios = buscar_usuarios()

    if not materiais:
        st.warning(
            "Cadastre pelo menos um material antes de realizar uma retirada."
        )
        st.stop()

    if not destinos:
        st.warning(
            "Nenhum destino cadastrado."
        )
        st.stop()

    numero = gerar_numero_movimentacao()

    agora = datetime.now()

    st.markdown(
        f"### Movimentação: `{numero}`"
    )

    c1, c2 = st.columns(2)

    with c1:
        st.text_input(
            "Data e hora",
            value=agora.strftime("%d/%m/%Y %H:%M"),
            disabled=True
        )

    with c2:

        destino_opcoes = {
            d["tag"]: d["id"]
            for d in destinos
        }

        destino = st.selectbox(
            "Destino da retirada *",
            list(destino_opcoes.keys())
        )

    finalidade = st.text_area(
        "Finalidade da aplicação *",
        placeholder=(
            "Informe onde e para qual finalidade os materiais serão utilizados."
        )
    )

    emergencial = st.checkbox(
        "🚨 Retirada emergencial"
    )

    st.divider()

    st.subheader("📦 Itens da retirada")

    if "itens_retirada" not in st.session_state:
        st.session_state.itens_retirada = [
            {
                "material_id": None,
                "quantidade": 1.0,
                "numero_serie": "",
                "observacao": ""
            }
        ]

    mapa_materiais = {
        m["descricao"]: m
        for m in materiais
    }

    # --------------------------------------------------------
    # LINHAS DE ITENS
    # --------------------------------------------------------

    itens_para_salvar = []

    for i in range(
        len(st.session_state.itens_retirada)
    ):

        item = st.session_state.itens_retirada[i]

        st.markdown(
            f"#### Item {i + 1}"
        )

        c1, c2, c3 = st.columns([3, 1, 2])

        with c1:

            nomes = list(mapa_materiais.keys())

            indice_atual = 0

            if item["material_id"]:

                for idx, m in enumerate(materiais):

                    if m["id"] == item["material_id"]:
                        indice_atual = idx
                        break

            nome_material = st.selectbox(
                "Material",
                nomes,
                index=indice_atual,
                key=f"material_{i}"
            )

        material = mapa_materiais[nome_material]

        with c2:

            quantidade = st.number_input(
                "Quantidade",
                min_value=0.01,
                value=float(item["quantidade"]),
                step=1.0,
                key=f"quantidade_{i}"
            )

        with c3:

            st.text_input(
                "Unidade",
                value=unidade_do_material(material),
                disabled=True,
                key=f"unidade_{i}"
            )

        c4, c5 = st.columns(2)

        with c4:

            numero_serie = st.text_input(
                "Número de série",
                value=item.get("numero_serie", ""),
                key=f"serie_{i}",
                placeholder=(
                    "Obrigatório se o material controlar série"
                )
            )

        with c5:

            observacao = st.text_input(
                "Observação do item",
                value=item.get("observacao", ""),
                key=f"obs_{i}"
            )

        saldo_atual = obter_saldo(material["id"])

        st.caption(
            f"Estoque disponível: **{saldo_atual:g} "
            f"{unidade_do_material(material)}**"
        )

        if material.get("alto_valor"):
            st.warning(
                "💰 Este material está marcado como alto valor."
            )

        if material.get("exige_foto"):
            st.warning(
                "📷 Este material exige fotografia."
            )

        if material.get("controla_numero_serie"):
            st.warning(
                "🔢 Este material exige número de série."
            )

        foto = None

        if material.get("exige_foto") or material.get("alto_valor"):

            foto = st.file_uploader(
                "📷 Fotografia do item",
                type=[
                    "jpg",
                    "jpeg",
                    "png",
                    "webp"
                ],
                key=f"foto_{i}"
            )

        itens_para_salvar.append(
            {
                "material": material,
                "quantidade": quantidade,
                "unidade": unidade_do_material(material),
                "numero_serie": numero_serie.strip(),
                "observacao": observacao.strip(),
                "foto": foto
            }
        )

        if i < len(
            st.session_state.itens_retirada
        ) - 1:

            st.divider()

    # --------------------------------------------------------
    # BOTÕES DE ITEM
    # --------------------------------------------------------

    b1, b2 = st.columns(2)

    with b1:

        if st.button(
            "➕ Adicionar item",
            use_container_width=True
        ):

            st.session_state.itens_retirada.append(
                {
                    "material_id": None,
                    "quantidade": 1.0,
                    "numero_serie": "",
                    "observacao": ""
                }
            )

            st.rerun()

    with b2:

        if len(
            st.session_state.itens_retirada
        ) > 1:

            if st.button(
                "➖ Remover último item",
                use_container_width=True
            ):

                st.session_state.itens_retirada.pop()

                st.rerun()

    st.divider()

    # --------------------------------------------------------
    # RESPONSÁVEIS
    # --------------------------------------------------------

    st.subheader("👤 Responsáveis")

    nomes_usuarios = [
        u["nome"]
        for u in usuarios
    ]

    mapa_usuarios = {
        u["nome"]: u["id"]
        for u in usuarios
    }

    if nomes_usuarios:

        c1, c2 = st.columns(2)

        with c1:

            retirado_por = st.selectbox(
                "Retirado por *",
                nomes_usuarios,
                key="retirado_por"
            )

        with c2:

            aprovadores = [
                u["nome"]
                for u in usuarios
                if u.get("perfil") in [
                    "ADMIN",
                    "GESTOR",
                    "APROVADOR"
                ]
            ]

            if not aprovadores:
                aprovadores = nomes_usuarios

            aprovado_por = st.selectbox(
                "Aprovado por *",
                aprovadores,
                key="aprovado_por"
            )

    else:

        st.warning(
            "Cadastre usuários antes de registrar a retirada."
        )

        retirado_por = None
        aprovado_por = None

    st.divider()

    # --------------------------------------------------------
    # DIVERGÊNCIA
    # --------------------------------------------------------

    st.subheader("⚠️ Conferência")

    divergencia = st.checkbox(
        "Existe divergência de quantidade ou material?"
    )

    descricao_divergencia = ""

    if divergencia:

        descricao_divergencia = st.text_area(
            "Descreva a divergência *",
            placeholder=(
                "Informe a quantidade informada, "
                "quantidade conferida e/ou material divergente."
            )
        )

    st.divider()

    # --------------------------------------------------------
    # RESUMO
    # --------------------------------------------------------

    st.subheader("📋 Resumo da retirada")

    resumo = []

    for item in itens_para_salvar:

        resumo.append(
            {
                "Item": item["material"]["descricao"],
                "Quantidade": item["quantidade"],
                "Unidade": item["unidade"],
                "Estoque atual": obter_saldo(
                    item["material"]["id"]
                )
            }
        )

    st.dataframe(
        pd.DataFrame(resumo),
        use_container_width=True,
        hide_index=True
    )

    salvar_retirada = st.button(
        "📤 REGISTRAR RETIRADA",
        type="primary",
        use_container_width=True
    )

    if salvar_retirada:

        erros = []

        if not finalidade.strip():
            erros.append(
                "Informe a finalidade da aplicação."
            )

        if not retirado_por:
            erros.append(
                "Informe quem retirou."
            )

        if not aprovado_por:
            erros.append(
                "Informe quem aprovou."
            )

        if divergencia and not descricao_divergencia.strip():
            erros.append(
                "Descreva a divergência."
            )

        if not itens_para_salvar:
            erros.append(
                "Adicione pelo menos um item."
            )

        # ----------------------------------------------
        # VALIDAR CADA ITEM
        # ----------------------------------------------

        for item in itens_para_salvar:

            material = item["material"]

            saldo = obter_saldo(
                material["id"]
            )

            if item["quantidade"] > saldo:

                erros.append(
                    f"Estoque insuficiente para "
                    f"{material['descricao']}. "
                    f"Disponível: {saldo:g} "
                    f"{item['unidade']}."
                )

            if (
                material.get("controla_numero_serie")
                and not item["numero_serie"]
            ):

                erros.append(
                    f"Informe o número de série para "
                    f"{material['descricao']}."
                )

            if (
                material.get("exige_foto")
                and not item["foto"]
            ):

                erros.append(
                    f"É obrigatória a fotografia para "
                    f"{material['descricao']}."
                )

        if erros:

            for erro in erros:
                st.error(erro)

        else:

            try:

                # --------------------------------------
                # CRIAR MOVIMENTAÇÃO
                # --------------------------------------

                movimentacao = {
                    "numero_movimentacao": numero,
                    "tipo": "RETIRADA",
                    "data_hora": agora.isoformat(),
                    "destino_id": destino_opcoes[destino],
                    "finalidade": finalidade.strip(),
                    "retirado_por_id": mapa_usuarios[retirado_por],
                    "aprovado_por_id": mapa_usuarios[aprovado_por],
                    "status": "CONCLUIDA",
                    "retirada_emergencial": emergencial,
                    "divergencia": divergencia,
                    "observacoes": (
                        descricao_divergencia.strip()
                        if divergencia
                        else None
                    )
                }

                mov_result = (
                    supabase
                    .table("estoque_movimentacoes")
                    .insert(movimentacao)
                    .execute()
                )

                if not mov_result.data:
                    raise Exception(
                        "Não foi possível criar a movimentação."
                    )

                movimentacao_id = mov_result.data[0]["id"]

                # --------------------------------------
                # GRAVAR ITENS E BAIXAR ESTOQUE
                # --------------------------------------

                for item in itens_para_salvar:

                    material = item["material"]

                    item_db = {
                        "movimentacao_id": movimentacao_id,
                        "material_id": material["id"],
                        "quantidade": item["quantidade"],
                        "unidade_id": material["unidade_id"],
                        "numero_serie": (
                            item["numero_serie"]
                            or None
                        ),
                        "observacao": (
                            item["observacao"]
                            or None
                        )
                    }

                    item_result = (
                        supabase
                        .table(
                            "estoque_movimentacao_itens"
                        )
                        .insert(item_db)
                        .execute()
                    )

                    if not item_result.data:
                        raise Exception(
                            f"Erro ao gravar item "
                            f"{material['descricao']}."
                        )

                    item_id = item_result.data[0]["id"]

                    # ----------------------------------
                    # BAIXA DO ESTOQUE
                    # ----------------------------------

                    saldo_anterior = obter_saldo(
                        material["id"]
                    )

                    saldo_posterior = atualizar_saldo(
                        material["id"],
                        -item["quantidade"]
                    )

                    # ----------------------------------
                    # HISTÓRICO
                    # ----------------------------------

                    supabase.table(
                        "estoque_historico"
                    ).insert(
                        {
                            "material_id": material["id"],
                            "movimentacao_id": movimentacao_id,
                            "tipo_movimentacao": "RETIRADA",
                            "quantidade_anterior": saldo_anterior,
                            "quantidade_movimentada": item["quantidade"],
                            "quantidade_posterior": saldo_posterior,
                            "registrado_em": agora.isoformat(),
                            "registrado_por_id":
                                mapa_usuarios[retirado_por]
                        }
                    ).execute()

                    # ----------------------------------
                    # ANEXO
                    # ----------------------------------

                    if item["foto"]:

                        arquivo = item["foto"]

                        nome_arquivo = (
                            f"{movimentacao_id}/"
                            f"{item_id}_"
                            f"{arquivo.name}"
                        )

                        try:

                            supabase.storage.from_(
                                "estoque-anexos"
                            ).upload(
                                nome_arquivo,
                                arquivo.getvalue(),
                                {
                                    "content-type":
                                        arquivo.type
                                }
                            )

                            supabase.table(
                                "estoque_anexos"
                            ).insert(
                                {
                                    "movimentacao_id":
                                        movimentacao_id,
                                    "movimentacao_item_id":
                                        item_id,
                                    "nome_arquivo":
                                        arquivo.name,
                                    "caminho_arquivo":
                                        nome_arquivo,
                                    "tipo_arquivo":
                                        arquivo.type,
                                    "tamanho_bytes":
                                        len(
                                            arquivo.getvalue()
                                        ),
                                    "enviado_por_id":
                                        mapa_usuarios[
                                            retirado_por
                                        ]
                                }
                            ).execute()

                        except Exception as erro_upload:

                            st.warning(
                                "A retirada foi registrada, "
                                "mas o anexo não pôde ser enviado: "
                                f"{erro_upload}"
                            )

                # --------------------------------------
                # DIVERGÊNCIA
                # --------------------------------------

                if divergencia:

                    supabase.table(
                        "estoque_divergencias"
                    ).insert(
                        {
                            "movimentacao_id":
                                movimentacao_id,
                            "descricao":
                                descricao_divergencia.strip(),
                            "registrada_por_id":
                                mapa_usuarios[
                                    retirado_por
                                ],
                            "registrada_em":
                                agora.isoformat(),
                            "resolvida":
                                False
                        }
                    ).execute()

                # --------------------------------------
                # MENSAGEM PARA GRUPO
                # --------------------------------------

                itens_msg = []

                for item in itens_para_salvar:

                    itens_msg.append(
                        {
                            "descricao":
                                item["material"]["descricao"],
                            "quantidade":
                                item["quantidade"],
                            "unidade":
                                item["unidade"]
                        }
                    )

                mensagem = criar_mensagem_whatsapp(
                    numero=numero,
                    data_hora=agora,
                    destino=destino,
                    itens=itens_msg,
                    finalidade=finalidade.strip(),
                    retirado_por=retirado_por,
                    aprovado_por=aprovado_por,
                    emergencial=emergencial
                )

                st.success(
                    f"✅ Retirada {numero} registrada com sucesso!"
                )

                st.subheader(
                    "📱 Mensagem pronta para o grupo"
                )

                st.text_area(
                    "Copie e envie no grupo",
                    value=mensagem,
                    height=450
                )

                st.session_state.itens_retirada = [
                    {
                        "material_id": None,
                        "quantidade": 1.0,
                        "numero_serie": "",
                        "observacao": ""
                    }
                ]

            except Exception as e:

                st.error(
                    "Erro ao registrar a retirada."
                )

                st.exception(e)


# ============================================================
# ESTOQUE ATUAL
# ============================================================

elif pagina == "📋 Estoque Atual":

    st.title("📋 Estoque Atual")

    estoque = buscar_estoque()

    if not estoque:

        st.info(
            "Nenhum material encontrado."
        )

    else:

        df = pd.DataFrame(estoque)

        pesquisa = st.text_input(
            "🔎 Pesquisar material"
        )

        if pesquisa:

            texto = pesquisa.lower()

            mask = (
                df.astype(str)
                .apply(
                    lambda col: col.str.lower().str.contains(
                        texto,
                        na=False
                    )
                )
                .any(axis=1)
            )

            df = df[mask]

        colunas = [
            c for c in [
                "codigo",
                "descricao",
                "unidade",
                "quantidade",
                "estoque_minimo",
                "estoque_maximo",
                "estoque_baixo"
            ]
            if c in df.columns
        ]

        st.dataframe(
            df[colunas],
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# MOVIMENTAÇÕES
# ============================================================

elif pagina == "🔄 Movimentações":

    st.title("🔄 Movimentações")

    movimentos = buscar_movimentacoes()

    if not movimentos:

        st.info(
            "Nenhuma movimentação registrada."
        )

    else:

        df = pd.DataFrame(movimentos)

        c1, c2, c3 = st.columns(3)

        with c1:

            tipos = [
                "TODOS"
            ] + sorted(
                df["tipo"].dropna().unique().tolist()
            ) if "tipo" in df.columns else ["TODOS"]

            filtro_tipo = st.selectbox(
                "Tipo",
                tipos
            )

        with c2:

            status = [
                "TODOS"
            ] + sorted(
                df["status"].dropna().unique().tolist()
            ) if "status" in df.columns else ["TODOS"]

            filtro_status = st.selectbox(
                "Status",
                status
            )

        with c3:

            busca = st.text_input(
                "Pesquisar"
            )

        if (
            filtro_tipo != "TODOS"
            and "tipo" in df.columns
        ):

            df = df[
                df["tipo"] == filtro_tipo
            ]

        if (
            filtro_status != "TODOS"
            and "status" in df.columns
        ):

            df = df[
                df["status"] == filtro_status
            ]

        if busca:

            mask = (
                df.astype(str)
                .apply(
                    lambda col:
                    col.str.contains(
                        busca,
                        case=False,
                        na=False
                    )
                )
                .any(axis=1)
            )

            df = df[mask]

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# DESTINOS
# ============================================================

elif pagina == "🏗️ Destinos / Sondas":

    st.title("🏗️ Destinos / Sondas")

    st.write(
        "Destinos cadastrados para recebimento dos materiais."
    )

    destinos = buscar_destinos()

    st.subheader("Cadastrar destino")

    with st.form("form_destino"):

        tag = st.text_input(
            "TAG",
            placeholder="Ex.: SDH-BF-004"
        )

        descricao = st.text_input(
            "Descrição",
            placeholder="Praça da sonda"
        )

        salvar = st.form_submit_button(
            "➕ Cadastrar destino",
            use_container_width=True
        )

    if salvar:

        if not tag.strip():

            st.error(
                "Informe a TAG."
            )

        else:

            try:

                supabase.table(
                    "estoque_destinos"
                ).insert(
                    {
                        "tag":
                            tag.strip().upper(),
                        "descricao":
                            descricao.strip() or None,
                        "ativo":
                            True
                    }
                ).execute()

                st.success(
                    "Destino cadastrado."
                )

                st.rerun()

            except Exception as e:

                st.error(
                    f"Erro ao cadastrar destino: {e}"
                )

    st.divider()

    if destinos:

        st.dataframe(
            pd.DataFrame(destinos),
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# USUÁRIOS
# ============================================================

elif pagina == "👥 Usuários":

    st.title("👥 Usuários")

    st.write(
        "Cadastre as pessoas responsáveis pelas movimentações."
    )

    with st.form("form_usuario"):

        nome = st.text_input(
            "Nome completo"
        )

        usuario = st.text_input(
            "Usuário",
            placeholder="Ex.: joao"
        )

        perfil = st.selectbox(
            "Perfil",
            [
                "OPERADOR",
                "APROVADOR",
                "GESTOR",
                "ADMIN"
            ]
        )

        salvar = st.form_submit_button(
            "➕ Cadastrar usuário",
            use_container_width=True
        )

    if salvar:

        if not nome.strip():
            st.error(
                "Informe o nome."
            )

        elif not usuario.strip():
            st.error(
                "Informe o usuário."
            )

        else:

            try:

                supabase.table(
                    "estoque_usuarios"
                ).insert(
                    {
                        "nome":
                            nome.strip(),
                        "usuario":
                            usuario.strip().lower(),
                        "perfil":
                            perfil,
                        "ativo":
                            True
                    }
                ).execute()

                st.success(
                    "Usuário cadastrado com sucesso."
                )

                st.rerun()

            except Exception as e:

                st.error(
                    f"Erro ao cadastrar usuário: {e}"
                )

    st.divider()

    usuarios = buscar_usuarios()

    if usuarios:

        st.dataframe(
            pd.DataFrame(usuarios),
            use_container_width=True,
            hide_index=True
        )
