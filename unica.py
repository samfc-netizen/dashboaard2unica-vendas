# unica.py
# Dashboard 2 - Única (Streamlit)
# Arquivo esperado na raiz do projeto: "base unica.xlsx"
import re
import unicodedata
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import plotly.colors as pc
import os
import glob
# =========================
# Config
# =========================
st.set_page_config(page_title="Dashboard 2 - Única", layout="wide")
st.title("Dashboard 2 - Única")
ARQUIVO_EXCEL = "base unica.xlsx"
MESES_PT = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
MES_NUM_TO_PT = {i + 1: m for i, m in enumerate(MESES_PT)}
# Ano-1 fixo (2025)
ANO_1 = 2025
ANO_1_MENSAL = {
    "JAN": 493_158.44,
    "FEV": 382_424.17,
    "MAR": 476_689.32,
    "ABR": 464_330.59,
    "MAI": 464_307.79,
    "JUN": 520_859.42,
    "JUL": 616_920.50,
    "AGO": 637_669.46,
    "SET": 566_804.74,
    "OUT": 657_211.74,
    "NOV": 562_471.16,
    "DEZ": 458_387.05,
}
# Metas fixas (mensal)
METAS_MENSAL = {
    "JAN": 601_653.30,
    "FEV": 466_557.49,
    "MAR": 581_560.97,
    "ABR": 566_483.32,
    "MAI": 566_455.50,
    "JUN": 635_448.49,
    "JUL": 752_643.01,
    "AGO": 777_956.74,
    "SET": 691_501.78,
    "OUT": 801_798.32,
    "NOV": 686_214.82,
    "DEZ": 559_232.20,
}
DIAS_UTEIS_MENSAL = {
    "JAN": 21,
    "FEV": 18,
    "MAR": 22,
    "ABR": 20,
    "MAI": 20,
    "JUN": 21,
    "JUL": 23,
    "AGO": 21,
    "SET": 21,
    "OUT": 21,
    "NOV": 20,
    "DEZ": 21,
}
# =========================
# Helpers
# =========================
def normalize_col(s: str) -> str:
    s = str(s).strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\s+", " ", s)
    return s.upper()
