"""CSS global do app (versão enxuta do tema original)."""
import streamlit as st

CSS = """
<style>
:root{
  --primary:#18324a; --primary-2:#244b6b; --accent:#d58b2a;
  --ok:#198754; --danger:#dc3545; --warn:#d99a19;
  --bg:#f4f6f8; --card:#fff; --text:#1f2937; --muted:#6b7280; --border:#e5e7eb;
}
.stApp{background:var(--bg);}
[data-testid="stHeader"]{background:rgba(244,246,248,.92);}
.block-container{max-width:1500px;padding-top:1.2rem;padding-bottom:3rem;}

/* Sidebar */
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#12283b 0%,#183b56 100%);
  border-right:1px solid rgba(255,255,255,.08);}
section[data-testid="stSidebar"] *{color:#f8fafc !important;}
section[data-testid="stSidebar"] .stRadio label{border-radius:10px;padding:7px 10px;}
section[data-testid="stSidebar"] .stRadio label:hover{background:rgba(255,255,255,.10);}
section[data-testid="stSidebar"] hr{border-color:rgba(255,255,255,.15);}
.brand{padding:10px 6px 16px;}
.brand .t{font-size:19px;font-weight:800;margin-top:6px;letter-spacing:.3px;}
.brand .s{font-size:12px;opacity:.75;margin-top:3px;}

/* Cabeçalho de página */
.page-header{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:14px;}
.page-title{font-size:30px;line-height:1.1;font-weight:800;color:var(--text);letter-spacing:-.6px;}
.page-sub{color:var(--muted);font-size:14px;margin-top:6px;}
.badge{background:#e8eef4;color:var(--primary);border:1px solid #d6e0e8;padding:7px 13px;
  border-radius:999px;font-size:12px;font-weight:700;white-space:nowrap;}

/* KPI */
.kpi{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:16px 16px 14px;
  min-height:122px;box-shadow:0 5px 18px rgba(15,23,42,.05);transition:transform .18s,box-shadow .18s;}
.kpi:hover{transform:translateY(-2px);box-shadow:0 10px 25px rgba(15,23,42,.09);}
.kpi-top{display:flex;justify-content:space-between;align-items:center;color:var(--muted);font-size:12.5px;font-weight:700;}
.kpi-ico{width:34px;height:34px;display:flex;align-items:center;justify-content:center;border-radius:10px;background:#edf2f7;font-size:18px;}
.kpi-val{margin-top:10px;font-size:28px;font-weight:800;color:var(--text);}
.kpi-cap{color:var(--muted);font-size:11.5px;margin-top:2px;display:flex;gap:6px;align-items:center;flex-wrap:wrap;}
.kpi.warn .kpi-val{color:#b45309;} .kpi.bad .kpi-val{color:#b91c1c;} .kpi.good .kpi-val{color:#166534;}
.delta{font-weight:800;font-size:11px;padding:2px 7px;border-radius:999px;}
.delta.up{color:#166534;background:#dcfce7;} .delta.down{color:#991b1b;background:#fee2e2;}
.delta.flat{color:#475569;background:#e2e8f0;}

/* Blocos */
.sec{color:var(--primary);font-size:13px;font-weight:800;letter-spacing:.4px;text-transform:uppercase;margin:6px 0 8px;}
.panel-t{font-size:16px;font-weight:800;color:var(--text);margin-bottom:2px;}
.panel-s{color:var(--muted);font-size:12px;margin-bottom:8px;}
div[data-testid="stVerticalBlockBorderWrapper"]{background:var(--card);border-radius:16px !important;
  border-color:var(--border) !important;}
.alert{border:1px solid #f0d8a8;background:#fffaf0;border-radius:12px;padding:10px 12px;margin:6px 0;}
.alert.zero{border-color:#f3b4b4;background:#fff5f5;}
.alert .n{color:var(--text);font-size:13px;font-weight:800;}
.alert .q{color:#b91c1c;font-size:12px;font-weight:800;margin-top:2px;}
.alert .m{color:var(--muted);font-size:11px;margin-top:1px;}
.empty{text-align:center;padding:36px 20px;color:var(--muted);background:#fff;border:1px dashed #cfd6de;border-radius:16px;}
.chip{display:inline-block;padding:4px 9px;border-radius:999px;font-size:11px;font-weight:800;}
.chip.ok{color:#166534;background:#dcfce7;} .chip.warn{color:#854d0e;background:#fef3c7;}
.chip.bad{color:#991b1b;background:#fee2e2;}

/* Widgets */
.stButton>button,.stDownloadButton>button,.stFormSubmitButton>button{border-radius:10px;min-height:42px;font-weight:700;border:1px solid #d7dee5;}
.stButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"]{background:var(--primary);border-color:var(--primary);color:#fff;}
div[data-testid="stDataFrame"]{border-radius:12px;overflow:hidden;border:1px solid var(--border);}

@media (max-width:800px){
  .block-container{padding-left:.8rem;padding-right:.8rem;}
  .page-title{font-size:24px;} .kpi{min-height:100px;} .page-header{flex-direction:column;align-items:flex-start;}
}
</style>
"""


def aplicar() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
