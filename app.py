
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
# ESTILO — INTERFACE MODERNA
# ============================================================

st.markdown(
    """
    <style>
        :root {
            --primary: #18324a;
            --primary-2: #244b6b;
            --accent: #d58b2a;
            --success: #198754;
            --danger: #dc3545;
            --warning: #d99a19;
            --bg: #f4f6f8;
            --card: #ffffff;
            --text: #1f2937;
            --muted: #6b7280;
            --border: #e5e7eb;
        }

        .stApp {
            background: var(--bg);
        }

        [data-testid="stHeader"] {
            background: rgba(244,246,248,.92);
        }

        .block-container {
            max-width: 1500px;
            padding-top: 1.2rem;
            padding-bottom: 3rem;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #12283b 0%, #183b56 100%);
            border-right: 1px solid rgba(255,255,255,.08);
        }

        section[data-testid="stSidebar"] * {
            color: #f8fafc !important;
        }

        section[data-testid="stSidebar"] .stRadio label {
            border-radius: 10px;
            padding: 7px 10px;
        }

        section[data-testid="stSidebar"] .stRadio label:hover {
            background: rgba(255,255,255,.10);
        }

        section[data-testid="stSidebar"] hr {
            border-color: rgba(255,255,255,.15);
        }

        .sidebar-brand {
            padding: 10px 6px 18px 6px;
        }

        .sidebar-brand .brand-icon {
            font-size: 34px;
            line-height: 1;
        }

        .sidebar-brand .brand-title {
            font-size: 19px;
            font-weight: 800;
            margin-top: 7px;
            letter-spacing: .3px;
        }

        .sidebar-brand .brand-subtitle {
            font-size: 12px;
            color: #cbd5e1 !important;
            margin-top: 3px;
        }

        /* Header */
        .page-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 18px;
        }

        .page-title {
            font-size: 31px;
            line-height: 1.1;
            font-weight: 800;
            color: var(--text);
            letter-spacing: -.6px;
        }

        .page-subtitle {
            color: var(--muted);
            font-size: 14px;
            margin-top: 6px;
        }

        .header-badge {
            background: #e8eef4;
            color: var(--primary);
            border: 1px solid #d6e0e8;
            padding: 8px 13px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            white-space: nowrap;
        }

        /* KPI cards */
        .kpi-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 18px 18px 16px;
            min-height: 126px;
            box-shadow: 0 5px 18px rgba(15,23,42,.05);
            transition: transform .18s ease, box-shadow .18s ease;
        }

        .kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(15,23,42,.09);
        }

        .kpi-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: var(--muted);
            font-size: 13px;
            font-weight: 700;
        }

        .kpi-icon {
            width: 38px;
            height: 38px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 11px;
            background: #edf2f7;
            font-size: 20px;
        }

        .kpi-value {
            margin-top: 12px;
            font-size: 29px;
            font-weight: 800;
            color: var(--text);
        }

        .kpi-caption {
            color: var(--muted);
            font-size: 12px;
            margin-top: 2px;
        }

        /* Generic cards */
        .panel {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 5px 18px rgba(15,23,42,.04);
            margin-bottom: 16px;
        }

        .panel-title {
            font-size: 17px;
            font-weight: 800;
            color: var(--text);
            margin-bottom: 3px;
        }

        .panel-subtitle {
            color: var(--muted);
            font-size: 12px;
            margin-bottom: 15px;
        }

        .section-label {
            color: var(--primary);
            font-size: 13px;
            font-weight: 800;
            letter-spacing: .4px;
            text-transform: uppercase;
            margin: 8px 0 10px;
        }

        .movement-chip {
            display: inline-block;
            padding: 5px 9px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 800;
        }

        .chip-success {
            color: #166534;
            background: #dcfce7;
        }

        .chip-warning {
            color: #854d0e;
            background: #fef3c7;
        }

        .chip-danger {
            color: #991b1b;
            background: #fee2e2;
        }

        .step-card {
            background: #fff;
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 15px 16px;
            margin: 7px 0;
        }

        .step-number {
            display: inline-flex;
            width: 29px;
            height: 29px;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            background: var(--primary);
            color: #fff;
            font-weight: 800;
            margin-right: 8px;
        }

        .step-title {
            font-weight: 800;
            color: var(--text);
        }

        .stock-good {
            color: #166534;
            font-weight: 800;
        }

        .stock-low {
            color: #b91c1c;
            font-weight: 800;
        }

        .empty-state {
            text-align: center;
            padding: 42px 20px;
            color: var(--muted);
            background: #fff;
            border: 1px dashed #cfd6de;
            border-radius: 16px;
        }

        /* Streamlit widgets */
        div[data-testid="stMetric"] {
            background: #fff;
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 14px;
            box-shadow: 0 4px 14px rgba(15,23,42,.04);
        }

        div[data-testid="stMetricLabel"] {
            font-size: 12px;
        }

        .stButton > button,
        .stFormSubmitButton > button {
            border-radius: 10px;
            min-height: 42px;
            font-weight: 700;
            border: 1px solid #d7dee5;
        }

        .stButton > button[kind="primary"],
        .stFormSubmitButton > button[kind="primary"] {
            background: var(--primary);
            border-color: var(--primary);
        }

        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        .stSelectbox div[data-baseweb="select"] > div {
            border-radius: 9px;
        }

        div[data-testid="stDataFrame"] {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid var(--border);
        }

        .quick-action {
            background: #fff;
            border: 1px solid var(--border);
            border-radius: 13px;
            padding: 14px;
            text-align: center;
            box-shadow: 0 4px 14px rgba(15,23,42,.04);
        }

        @media (max-width: 800px) {
            .block-container {
                padding-left: .8rem;
                padding-right: .8rem;
            }

            .page-title {
                font-size: 25px;
            }

            .kpi-card {
                min-height: 108px;
            }
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

st.sidebar.markdown(
    """
    <div class="sidebar-brand">
        <div class="brand-icon">📦</div>
        <div class="brand-title">CONTROLE DE ESTOQUE</div>
        <div class="brand-subtitle">Gestão e rastreabilidade de materiais</div>
    </div>
    """,
    unsafe_allow_html=True
)

pagina = st.sidebar.radio(
    "NAVEGAÇÃO",
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

st.sidebar.markdown(
    """
    <div style="font-size:12px;color:#cbd5e1 !important;line-height:1.6;">
        <b>Operação</b><br>
        Controle de entradas, retiradas e rastreabilidade.<br><br>
        <span style="opacity:.75;">Sistema independente do DDH</span>
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# DASHBOARD
# ============================================================

if pagina == "📊 Dashboard":

    st.markdown(
        """
        <div class="page-header">
            <div>
                <div class="page-title">📦 Dashboard</div>
                <div class="page-subtitle">Visão geral do estoque e das movimentações</div>
            </div>
            <div class="header-badge">● SISTEMA ONLINE</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    estoque = buscar_estoque()
    movimentos = buscar_movimentacoes()

    df_estoque = pd.DataFrame(estoque)
    df_mov = pd.DataFrame(movimentos)

    total_materiais = len(df_estoque)
    estoque_baixo = 0

    if not df_estoque.empty and "estoque_baixo" in df_estoque.columns:
        estoque_baixo = int(
            df_estoque["estoque_baixo"].fillna(False).astype(bool).sum()
        )

    hoje = datetime.now().date()
    retiradas_hoje = 0
    entradas_hoje = 0

    if not df_mov.empty and "data_hora" in df_mov.columns:
        datas = pd.to_datetime(df_mov["data_hora"], errors="coerce").dt.date
        hoje_df = df_mov[datas == hoje]

        if "tipo" in hoje_df.columns:
            retiradas_hoje = int((hoje_df["tipo"] == "RETIRADA").sum())
            entradas_hoje = int((hoje_df["tipo"] == "ENTRADA").sum())

    # KPIs
    k1, k2, k3, k4 = st.columns(4)

    cards = [
        ("📦", "Materiais cadastrados", total_materiais, "Itens ativos no catálogo"),
        ("📤", "Retiradas hoje", retiradas_hoje, "Movimentações de saída"),
        ("📥", "Entradas hoje", entradas_hoje, "Movimentações de entrada"),
        ("⚠️", "Estoque baixo", estoque_baixo, "Materiais que precisam de atenção"),
    ]

    for col, (icon, label, value, caption) in zip([k1, k2, k3, k4], cards):
        with col:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-top">
                        <span>{label}</span>
                        <span class="kpi-icon">{icon}</span>
                    </div>
                    <div class="kpi-value">{value}</div>
                    <div class="kpi-caption">{caption}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # Ações rápidas
    st.markdown('<div class="panel-title">Acesso rápido</div>', unsafe_allow_html=True)
    qa1, qa2, qa3 = st.columns(3)

    with qa1:
        st.markdown(
            '<div class="quick-action">📤<br><b>Nova Retirada</b><br><small>Registrar saída de materiais</small></div>',
            unsafe_allow_html=True
        )
    with qa2:
        st.markdown(
            '<div class="quick-action">📦<br><b>Estoque Atual</b><br><small>Consultar saldos</small></div>',
            unsafe_allow_html=True
        )
    with qa3:
        st.markdown(
            '<div class="quick-action">🔄<br><b>Movimentações</b><br><small>Consultar histórico</small></div>',
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    left, right = st.columns([1.7, 1])

    with left:
        st.markdown(
            """
            <div class="panel">
                <div class="panel-title">🔄 Últimas movimentações</div>
                <div class="panel-subtitle">Atividades mais recentes registradas no sistema</div>
            """,
            unsafe_allow_html=True
        )

        if df_mov.empty:
            st.markdown(
                '<div class="empty-state">📭<br><br>Nenhuma movimentação registrada.</div>',
                unsafe_allow_html=True
            )
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
                ] if c in df_mov.columns
            ]
            st.dataframe(
                df_mov[colunas].head(15),
                use_container_width=True,
                hide_index=True
            )

        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown(
            """
            <div class="panel">
                <div class="panel-title">⚠️ Atenção no estoque</div>
                <div class="panel-subtitle">Materiais próximos ou abaixo do mínimo</div>
            """,
            unsafe_allow_html=True
        )

        if not df_estoque.empty and "estoque_baixo" in df_estoque.columns:
            baixos = df_estoque[
                df_estoque["estoque_baixo"].fillna(False).astype(bool)
            ].copy()

            if baixos.empty:
                st.success("✓ Nenhum material com estoque baixo.")
            else:
                for _, row in baixos.head(8).iterrows():
                    desc = row.get("descricao", "Material")
                    qtd = row.get("quantidade", 0)
                    unidade = row.get("unidade", "un")
                    st.markdown(
                        f"""
                        <div class="step-card">
                            <b>{desc}</b><br>
                            <span class="stock-low">Estoque: {qtd:g} {unidade}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
        else:
            st.info("Não foi possível calcular os alertas.")

        st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# CADASTRO DE MATERIAIS
# ============================================================

elif pagina == "📦 Cadastro de Materiais":

    st.markdown(
        '<div class="page-title">📦 Cadastro de Materiais</div>'
        '<div class="page-subtitle">Cadastre e configure os materiais utilizados nas operações.</div>',
        unsafe_allow_html=True
    )

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

    st.markdown(
        '<div class="page-title">📤 Nova Retirada</div>'
        '<div class="page-subtitle">Registre uma saída de materiais com rastreabilidade completa.</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="panel">
            <div class="panel-title">📋 Como funciona</div>
            <div class="panel-subtitle">
                Escolha o destino, adicione os materiais, confira os responsáveis
                e registre a movimentação.
            </div>
            <span class="movement-chip chip-success">1 DESTINO</span>
            &nbsp;&nbsp;
            <span class="movement-chip chip-success">2 MATERIAIS</span>
            &nbsp;&nbsp;
            <span class="movement-chip chip-success">3 CONFERÊNCIA</span>
            &nbsp;&nbsp;
            <span class="movement-chip chip-success">4 REGISTRO</span>
        </div>
        """,
        unsafe_allow_html=True
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
        f"""
        <div class="panel">
            <div class="panel-title">Movimentação <span style="color:#18324a;">{numero}</span></div>
            <div class="panel-subtitle">Número gerado automaticamente para rastreabilidade.</div>
        </div>
        """,
        unsafe_allow_html=True
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

    st.markdown(
        '<div class="section-label">Etapa 2 · Materiais da retirada</div>',
        unsafe_allow_html=True
    )

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

    st.markdown(
        '<div class="section-label">Etapa 3 · Responsáveis</div>',
        unsafe_allow_html=True
    )

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

    st.markdown(
        '<div class="section-label">Etapa 4 · Conferência</div>',
        unsafe_allow_html=True
    )

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

    st.markdown(
        '<div class="section-label">Conferência final</div>',
        unsafe_allow_html=True
    )

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
        "📤 CONFIRMAR E REGISTRAR RETIRADA",
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

    st.markdown(
        '<div class="page-title">📋 Estoque Atual</div>'
        '<div class="page-subtitle">Consulte saldos, limites e disponibilidade dos materiais.</div>',
        unsafe_allow_html=True
    )

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

    st.markdown(
        '<div class="page-title">🔄 Movimentações</div>'
        '<div class="page-subtitle">Histórico de entradas e retiradas registradas.</div>',
        unsafe_allow_html=True
    )

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

    st.markdown(
        '<div class="page-title">🏗️ Destinos / Sondas</div>'
        '<div class="page-subtitle">Gerencie os locais e sondas que recebem materiais.</div>',
        unsafe_allow_html=True
    )

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

    st.markdown(
        '<div class="page-title">👥 Usuários</div>'
        '<div class="page-subtitle">Gerencie os responsáveis pelas movimentações.</div>',
        unsafe_allow_html=True
    )

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


# ============================================================
# RODAPÉ
# ============================================================
st.markdown(
    """
    <div style="
        margin-top:35px;
        padding:15px 4px;
        border-top:1px solid #e5e7eb;
        color:#8a94a0;
        font-size:11px;
        text-align:center;">
        Controle de Estoque • Gestão de materiais e rastreabilidade
    </div>
    """,
    unsafe_allow_html=True
)