def norm_text(s) -> str:
    s = "" if s is None else str(s)
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s
def format_brl(v) -> str:
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return "—"
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"
def parse_brl_number(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    s = str(v).strip()
    if s == "" or s.lower() in {"nan", "none"}:
        return None
    s = s.replace("R$", "").replace("\u00a0", " ").strip()
    s = re.sub(r"[^\d,.\-]", "", s)
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    else:
        if "," in s and "." not in s:
            s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None
def month_key_from_monthnum(m: int) -> str:
    return MES_NUM_TO_PT.get(int(m), "")
def fmt_pct(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    return f"{x:,.1f}%".replace(",", "X").replace(".", ",").replace("X", ".")
def split_city_uf(city_raw: str):
    """
    Ex.: 'SOBRADINHO- DF' / 'SOBRADINHO -DF' / 'SOBRADINHO-DF'
    Retorna: (UF, CIDADE_LIMPA)
    """
    s = norm_text(city_raw)
    if not s or s.lower() == "nan":
        return "N/I", "N/I"
    s_up = s.upper()
    m = re.search(r"(?:\s*-\s*|\s+)([A-Z]{2})\s*$", s_up)
    if m:
        uf = m.group(1)
        cidade = re.sub(r"(?:\s*-\s*|\s+)[A-Z]{2}\s*$", "", s, flags=re.IGNORECASE).strip()
        return (uf if uf else "N/I"), (cidade if cidade else "N/I")
    return "N/I", s
def build_static_color_map(categories, palette):
    cats = [c for c in categories if c is not None and str(c).strip() != "" and str(c).lower() != "nan"]
    cats = sorted(set([str(c).strip() for c in cats]), key=lambda x: x.upper())
    return {cat: palette[i % len(palette)] for i, cat in enumerate(cats)}
def style_diff_column(df_show: pd.DataFrame, diff_col_name: str):
    def _style(v):
        try:
            x = float(v)
        except Exception:
            return ""
        if x > 0:
            return "color:#0B5ED7;font-weight:700;"  # azul
        if x < 0:
            return "color:#DC3545;font-weight:700;"  # vermelho
        return ""
    return df_show.style.applymap(_style, subset=[diff_col_name])
def metric_card(title: str, value: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div style="
            border: 1px solid rgba(255,255,255,0.10);
            background: rgba(255,255,255,0.03);
            border-radius: 16px;
            padding: 14px 14px;
            box-shadow: 0 8px 22px rgba(0,0,0,0.10);
            height: 92px;
            display:flex;
            flex-direction:column;
            justify-content:center;
        ">
            <div style="font-size:12px; opacity:0.75; margin-bottom:6px;">{title}</div>
            <div style="font-size:22px; font-weight:800; line-height:1.1;">{value}</div>
            <div style="font-size:12px; opacity:0.65; margin-top:6px;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
@st.cache_data(show_spinner=False)
def load_base(path: str, mtime: float):
    xls = pd.ExcelFile(path)
    sheet0 = xls.sheet_names[0]
    df0 = pd.read_excel(xls, sheet_name=sheet0)
    return sheet0, df0
def compress_region_table(reg_tbl: pd.DataFrame, top_n: int = 500) -> pd.DataFrame:
    """
    Reduz complexidade do mapa em "TODOS": mantém TOP N bairros e agrega o resto em OUTROS.
    """
    if reg_tbl is None or reg_tbl.empty:
        return reg_tbl
    reg_tbl = reg_tbl.copy()
    reg_tbl = reg_tbl.rename(columns={"FAT (R$)": "FAT"}).sort_values("FAT", ascending=False)
    if len(reg_tbl) <= top_n:
        reg_tbl["FAT (R$)"] = reg_tbl["FAT"]
        return reg_tbl.drop(columns=["FAT"])
    top = reg_tbl.head(top_n).copy()
    rest = reg_tbl.iloc[top_n:].copy()
    rest_agg = (
        rest.groupby(["UF", "CIDADE_LIMPA"], as_index=False)["FAT"]
        .sum()
        .assign(BAIRRO="OUTROS")
    )
    out = pd.concat([top, rest_agg], ignore_index=True)
    out["FAT (R$)"] = out["FAT"]
    return out.drop(columns=["FAT"])
# =========================
# Load data
# =========================
with st.spinner("Carregando base..."):
    try:
        mtime = os.path.getmtime(ARQUIVO_EXCEL)
        sheet, raw = load_base(ARQUIVO_EXCEL, mtime)
    except FileNotFoundError:
        st.error("❌ Arquivo não encontrado.")
        st.info("Confirme que o Excel está na raiz do projeto e com o nome EXATO:")
        st.code(ARQUIVO_EXCEL)
        st.info("Arquivos encontrados na raiz do app:")
        st.code("\\n".join(sorted(glob.glob("*"))))
        st.stop()
    except Exception as e:
        st.error("❌ Erro ao abrir a planilha.")
        st.exception(e)
        st.stop()
df = raw.copy()
df.columns = [normalize_col(c) for c in df.columns]
required = {"DATA", "VR.TOTAL"}
missing = sorted(list(required - set(df.columns)))
if missing:
    st.error("❌ Colunas obrigatórias ausentes na base:")
    st.code("\n".join(missing))
    st.stop()
df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce", dayfirst=True)
df = df[df["DATA"].notna()].copy()
if df.empty:
    st.error("❌ Nenhuma linha com DATA válida encontrada.")
    st.stop()
df["VR_TOTAL"] = df["VR.TOTAL"].apply(parse_brl_number).fillna(0.0)
df["CUSTO_NUM"] = df["CUSTO"].apply(parse_brl_number).fillna(0.0) if "CUSTO" in df.columns else 0.0
df["ANO"] = df["DATA"].dt.year
df["MES_NUM"] = df["DATA"].dt.month
df["MES"] = df["MES_NUM"].map(month_key_from_monthnum)
df["DIA"] = df["DATA"].dt.date
# =========================
# Sidebar filtros
# =========================
min_dt = df["DATA"].min().date()
max_dt = df["DATA"].max().date()
if "vendedor_sel" not in st.session_state:
    st.session_state["vendedor_sel"] = "TODOS"
with st.sidebar:
    st.header("Filtros")
    st.caption("Atualização de dados")
    if st.button("🔄 Recarregar base (limpar cache)"):
        st.cache_data.clear()
        st.rerun()
    dt_ini, dt_fim = st.date_input(
        "Período (DATA)",
        value=(min_dt, max_dt),
        min_value=min_dt,
        max_value=max_dt,
    )
    if isinstance(dt_ini, (tuple, list)):
        dt_ini, dt_fim = dt_ini[0], dt_ini[1]
    vendedor_sel = "TODOS"
    if "VENDEDOR" in df.columns:
        df_dt = df[(df["DIA"] >= dt_ini) & (df["DIA"] <= dt_fim)].copy()
        vend_opts = (
            df_dt["VENDEDOR"].fillna("").astype(str).map(norm_text).replace("", pd.NA).dropna().unique().tolist()
            if not df_dt.empty
            else df["VENDEDOR"].fillna("").astype(str).map(norm_text).replace("", pd.NA).dropna().unique().tolist()
        )
        vend_opts = sorted(set(vend_opts), key=lambda x: x.upper())
        vend_opts = ["TODOS"] + vend_opts
        cur = st.session_state.get("vendedor_sel", "TODOS")
        if cur not in vend_opts:
            cur = "TODOS"
            st.session_state["vendedor_sel"] = cur
        vendedor_sel = st.selectbox("Selecionar vendedor", options=vend_opts, index=vend_opts.index(cur))
        st.session_state["vendedor_sel"] = vendedor_sel
    else:
        st.info("Coluna VENDEDOR não encontrada (filtro por vendedor indisponível).")
# =========================
# Dataframes filtrados
# =========================
mask_dt = (df["DIA"] >= dt_ini) & (df["DIA"] <= dt_fim)
df_periodo_all = df.loc[mask_dt].copy()
if df_periodo_all.empty:
    st.warning("Nenhum dado encontrado no período selecionado.")
    st.stop()
if vendedor_sel != "TODOS" and "VENDEDOR" in df_periodo_all.columns:
    df_periodo = df_periodo_all[
        df_periodo_all["VENDEDOR"].fillna("").astype(str).map(norm_text) == norm_text(vendedor_sel)
    ].copy()
else:
    df_periodo = df_periodo_all.copy()
ano_atual = int(df_periodo_all["ANO"].max())
palette = (
    pc.qualitative.Plotly
    + pc.qualitative.D3
    + pc.qualitative.Set2
    + pc.qualitative.Safe
    + pc.qualitative.Dark24
)
segmentos_base = (
    df_periodo_all["SEGMENTO"].fillna("").astype(str).map(norm_text).replace("", pd.NA).dropna().tolist()
    if "SEGMENTO" in df_periodo_all.columns
    else []
)
SEGMENTO_COLOR_MAP = build_static_color_map(segmentos_base, palette)
# =========================
# SEÇÃO 1 — Indicadores
# =========================
faturamento_periodo = float(df_periodo["VR_TOTAL"].sum()) if not df_periodo.empty else 0.0
custo_periodo = float(df_periodo["CUSTO_NUM"].sum()) if not df_periodo.empty else 0.0
markup = (faturamento_periodo / custo_periodo) if custo_periodo else None
clientes_ativos = (
    df_periodo["CLIENTE"].fillna("").astype(str).map(norm_text).replace("", pd.NA).dropna().nunique()
    if (not df_periodo.empty and "CLIENTE" in df_periodo.columns)
    else 0
)
if not df_periodo.empty:
    vpd = df_periodo.groupby("DIA", as_index=False)["VR_TOTAL"].sum()
    vpd = vpd[vpd["VR_TOTAL"] > 0]
    media_dia = float(vpd["VR_TOTAL"].mean()) if not vpd.empty else 0.0
else:
    media_dia = 0.0
mes_ref_num = pd.to_datetime(dt_fim).month
mes_ref = month_key_from_monthnum(mes_ref_num)
dias_uteis_ref = int(DIAS_UTEIS_MENSAL.get(mes_ref, 0))
if not df_periodo.empty:
    df_mes_ref = df_periodo[df_periodo["MES_NUM"] == mes_ref_num].copy()
    vpd_mes = df_mes_ref.groupby("DIA", as_index=False)["VR_TOTAL"].sum()
    vpd_mes = vpd_mes[vpd_mes["VR_TOTAL"] > 0]
    media_dia_mes = float(vpd_mes["VR_TOTAL"].mean()) if not vpd_mes.empty else 0.0
else:
    media_dia_mes = 0.0
previsao_mes = media_dia_mes * dias_uteis_ref
st.markdown("## Indicadores")
r1 = st.columns(4)
r2 = st.columns(3)
with r1[0]:
    metric_card("Faturamento (Período)", format_brl(faturamento_periodo), f"{dt_ini} → {dt_fim}")
with r1[1]:
    metric_card("Ano Atual (no período)", str(ano_atual), "Base: DATA filtrada")
with r1[2]:
    metric_card("Vendedor (filtro)", vendedor_sel, "TODOS = sem recorte")
with r1[3]:
    metric_card("Clientes Ativos (período)", f"{clientes_ativos:,}".replace(",", "."), "Clientes únicos")
with r2[0]:
    metric_card("Média diária (dias c/ venda)", format_brl(media_dia), "Ignora dias zerados")
with r2[1]:
    metric_card(f"Previsão (mês {mes_ref})", format_brl(previsao_mes), f"{dias_uteis_ref} dias úteis")
with r2[2]:
    metric_card(
        "Markup (Fat/Custo)",
        ("—" if markup is None else f"{markup:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
        "Σ Fat ÷ Σ Custo",
    )
st.divider()
# =========================
# SEÇÃO 2 — Ano-1 vs Ano Atual
# =========================
st.markdown("## Ano-1 vs Ano Atual")
df_atual = df_periodo[df_periodo["ANO"] == ano_atual].copy() if not df_periodo.empty else df_periodo.copy()
real_mensal_atual = (
    df_atual.groupby("MES", as_index=False)["VR_TOTAL"].sum()
    if not df_atual.empty
    else pd.DataFrame({"MES": [], "VR_TOTAL": []})
)
base_meses = pd.DataFrame({"MES": MESES_PT})
tbl = base_meses.merge(real_mensal_atual, on="MES", how="left").rename(columns={"VR_TOTAL": f"REAL_{ano_atual}"})
tbl[f"REAL_{ano_atual}"] = tbl[f"REAL_{ano_atual}"].fillna(0.0)
tbl[f"ANO-1_{ANO_1}"] = tbl["MES"].map(ANO_1_MENSAL).fillna(0.0)
tbl["DIF_NUM"] = tbl[f"REAL_{ano_atual}"] - tbl[f"ANO-1_{ANO_1}"]
tbl["CRESC (%)"] = tbl.apply(
    lambda r: (r["DIF_NUM"] / r[f"ANO-1_{ANO_1}"] * 100) if r[f"ANO-1_{ANO_1}"] != 0 else None,
    axis=1,
)
meses_no_periodo_ano_atual = sorted(
    df_periodo_all[df_periodo_all["ANO"] == ano_atual]["MES"].dropna().unique().tolist(),
    key=lambda x: MESES_PT.index(x),
)
tbl_periodo = tbl[tbl["MES"].isin(meses_no_periodo_ano_atual)].copy() if meses_no_periodo_ano_atual else tbl.copy()
total_atual_periodo_meses = float(tbl_periodo[f"REAL_{ano_atual}"].sum())
total_ano1_periodo_meses = float(tbl_periodo[f"ANO-1_{ANO_1}"].sum())
dif_total = total_atual_periodo_meses - total_ano1_periodo_meses
cres_total = (dif_total / total_ano1_periodo_meses * 100) if total_ano1_periodo_meses else None
c1, c2, c3 = st.columns(3)
c1.metric(f"Total {ano_atual} (meses do período)", format_brl(total_atual_periodo_meses))
c2.metric(f"Total {ANO_1} (fixo, mesmos meses)", format_brl(total_ano1_periodo_meses))
c3.metric("Diferença / Crescimento", f"{format_brl(dif_total)}  |  {('—' if cres_total is None else fmt_pct(cres_total))}")
with st.expander("Abrir tabela Ano-1 vs Ano Atual (por mês)"):
    df_disp = pd.DataFrame(
        {
            "MES": tbl["MES"],
            f"ANO-1_{ANO_1}": tbl[f"ANO-1_{ANO_1}"].map(format_brl),
            f"REAL_{ano_atual}": tbl[f"REAL_{ano_atual}"].map(format_brl),
            "DIF (R$)": tbl["DIF_NUM"],
            "CRESC (%)": tbl["CRESC (%)"].apply(fmt_pct),
        }
    )
    sty = style_diff_column(df_disp, "DIF (R$)").format({"DIF (R$)": lambda x: format_brl(x)})
    st.dataframe(sty, use_container_width=True, hide_index=True)
st.divider()
# =========================
# SEÇÃO 3 — Metas
# =========================
st.markdown("## Metas (Período)")
meses_meta = meses_no_periodo_ano_atual if meses_no_periodo_ano_atual else MESES_PT
meta_periodo = float(sum(METAS_MENSAL.get(m, 0.0) for m in meses_meta))
pct_meta = (faturamento_periodo / meta_periodo * 100) if meta_periodo else 0.0
m1, m2, m3 = st.columns(3)
m1.metric("Meta (meses do período)", format_brl(meta_periodo))
m2.metric("Realizado (período)", format_brl(faturamento_periodo))
m3.metric("% Meta atingida", fmt_pct(pct_meta))
fig_gauge = go.Figure(
    go.Indicator(
        mode="gauge+number",
        value=pct_meta,
        number={"suffix": "%"},
        gauge={
            "axis": {"range": [0, 120]},
            "bar": {"thickness": 0.25},
            "steps": [
                {"range": [0, 80], "color": "lightgray"},
                {"range": [80, 100], "color": "gray"},
                {"range": [100, 120], "color": "darkgray"},
            ],
            "threshold": {"line": {"width": 4}, "thickness": 0.75, "value": 100},
        },
        title={"text": "% da Meta Atingida (Período)"},
    )
)
fig_gauge.update_layout(height=260, margin=dict(l=10, r=10, t=60, b=10))
st.plotly_chart(fig_gauge, use_container_width=True)
with st.expander("Abrir tabela Meta x Realizado (por mês)"):
    real_mensal = (
        df_atual.groupby("MES", as_index=False)["VR_TOTAL"].sum()
        if not df_atual.empty
        else pd.DataFrame({"MES": [], "VR_TOTAL": []})
    )
    tbl_m = pd.DataFrame({"MES": MESES_PT})
    tbl_m = tbl_m.merge(real_mensal, on="MES", how="left").rename(columns={"VR_TOTAL": "REAL_NUM"})
    tbl_m["REAL_NUM"] = tbl_m["REAL_NUM"].fillna(0.0)
    tbl_m["META_NUM"] = tbl_m["MES"].map(METAS_MENSAL).fillna(0.0)
    tbl_m["DIF_NUM"] = tbl_m["REAL_NUM"] - tbl_m["META_NUM"]
    tbl_m["% ATING."] = tbl_m.apply(lambda r: (r["REAL_NUM"] / r["META_NUM"] * 100) if r["META_NUM"] else None, axis=1)
    df_disp = pd.DataFrame(
        {
            "MES": tbl_m["MES"],
            "META (R$)": tbl_m["META_NUM"].map(format_brl),
            "REAL (R$)": tbl_m["REAL_NUM"].map(format_brl),
            "DIF (R$)": tbl_m["DIF_NUM"],
            "% ATING.": tbl_m["% ATING."].apply(fmt_pct),
        }
    )
    sty = style_diff_column(df_disp, "DIF (R$)").format({"DIF (R$)": lambda x: format_brl(x)})
    st.dataframe(sty, use_container_width=True, hide_index=True)
st.divider()
# =========================
# SEÇÃO 4 — Produtos (Marcas / Segmentos)
# =========================
st.markdown("## Produtos")
cA, cB = st.columns([1.2, 1.0])
with cA:
    st.subheader("Top 10 Marcas")
    if (not df_periodo.empty) and ("MARCA" in df_periodo.columns):
        total_geral = float(df_periodo["VR_TOTAL"].sum()) if len(df_periodo) else 0.0
        marcas = (
            df_periodo.groupby("MARCA", as_index=False)["VR_TOTAL"].sum()
            .sort_values("VR_TOTAL", ascending=False)
            .rename(columns={"VR_TOTAL": "FAT (R$)"})
        )
        marcas["% SOBRE TOTAL"] = marcas["FAT (R$)"].apply(lambda x: (x / total_geral * 100) if total_geral else None)
        top10 = marcas.head(10).copy()
        top10_show = top10.copy()
        top10_show["FAT (R$)"] = top10_show["FAT (R$)"].map(format_brl)
        top10_show["% SOBRE TOTAL"] = top10["% SOBRE TOTAL"].apply(fmt_pct)
        st.dataframe(top10_show, use_container_width=True, hide_index=True)
        resto = marcas.iloc[10:].copy()
        if not resto.empty:
            with st.expander("Ver demais marcas (drill)"):
                resto_show = resto.copy()
                resto_show["FAT (R$)"] = resto_show["FAT (R$)"].map(format_brl)
                resto_show["% SOBRE TOTAL"] = resto["% SOBRE TOTAL"].apply(fmt_pct)
                st.dataframe(resto_show, use_container_width=True, hide_index=True)
    else:
        st.info("Sem dados (ou coluna MARCA ausente) para o período/vendedor selecionado.")
with cB:
    st.subheader("Faturamento por Segmento (Pizza)")
    if (not df_periodo.empty) and ("SEGMENTO" in df_periodo.columns):
        seg = (
            df_periodo.groupby("SEGMENTO", as_index=False)["VR_TOTAL"].sum()
            .sort_values("VR_TOTAL", ascending=False)
            .rename(columns={"VR_TOTAL": "FAT (R$)"})
        )
        fig_seg = px.pie(
            seg,
            names="SEGMENTO",
            values="FAT (R$)",
            color="SEGMENTO",
            color_discrete_map=SEGMENTO_COLOR_MAP,
            title="Distribuição por Segmento (período)",
        )
        fig_seg.update_layout(height=420)
        st.plotly_chart(fig_seg, use_container_width=True)
    else:
        st.info("Sem dados (ou coluna SEGMENTO ausente) para o período/vendedor selecionado.")
st.divider()
# =========================
# SEÇÃO 5 — Clientes & Regiões (MAPA + EVOLUÇÃO DE CLIENTES)
# =========================
st.markdown("## Clientes & Regiões")
has_city = "CIDADE" in df_periodo_all.columns
has_bairro = "BAIRRO" in df_periodo_all.columns
has_cliente = "CLIENTE" in df_periodo_all.columns
if has_city and has_bairro and has_cliente:
    # Base do mapa: período SEMPRE.
    reg = df_periodo_all.copy()
    if vendedor_sel != "TODOS" and "VENDEDOR" in reg.columns:
        reg = reg[reg["VENDEDOR"].fillna("").astype(str).map(norm_text) == norm_text(vendedor_sel)].copy()
    # >>> CORREÇÃO PRINCIPAL DO "BRANCO EM TODOS":
    # Plotly Sunburst/Treemap não lida bem com valores negativos.
    # Quando está em TODOS, entram devoluções/ajustes e pode ficar "em branco".
    # Então o mapa usa SOMENTE vendas positivas.
    reg = reg[reg["VR_TOTAL"] > 0].copy()
    if reg.empty:
        st.warning("Mapa: não há vendas positivas para o filtro atual (período/vendedor).")
    else:
        reg["CIDADE"] = reg["CIDADE"].fillna("N/I").astype(str).map(norm_text)
        reg["BAIRRO"] = reg["BAIRRO"].fillna("N/I").astype(str).map(norm_text)
        reg["CLIENTE"] = reg["CLIENTE"].fillna("N/I").astype(str).map(norm_text)
        uf_city = reg["CIDADE"].apply(split_city_uf)
        reg["UF"] = uf_city.map(lambda x: x[0])
        reg["CIDADE_LIMPA"] = uf_city.map(lambda x: x[1])
        reg_tbl = (
            reg.groupby(["UF", "CIDADE_LIMPA", "BAIRRO"], as_index=False)["VR_TOTAL"]
            .sum()
            .rename(columns={"VR_TOTAL": "FAT (R$)"})
            .sort_values("FAT (R$)", ascending=False)
        )
        reg_tbl_plot = compress_region_table(reg_tbl, top_n=500)
        st.subheader("Mapa de Regiões e Faturamento (UF → Cidade → Bairro)")
        # Sunburst (e fallback automático pra Treemap se der problema)
        try:
            fig_reg = px.sunburst(reg_tbl_plot, path=["UF", "CIDADE_LIMPA", "BAIRRO"], values="FAT (R$)")
            fig_reg.update_layout(height=540)
            st.plotly_chart(fig_reg, use_container_width=True)
        except Exception:
            fig_tm = px.treemap(reg_tbl_plot, path=["UF", "CIDADE_LIMPA", "BAIRRO"], values="FAT (R$)")
            fig_tm.update_layout(height=540)
            st.plotly_chart(fig_tm, use_container_width=True)
        st.markdown("### Seleção de Região (para listar clientes)")
        colA, colB, colC = st.columns(3)
        uf_opts = sorted(reg["UF"].dropna().unique().tolist())
        uf_sel = colA.selectbox("UF", options=["TODOS"] + uf_opts, index=0, key="UF_SEL")
        reg_f = reg.copy()
        if uf_sel != "TODOS":
            reg_f = reg_f[reg_f["UF"] == uf_sel].copy()
        cid_opts = sorted(reg_f["CIDADE_LIMPA"].dropna().unique().tolist())
        cid_sel = colB.selectbox("Cidade", options=["TODOS"] + cid_opts, index=0, key="CID_SEL")
        if cid_sel != "TODOS":
            reg_f = reg_f[reg_f["CIDADE_LIMPA"] == cid_sel].copy()
        bai_opts = sorted(reg_f["BAIRRO"].dropna().unique().tolist())
        bai_sel = colC.selectbox("Bairro", options=["TODOS"] + bai_opts, index=0, key="BAI_SEL")
        if bai_sel != "TODOS":
            reg_f = reg_f[reg_f["BAIRRO"] == bai_sel].copy()
        if reg_f.empty:
            st.warning("Nenhum dado para a região selecionada.")
        else:
            cli_reg = (
                reg_f.groupby("CLIENTE", as_index=False)["VR_TOTAL"]
                .sum()
                .rename(columns={"VR_TOTAL": "FAT (R$)"})
                .sort_values("FAT (R$)", ascending=False)
            )
            cli_reg_show = cli_reg.copy()
            cli_reg_show["FAT (R$)"] = cli_reg_show["FAT (R$)"].map(format_brl)
            st.metric("Clientes na região (únicos)", f"{cli_reg['CLIENTE'].nunique():,}".replace(",", "."))
            st.dataframe(cli_reg_show, use_container_width=True, hide_index=True)
    st.divider()
    # ===== Evolução de Clientes (DRILL) =====
    st.subheader("Evolução de Clientes (drill)")
    if not df_periodo.empty and "CLIENTE" in df_periodo.columns:
        evo = df_periodo.copy()
        evo["CLIENTE"] = evo["CLIENTE"].fillna("N/I").astype(str).map(norm_text)
        evo["MES_REF"] = evo["DATA"].dt.to_period("M").astype(str)
        evo_tbl = (
            evo.groupby(["MES_REF", "CLIENTE"], as_index=False)["VR_TOTAL"]
            .sum()
            .rename(columns={"VR_TOTAL": "FAT (R$)"})
            .sort_values(["MES_REF", "FAT (R$)"], ascending=[False, False])
        )
        with st.expander("Abrir evolução (mês → cliente → valor)"):
            meses_disp = sorted(evo_tbl["MES_REF"].unique().tolist(), reverse=True)
            mes_pick = st.selectbox("Mês", options=["TODOS"] + meses_disp, index=0, key="EVO_MES")
            evo_f = evo_tbl.copy()
            if mes_pick != "TODOS":
                evo_f = evo_f[evo_f["MES_REF"] == mes_pick].copy()
            busca = st.text_input("Buscar cliente (opcional)", value="", key="EVO_BUSCA").strip()
            if busca:
                evo_f = evo_f[evo_f["CLIENTE"].str.contains(busca, case=False, na=False)].copy()
            evo_show = evo_f.copy()
            evo_show["FAT (R$)"] = evo_show["FAT (R$)"].map(format_brl)
            st.dataframe(evo_show, use_container_width=True, hide_index=True)
    else:
        st.info("Sem dados/coluna CLIENTE para montar Evolução de Clientes.")
else:
    st.info("Preciso das colunas CIDADE, BAIRRO e CLIENTE para o mapa e evolução (alguma está ausente).")
