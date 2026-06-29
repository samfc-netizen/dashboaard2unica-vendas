# unica.py
# Dashboard 2 - Única (Streamlit)
# Arquivo esperado na raiz do projeto: "base unica.xlsx"
import re
import io
import html
from datetime import datetime
import unicodedata
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
import plotly.graph_objects as go
import plotly.colors as pc
import os
import glob
import json

# =========================
# Gemini / Google AI
# =========================
# Compatível com o SDK novo (google-genai) e com o SDK antigo (google-generativeai).
# No requirements.txt, recomenda-se adicionar:
# google-genai
try:
    from google import genai as genai_new
except Exception:
    genai_new = None

try:
    import google.generativeai as genai_legacy
except Exception:
    genai_legacy = None

# Mantém compatibilidade com validações antigas do código
genai = genai_new if genai_new is not None else genai_legacy
# =========================
# Config
# =========================
st.set_page_config(page_title="Dashboard 2 - Única", layout="wide")
st.title("Dashboard 2 - Única")

st.markdown("""
<style>
/* Botões PDF compactos e discretos */
div.stDownloadButton {
    display: inline-block !important;
    width: auto !important;
    margin-top: 0.35rem !important;
    margin-bottom: 0.75rem !important;
}
div.stDownloadButton > button {
    background: linear-gradient(90deg, #ff4b4b, #ff7a00) !important;
    color: white !important;
    font-weight: 700 !important;
    border-radius: 12px !important;
    border: none !important;
    padding: 0.55rem 1.05rem !important;
    font-size: 0.88rem !important;
    min-height: 38px !important;
    width: auto !important;
    box-shadow: 0px 3px 9px rgba(0,0,0,0.18) !important;
    transition: all 0.20s ease-in-out !important;
}
div.stDownloadButton > button:hover {
    transform: translateY(-1px);
    background: linear-gradient(90deg, #ff2d2d, #ff5e00) !important;
    color: #ffffff !important;
    box-shadow: 0px 4px 12px rgba(0,0,0,0.22) !important;
}
div.stDownloadButton > button:focus {
    outline: none !important;
    border: none !important;
    box-shadow: 0px 3px 9px rgba(0,0,0,0.18) !important;
}
div.stDownloadButton > button p {
    color: white !important;
    font-weight: 700 !important;
    margin: 0 !important;
    white-space: nowrap !important;
}
</style>
""", unsafe_allow_html=True)

ARQUIVO_EXCEL = "base unica.xlsx"
MESES_PT = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
MES_NUM_TO_PT = {i + 1: m for i, m in enumerate(MESES_PT)}
DIAS_SEMANA_PT = {
    "Monday": "Segunda-feira",
    "Tuesday": "Terça-feira",
    "Wednesday": "Quarta-feira",
    "Thursday": "Quinta-feira",
    "Friday": "Sexta-feira",
    "Saturday": "Sábado",
    "Sunday": "Domingo",
}
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

def find_col(cols, exact=None, must_contain=None):
    """Return first matching column name from an iterable of column names (already normalized)."""
    cols = list(cols)
    if exact:
        for c in exact:
            if c in cols:
                return c
    if must_contain:
        # must_contain: list[str] where each str must be contained in column name
        for col in cols:
            ok = True
            for token in must_contain:
                if token not in col:
                    ok = False
                    break
            if ok:
                return col
    return None

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
            return "color:#0B5ED7;font-weight:700;"
        if x < 0:
            return "color:#DC3545;font-weight:700;"
        return ""
    return df_show.style.map(_style, subset=[diff_col_name])
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


def _pdf_imports():
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        return colors, TA_CENTER, TA_LEFT, A4, landscape, getSampleStyleSheet, ParagraphStyle, cm, SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    except Exception as e:
        raise RuntimeError("Para exportar em PDF, adicione 'reportlab' no requirements.txt e instale com: pip install reportlab") from e


def _prepare_df_for_pdf(df_in: pd.DataFrame, max_rows: int | None = None) -> pd.DataFrame:
    df_pdf = df_in.copy()
    if not isinstance(df_pdf.index, pd.RangeIndex):
        df_pdf = df_pdf.reset_index()
    df_pdf = df_pdf.fillna("").astype(str)
    if max_rows is not None and len(df_pdf) > max_rows:
        df_pdf = df_pdf.head(max_rows).copy()
    return df_pdf


def dataframe_to_pdf_bytes(df_in: pd.DataFrame, titulo: str = "Relatório", subtitulo: str = "", max_rows: int | None = None) -> bytes:
    colors, TA_CENTER, TA_LEFT, A4, landscape, getSampleStyleSheet, ParagraphStyle, cm, SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak = _pdf_imports()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=0.7 * cm,
        leftMargin=0.7 * cm,
        topMargin=0.7 * cm,
        bottomMargin=0.7 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TituloRelatorio", parent=styles["Heading2"], alignment=TA_CENTER, fontSize=13, leading=16, spaceAfter=6)
    subtitle_style = ParagraphStyle("SubtituloRelatorio", parent=styles["BodyText"], alignment=TA_CENTER, fontSize=8, leading=10, textColor=colors.HexColor("#666666"), spaceAfter=8)
    cell_style = ParagraphStyle("CelulaTabela", parent=styles["BodyText"], fontSize=6.3, leading=7.5, wordWrap="CJK")
    header_style = ParagraphStyle("CabecalhoTabela", parent=cell_style, alignment=TA_CENTER, fontName="Helvetica-Bold", textColor=colors.white)

    df_pdf = _prepare_df_for_pdf(df_in, max_rows=max_rows)

    data = [[Paragraph(html.escape(str(c)), header_style) for c in df_pdf.columns]]
    for _, row in df_pdf.iterrows():
        data.append([Paragraph(html.escape(str(v)), cell_style) for v in row.tolist()])

    page_width = landscape(A4)[0] - (1.4 * cm)
    n_cols = max(len(df_pdf.columns), 1)
    col_widths = [page_width / n_cols] * n_cols

    tabela = Table(data, colWidths=col_widths, repeatRows=1, splitByRow=True)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.3),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D9D9D9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FB")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    story = [Paragraph(html.escape(titulo), title_style)]
    if subtitulo:
        story.append(Paragraph(html.escape(subtitulo), subtitle_style))
    story.extend([Spacer(1, 0.2 * cm), tabela])
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def dashboard_to_pdf_bytes(sections: list[dict], titulo: str = "Dashboard Completo - Única", subtitulo: str = "") -> bytes:
    colors, TA_CENTER, TA_LEFT, A4, landscape, getSampleStyleSheet, ParagraphStyle, cm, SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak = _pdf_imports()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=0.7 * cm,
        leftMargin=0.7 * cm,
        topMargin=0.7 * cm,
        bottomMargin=0.7 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TituloDash", parent=styles["Title"], alignment=TA_CENTER, fontSize=16, leading=19, spaceAfter=8)
    subtitle_style = ParagraphStyle("SubtituloDash", parent=styles["BodyText"], alignment=TA_CENTER, fontSize=8, leading=10, textColor=colors.HexColor("#666666"), spaceAfter=10)
    section_style = ParagraphStyle("SecaoDash", parent=styles["Heading2"], alignment=TA_LEFT, fontSize=11, leading=13, spaceBefore=8, spaceAfter=5, textColor=colors.HexColor("#1F4E79"))
    cell_style = ParagraphStyle("CelulaDash", parent=styles["BodyText"], fontSize=6.0, leading=7.2, wordWrap="CJK")
    header_style = ParagraphStyle("HeaderDash", parent=cell_style, alignment=TA_CENTER, fontName="Helvetica-Bold", textColor=colors.white)

    story = [Paragraph(html.escape(titulo), title_style)]
    if subtitulo:
        story.append(Paragraph(html.escape(subtitulo), subtitle_style))
    story.append(Spacer(1, 0.2 * cm))

    page_width = landscape(A4)[0] - (1.4 * cm)

    for i, sec in enumerate(sections):
        name = sec.get("title", f"Seção {i+1}")
        df_sec = sec.get("df", pd.DataFrame())
        max_rows = sec.get("max_rows", None)
        df_pdf = _prepare_df_for_pdf(df_sec, max_rows=max_rows)

        if i > 0:
            story.append(PageBreak())

        story.append(Paragraph(html.escape(name), section_style))

        if df_pdf.empty:
            story.append(Paragraph("Sem dados para esta seção.", cell_style))
            continue

        data = [[Paragraph(html.escape(str(c)), header_style) for c in df_pdf.columns]]
        for _, row in df_pdf.iterrows():
            data.append([Paragraph(html.escape(str(v)), cell_style) for v in row.tolist()])

        n_cols = max(len(df_pdf.columns), 1)
        col_widths = [page_width / n_cols] * n_cols
        tabela = Table(data, colWidths=col_widths, repeatRows=1, splitByRow=True)
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 6.0),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D9D9D9")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FB")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(tabela)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def botao_download_pdf(df_in: pd.DataFrame, titulo: str, nome_arquivo: str, subtitulo: str = "", max_rows: int | None = None):
    try:
        pdf_bytes = dataframe_to_pdf_bytes(df_in, titulo=titulo, subtitulo=subtitulo, max_rows=max_rows)
        st.download_button(
            label=f"Baixar PDF - {titulo}",
            data=pdf_bytes,
            file_name=nome_arquivo,
            mime="application/pdf",
            use_container_width=False,
        )
    except Exception as e:
        st.warning(str(e))


def add_pdf_section(title: str, df_sec: pd.DataFrame, max_rows: int | None = None):
    if "pdf_sections" not in st.session_state:
        st.session_state["pdf_sections"] = []
    try:
        st.session_state["pdf_sections"].append({"title": title, "df": df_sec.copy(), "max_rows": max_rows})
    except Exception:
        pass

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


def build_product_dictionary(df_in: pd.DataFrame, code_col: str, desc_col: str) -> pd.DataFrame:
    """
    Cria uma dimensão de produtos única por CÓDIGO, escolhendo uma DESCRIÇÃO representativa.

    Regra de síntese:
    - Agrupa por código
    - Escolhe a descrição mais frequente; em empate, escolhe a mais longa (mais informativa)
    - No dashboard, sempre exibimos a descrição representativa, mas o código é a chave.
    """
    if df_in is None or df_in.empty:
        return pd.DataFrame(columns=[code_col, desc_col])

    d = df_in[[code_col, desc_col]].copy()
    d[code_col] = d[code_col].astype(str).map(norm_text)
    d[desc_col] = d[desc_col].astype(str).map(norm_text)

    # limpar vazios
    d = d[(d[code_col].notna()) & (d[code_col].astype(str).str.strip() != "")]
    d = d[(d[desc_col].notna()) & (d[desc_col].astype(str).str.strip() != "")]

    if d.empty:
        return pd.DataFrame(columns=[code_col, desc_col])

    # frequência por (código, descrição)
    freq = d.groupby([code_col, desc_col], as_index=False).size().rename(columns={"size": "FREQ"})
    # rank: maior freq, maior comprimento descrição
    freq["_LEN"] = freq[desc_col].astype(str).str.len()
    freq = freq.sort_values([code_col, "FREQ", "_LEN"], ascending=[True, False, False])

    # pega a melhor descrição por código
    best = freq.drop_duplicates(subset=[code_col], keep="first")[[code_col, desc_col]].copy()
    return best

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
# RELATÓRIOS WHATSAPP
# =========================
WHATSAPP_REPORT_UNICA = "5561993215052"


def _safe_dim(df_in: pd.DataFrame, col: str, fallback: str) -> pd.Series:
    if col not in df_in.columns:
        return pd.Series([fallback] * len(df_in), index=df_in.index, dtype="string")
    s = df_in[col].fillna(fallback).astype(str).map(norm_text)
    s = s.replace("", fallback)
    return s


def _ranking_texto(df_in: pd.DataFrame, col: str, total: float, titulo: str, top_n: int | None = None) -> str:
    if df_in.empty or col not in df_in.columns:
        return f"{titulo}:\n- Sem dados"

    dfx = df_in.copy()
    dfx[col] = _safe_dim(dfx, col, "N/I")
    tbl = (
        dfx.groupby(col, as_index=False)["VR_TOTAL"].sum()
        .sort_values("VR_TOTAL", ascending=False)
    )
    if top_n is not None:
        tbl = tbl.head(top_n)

    linhas = [f"{titulo}:"]
    for _, row in tbl.iterrows():
        valor = float(row["VR_TOTAL"])
        pct = (valor / total * 100) if total else 0.0
        linhas.append(f"- {row[col]}: {format_brl(valor)} ({fmt_pct(pct)})")
    return "\n".join(linhas)


def _previsao_fechamento_mes(df_mes: pd.DataFrame, mes_key: str) -> tuple[float, int, float]:
    dias_uteis = int(DIAS_UTEIS_MENSAL.get(mes_key, 0))
    if df_mes.empty:
        return 0.0, dias_uteis, 0.0
    venda_por_dia = df_mes.groupby("DIA", as_index=False)["VR_TOTAL"].sum()
    venda_por_dia = venda_por_dia[venda_por_dia["VR_TOTAL"] > 0]
    media_dias_com_venda = float(venda_por_dia["VR_TOTAL"].mean()) if not venda_por_dia.empty else 0.0
    return media_dias_com_venda * dias_uteis, dias_uteis, media_dias_com_venda


def montar_report_unica(df_base: pd.DataFrame, data_ref) -> str:
    data_ref = pd.to_datetime(data_ref).date()
    mes_num = data_ref.month
    ano = data_ref.year
    mes_key = month_key_from_monthnum(mes_num)

    df_dia = df_base[df_base["DIA"] == data_ref].copy()
    df_mes = df_base[(df_base["ANO"] == ano) & (df_base["MES_NUM"] == mes_num) & (df_base["DIA"] <= data_ref)].copy()

    venda_dia = float(df_dia["VR_TOTAL"].sum()) if not df_dia.empty else 0.0
    venda_mes = float(df_mes["VR_TOTAL"].sum()) if not df_mes.empty else 0.0
    prev_mes, dias_uteis, media_dia = _previsao_fechamento_mes(df_mes, mes_key)

    data_txt = data_ref.strftime("%d/%m/%Y")
    linhas = [
        f"REPORT ÚNICA - {data_txt}",
        "",
        f"REPORT DO DIA - {data_txt}",
        f"Venda do dia: {format_brl(venda_dia)}",
        "Previsão de fechamento: não aplicável para o recorte diário.",
        "",
        _ranking_texto(df_dia, "VENDEDOR", venda_dia, "Vendas por vendedor", top_n=None),
        "",
        _ranking_texto(df_dia, "SEGMENTO", venda_dia, "Vendas por segmento", top_n=None),
        "",
        _ranking_texto(df_dia, "MARCA", venda_dia, "Top 10 marcas", top_n=10),
        "",
        _ranking_texto(df_dia, "CLIENTE", venda_dia, "Top 10 clientes", top_n=10),
        "",
        f"REPORT DO MÊS VIGENTE - {mes_key}/{ano}",
        f"Venda do mês: {format_brl(venda_mes)}",
        f"Previsão de fechamento: {format_brl(prev_mes)} ({dias_uteis} dias úteis; média dos dias com venda: {format_brl(media_dia)})",
        "",
        _ranking_texto(df_mes, "VENDEDOR", venda_mes, "Vendas por vendedor", top_n=None),
        "",
        _ranking_texto(df_mes, "SEGMENTO", venda_mes, "Vendas por segmento", top_n=None),
        "",
        _ranking_texto(df_mes, "MARCA", venda_mes, "Top 10 marcas", top_n=10),
        "",
        _ranking_texto(df_mes, "CLIENTE", venda_mes, "Top 10 clientes", top_n=10),
    ]
    return "\n".join(linhas)


def render_relatorios_unica(df_base: pd.DataFrame, min_data, max_data):
    """Aba Relatórios com UX melhorada e envio via WhatsApp sem limite de URL.

    Fluxo do botão principal:
    1) copia o relatório completo para a área de transferência do navegador;
    2) abre o WhatsApp no contato configurado;
    3) o usuário cola o texto completo na conversa.
    """
    import json

    st.markdown("""
    <style>
    .rel-hero {
        background: linear-gradient(135deg, #0f172a 0%, #14532d 100%);
        border: 1px solid rgba(255,255,255,0.14);
        border-radius: 22px;
        padding: 24px 26px;
        margin-bottom: 18px;
        box-shadow: 0 16px 38px rgba(15,23,42,0.18);
    }
    .rel-hero h2 {
        color: #ffffff !important;
        margin: 0 0 6px 0;
        font-size: 30px;
        font-weight: 850;
        letter-spacing: -0.02em;
    }
    .rel-hero p {
        color: rgba(255,255,255,0.82) !important;
        margin: 0;
        font-size: 15px;
        line-height: 1.45;
    }
    .rel-step-card {
        background: #ffffff;
        color: #0f172a;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 16px 18px;
        box-shadow: 0 8px 24px rgba(15,23,42,0.08);
        min-height: 120px;
    }
    .rel-step-card .num {
        background: #dcfce7;
        color: #166534;
        border-radius: 999px;
        width: 32px;
        height: 32px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 850;
        margin-bottom: 10px;
    }
    .rel-step-card strong {
        display: block;
        font-size: 15px;
        margin-bottom: 5px;
        color: #111827;
    }
    .rel-step-card span {
        color: #64748b;
        font-size: 13px;
        line-height: 1.35;
    }
    .rel-section-title {
        font-size: 20px;
        font-weight: 800;
        color: #0f172a;
        margin: 18px 0 8px 0;
    }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        padding: 16px 18px;
        border-radius: 18px;
        box-shadow: 0 8px 24px rgba(15,23,42,0.07);
    }
    div[data-testid="stMetric"] label, div[data-testid="stMetric"] div {
        color: #0f172a !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        """
        <div class="rel-hero">
            <h2>📲 Relatórios WhatsApp</h2>
            <p>Gere o report da Única, copie o texto completo e abra o WhatsApp no contato cadastrado. O envio não depende mais do limite de caracteres do link.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="rel-section-title">1. Escolha a data do report</div>', unsafe_allow_html=True)
    data_ref = st.date_input(
        "Data do relatório",
        value=max_data,
        min_value=min_data,
        max_value=max_data,
        key="relatorio_unica_data_ref",
    )

    texto = montar_report_unica(df_base, data_ref)
    whatsapp_url = f"https://wa.me/{WHATSAPP_REPORT_UNICA}"

    df_dia = df_base[df_base["DIA"] == data_ref].copy()
    df_mes = df_base[(df_base["ANO"] == data_ref.year) & (df_base["MES_NUM"] == data_ref.month) & (df_base["DIA"] <= data_ref)].copy()
    venda_dia = float(df_dia["VR_TOTAL"].sum()) if not df_dia.empty else 0.0
    venda_mes = float(df_mes["VR_TOTAL"].sum()) if not df_mes.empty else 0.0
    mes_key = month_key_from_monthnum(data_ref.month)
    prev_mes, _, _ = _previsao_fechamento_mes(df_mes, mes_key)

    st.markdown('<div class="rel-section-title">2. Resumo do relatório</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Venda do dia", format_brl(venda_dia))
    with c2:
        st.metric("Venda do mês vigente", format_brl(venda_mes))
    with c3:
        st.metric("Previsão fechamento mês", format_brl(prev_mes))

    st.markdown('<div class="rel-section-title">3. Envio</div>', unsafe_allow_html=True)
    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(
            '<div class="rel-step-card"><div class="num">1</div><strong>Clique no botão verde</strong><span>O relatório completo será copiado para a área de transferência.</span></div>',
            unsafe_allow_html=True,
        )
    with s2:
        st.markdown(
            '<div class="rel-step-card"><div class="num">2</div><strong>WhatsApp será aberto</strong><span>O app abre direto no número configurado da Única.</span></div>',
            unsafe_allow_html=True,
        )
    with s3:
        st.markdown(
            '<div class="rel-step-card"><div class="num">3</div><strong>Cole e envie</strong><span>No campo da conversa, pressione Ctrl+V ou toque em colar.</span></div>',
            unsafe_allow_html=True,
        )

    texto_json = json.dumps(texto, ensure_ascii=False)
    url_json = json.dumps(whatsapp_url, ensure_ascii=False)
    components.html(
        f"""
        <div style="font-family: Arial, sans-serif; margin: 12px 0 2px 0;">
            <button id="btnZap" style="
                width: 100%;
                min-height: 68px;
                border: 0;
                border-radius: 18px;
                cursor: pointer;
                background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
                color: white;
                font-size: 22px;
                font-weight: 900;
                letter-spacing: -0.01em;
                box-shadow: 0 14px 30px rgba(18,140,126,0.30);
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 12px;
                transition: transform .15s ease, filter .15s ease;
            " onmouseover="this.style.transform='translateY(-1px)'; this.style.filter='brightness(1.03)'" onmouseout="this.style.transform='translateY(0)'; this.style.filter='brightness(1)'">
                <span style="font-size: 28px; line-height: 1;">🟢</span>
                <span>Enviar pelo WhatsApp</span>
            </button>
            <div id="zapStatus" style="
                margin-top: 10px;
                font-size: 13px;
                color: #334155;
                text-align: center;
            ">Ao clicar, o texto completo será copiado e o WhatsApp será aberto.</div>
            <textarea id="fallbackText" style="position:absolute; left:-9999px; top:-9999px;"></textarea>
        </div>
        <script>
        const reportText = {texto_json};
        const whatsappUrl = {url_json};
        const btn = document.getElementById('btnZap');
        const statusEl = document.getElementById('zapStatus');
        const fallback = document.getElementById('fallbackText');

        async function copyText(text) {{
            if (navigator.clipboard && window.isSecureContext) {{
                await navigator.clipboard.writeText(text);
                return true;
            }}
            fallback.value = text;
            fallback.focus();
            fallback.select();
            return document.execCommand('copy');
        }}

        btn.addEventListener('click', async () => {{
            try {{
                await copyText(reportText);
                statusEl.innerHTML = '✅ Relatório copiado. Abrindo WhatsApp... cole a mensagem na conversa.';
                statusEl.style.color = '#166534';
                window.open(whatsappUrl, '_blank');
            }} catch (err) {{
                fallback.value = reportText;
                fallback.style.position = 'static';
                fallback.style.left = 'auto';
                fallback.style.top = 'auto';
                fallback.style.width = '100%';
                fallback.style.height = '180px';
                fallback.style.marginTop = '12px';
                fallback.select();
                statusEl.innerHTML = '⚠️ Não foi possível copiar automaticamente. Selecione o texto abaixo, copie manualmente e abra o WhatsApp.';
                statusEl.style.color = '#b45309';
                window.open(whatsappUrl, '_blank');
            }}
        }});
        </script>
        """,
        height=120,
    )

    st.download_button(
        "⬇️ Baixar texto .txt",
        data=texto.encode("utf-8"),
        file_name=f"report_unica_{data_ref.strftime('%Y_%m_%d')}.txt",
        mime="text/plain",
        use_container_width=True,
    )

    st.markdown("### Texto gerado")
    st.caption(f"Tamanho do texto: {len(texto):,} caracteres. O botão verde copia o texto inteiro, sem enviar pela URL do WhatsApp.".replace(",", "."))
    st.text_area("Revise o texto antes de enviar", value=texto, height=620)
# =========================
# Sidebar filtros
# =========================
min_dt = df["DATA"].min().date()
max_dt = df["DATA"].max().date()
if "vendedor_sel" not in st.session_state:
    st.session_state["vendedor_sel"] = "TODOS"
with st.sidebar:
    pagina_app = st.radio("Página", ["Dashboard", "Relatórios"], index=0)
    st.header("Filtros")

    filtro_tipo = st.radio("Tipo de filtro", ["Período (DATA)", "Mês (ANO/MÊS)"], index=0)

    if filtro_tipo == "Período (DATA)":
        dt_ini, dt_fim = st.date_input(
            "Período (DATA)",
            value=(min_dt, max_dt),
            min_value=min_dt,
            max_value=max_dt,
        )
        if isinstance(dt_ini, (tuple, list)):
            dt_ini, dt_fim = dt_ini[0], dt_ini[1]
        mask_base = (df["DIA"] >= dt_ini) & (df["DIA"] <= dt_fim)
    else:
        anos_opts = sorted(df["ANO"].dropna().unique().tolist())
        ano_padrao = max(anos_opts) if anos_opts else int(df["ANO"].max())
        ano_sel = st.selectbox("Ano", options=anos_opts, index=(anos_opts.index(ano_padrao) if ano_padrao in anos_opts else 0))
        meses_sel = st.multiselect("Mês(es)", options=MESES_PT, default=MESES_PT)
        if not meses_sel:
            meses_sel = MESES_PT
        mask_base = (df["ANO"] == int(ano_sel)) & (df["MES"].isin(meses_sel))

        df_tmp = df.loc[mask_base]
        if df_tmp.empty:
            dt_ini, dt_fim = min_dt, max_dt
        else:
            dt_ini = df_tmp["DIA"].min()
            dt_fim = df_tmp["DIA"].max()

    # manter seleção de vendedor
    if "vendedor_sel" not in st.session_state:
        st.session_state["vendedor_sel"] = "TODOS"

    vendedor_sel = "TODOS"
    if "VENDEDOR" in df.columns:
        df_dt = df.loc[mask_base].copy()
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
mask_dt = mask_base
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

if pagina_app == "Relatórios":
    render_relatorios_unica(df, min_dt, max_dt)
    st.stop()

st.session_state["pdf_sections"] = []

# Base completa do ano (para tabelas Ano-1 e Metas), sem zerar meses fora do filtro de período/mês
df_base_vendor = df.copy()
if vendedor_sel != "TODOS" and "VENDEDOR" in df_base_vendor.columns:
    df_base_vendor = df_base_vendor[df_base_vendor["VENDEDOR"].fillna("").astype(str).map(norm_text) == norm_text(vendedor_sel)].copy()

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

indicadores_pdf = pd.DataFrame([
    {"Indicador": "Faturamento (Período)", "Valor": format_brl(faturamento_periodo), "Observação": f"{dt_ini} → {dt_fim}"},
    {"Indicador": "Ano Atual (no período)", "Valor": str(ano_atual), "Observação": "Base: DATA filtrada"},
    {"Indicador": "Vendedor (filtro)", "Valor": vendedor_sel, "Observação": "TODOS = sem recorte"},
    {"Indicador": "Clientes Ativos (período)", "Valor": f"{clientes_ativos:,}".replace(",", "."), "Observação": "Clientes únicos"},
    {"Indicador": "Média diária (dias c/ venda)", "Valor": format_brl(media_dia), "Observação": "Ignora dias zerados"},
    {"Indicador": f"Previsão (mês {mes_ref})", "Valor": format_brl(previsao_mes), "Observação": f"{dias_uteis_ref} dias úteis"},
    {"Indicador": "Markup (Fat/Custo)", "Valor": ("—" if markup is None else f"{markup:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")), "Observação": "Σ Fat ÷ Σ Custo"},
])
add_pdf_section("Indicadores", indicadores_pdf)


# =========================
# INDICADORES COMPLEMENTARES — Vendedores e Dias de Venda
# =========================
st.markdown("### Indicadores Complementares")
cc1, cc2 = st.columns([1.05, 1.15])

with cc1:
    st.subheader("Ranking de vendas por vendedor")
    if "VENDEDOR" in df_periodo_all.columns:
        rank_vend = df_periodo_all.copy()
        rank_vend["VENDEDOR"] = rank_vend["VENDEDOR"].fillna("N/I").astype(str).map(norm_text)
        rank_vend = rank_vend[rank_vend["VENDEDOR"].astype(str).str.strip() != ""].copy()

        rank_vend_tbl = (
            rank_vend.groupby("VENDEDOR", as_index=False)["VR_TOTAL"].sum()
            .rename(columns={"VR_TOTAL": "FAT_NUM"})
            .sort_values("FAT_NUM", ascending=False)
        )

        total_rank_vend = float(rank_vend_tbl["FAT_NUM"].sum()) if not rank_vend_tbl.empty else 0.0
        rank_vend_tbl["RANK"] = range(1, len(rank_vend_tbl) + 1)
        rank_vend_tbl["% SOBRE TOTAL"] = rank_vend_tbl["FAT_NUM"].apply(
            lambda x: (x / total_rank_vend * 100) if total_rank_vend else None
        )

        rank_vend_show = rank_vend_tbl[["RANK", "VENDEDOR", "FAT_NUM", "% SOBRE TOTAL"]].copy()
        rank_vend_show = rank_vend_show.rename(columns={"FAT_NUM": "FAT (R$)"})
        rank_vend_show["FAT (R$)"] = rank_vend_show["FAT (R$)"].map(format_brl)
        rank_vend_show["% SOBRE TOTAL"] = rank_vend_tbl["% SOBRE TOTAL"].apply(fmt_pct)

        st.caption("Considera o período selecionado.")
        st.dataframe(rank_vend_show, use_container_width=True, hide_index=True)
        botao_download_pdf(rank_vend_show, "Ranking de Vendedores", "ranking_vendedores.pdf")
        add_pdf_section("Ranking de Vendedores", rank_vend_show)
    else:
        st.info("Coluna VENDEDOR não encontrada para montar o ranking.")

with cc2:
    st.subheader("Dias de venda do período")
    if not df_periodo.empty:
        dias_tbl = (
            df_periodo.groupby("DIA", as_index=False)["VR_TOTAL"].sum()
            .rename(columns={"VR_TOTAL": "FAT_NUM"})
            .sort_values(["FAT_NUM", "DIA"], ascending=[False, True])
        )
        dias_tbl = dias_tbl[dias_tbl["FAT_NUM"] > 0].copy()

        if dias_tbl.empty:
            st.info("Não há dias com venda no filtro atual.")
        else:
            top_qtd = min(3, len(dias_tbl))
            dias_tbl["DESTAQUE"] = ""
            dias_tbl.loc[dias_tbl.index[:top_qtd], "DESTAQUE"] = [f"TOP {i}" for i in range(1, top_qtd + 1)]
            dias_tbl["DIA SEMANA"] = pd.to_datetime(dias_tbl["DIA"]).dt.day_name().map(DIAS_SEMANA_PT)

            dias_show = dias_tbl[["DIA", "DIA SEMANA", "FAT_NUM", "DESTAQUE"]].copy()
            dias_show["DIA"] = pd.to_datetime(dias_show["DIA"])
            dias_show = dias_show.rename(columns={"FAT_NUM": "VENDAS (R$)"})

            def _style_dias(row):
                if str(row.get("DESTAQUE", "")).startswith("TOP"):
                    return ["background-color: rgba(11,94,215,0.18); font-weight:700;" for _ in row.index]
                return ["" for _ in row.index]

            sty_dias = dias_show.style.apply(_style_dias, axis=1).format({
                "DIA": lambda x: pd.to_datetime(x).strftime("%d/%m/%Y") if pd.notna(x) else "—",
                "VENDAS (R$)": lambda x: format_brl(x),
            })
            st.caption("Ao clicar na coluna DIA, a ordenação respeita a data real (do mais antigo para o mais novo).")
            st.dataframe(sty_dias, use_container_width=True, hide_index=True)
            dias_pdf = dias_show.copy()
            dias_pdf["DIA"] = dias_pdf["DIA"].apply(lambda x: pd.to_datetime(x).strftime("%d/%m/%Y") if pd.notna(x) else "—")
            dias_pdf["VENDAS (R$)"] = dias_pdf["VENDAS (R$)"].map(format_brl)
            botao_download_pdf(dias_pdf, "Dias de Venda", "dias_de_venda.pdf")
            add_pdf_section("Dias de Venda", dias_pdf)
    else:
        st.info("Sem dados para montar a tabela de dias de venda.")

st.divider()
# =========================
# SEÇÃO 2 — Ano-1 vs Ano Atual
# =========================
st.markdown("## Ano-1 vs Ano Atual")
df_atual = df_base_vendor[df_base_vendor["ANO"] == ano_atual].copy()
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
    ano1_pdf = df_disp.copy()
    ano1_pdf["DIF (R$)"] = ano1_pdf["DIF (R$)"].map(format_brl)
    botao_download_pdf(ano1_pdf, "Ano-1 vs Ano Atual", "ano_1_vs_ano_atual.pdf")
    add_pdf_section("Ano-1 vs Ano Atual", ano1_pdf)
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
    metas_pdf = df_disp.copy()
    metas_pdf["DIF (R$)"] = metas_pdf["DIF (R$)"].map(format_brl)
    botao_download_pdf(metas_pdf, "Meta x Realizado", "meta_x_realizado.pdf")
    add_pdf_section("Meta x Realizado", metas_pdf)
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
        botao_download_pdf(top10_show, "Top 10 Marcas", "top_10_marcas.pdf")
        add_pdf_section("Top 10 Marcas", top10_show)
        resto = marcas.iloc[10:].copy()
        if not resto.empty:
            with st.expander("Ver demais marcas (drill)"):
                resto_show = resto.copy()
                resto_show["FAT (R$)"] = resto_show["FAT (R$)"].map(format_brl)
                resto_show["% SOBRE TOTAL"] = resto["% SOBRE TOTAL"].apply(fmt_pct)
                st.dataframe(resto_show, use_container_width=True, hide_index=True)
                botao_download_pdf(resto_show, "Demais Marcas", "demais_marcas.pdf", max_rows=None)
                add_pdf_section("Drill - Demais Marcas", resto_show)
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
        seg_show = seg.copy()
        total_seg = float(seg_show["FAT (R$)"].sum()) if not seg_show.empty else 0.0
        seg_show["% SOBRE TOTAL"] = seg_show["FAT (R$)"].apply(lambda x: (x / total_seg * 100) if total_seg else None).apply(fmt_pct)
        seg_show["FAT (R$)"] = seg_show["FAT (R$)"].map(format_brl)
        botao_download_pdf(seg_show, "Faturamento por Segmento", "faturamento_por_segmento.pdf")
        add_pdf_section("Faturamento por Segmento", seg_show)
    else:
        st.info("Sem dados (ou coluna SEGMENTO ausente) para o período/vendedor selecionado.")

# ===== Top 10 Linhas (com drill de marcas dentro da linha) =====
st.markdown("### Top 10 Linhas")
if (not df_periodo.empty) and ("LINHA" in df_periodo.columns):
    total_geral_linhas = float(df_periodo["VR_TOTAL"].sum()) if len(df_periodo) else 0.0
    linhas_tbl = (
        df_periodo.groupby("LINHA", as_index=False)["VR_TOTAL"].sum()
        .sort_values("VR_TOTAL", ascending=False)
        .rename(columns={"VR_TOTAL": "FAT (R$)"})
    )
    linhas_tbl["% SOBRE TOTAL"] = linhas_tbl["FAT (R$)"].apply(lambda x: (x / total_geral_linhas * 100) if total_geral_linhas else None)

    top10_linhas = linhas_tbl.head(10).copy()
    top10_linhas_show = top10_linhas.copy()
    top10_linhas_show["FAT (R$)"] = top10_linhas_show["FAT (R$)"].map(format_brl)
    top10_linhas_show["% SOBRE TOTAL"] = top10_linhas["% SOBRE TOTAL"].apply(fmt_pct)
    st.dataframe(top10_linhas_show, use_container_width=True, hide_index=True)
    botao_download_pdf(top10_linhas_show, "Top 10 Linhas", "top_10_linhas.pdf")
    add_pdf_section("Top 10 Linhas", top10_linhas_show)

    with st.expander("Drill: marcas que performaram dentro da linha (e % sobre a linha)"):
        linhas_opts = (
            linhas_tbl["LINHA"].fillna("").astype(str).map(norm_text).replace("", pd.NA).dropna().unique().tolist()
        )
        linhas_opts = sorted(set(linhas_opts), key=lambda x: x.upper())
        linha_sel = st.selectbox("Selecionar linha", options=linhas_opts, index=0, key="LINHA_DRILL")
        df_linha = df_periodo[df_periodo["LINHA"].fillna("").astype(str).map(norm_text) == norm_text(linha_sel)].copy()
        total_linha = float(df_linha["VR_TOTAL"].sum()) if not df_linha.empty else 0.0

        if df_linha.empty or ("MARCA" not in df_linha.columns):
            st.info("Sem dados (ou coluna MARCA ausente) para detalhar marcas dentro desta linha.")
        else:
            marcas_linha = (
                df_linha.groupby("MARCA", as_index=False)["VR_TOTAL"].sum()
                .sort_values("VR_TOTAL", ascending=False)
                .rename(columns={"VR_TOTAL": "FAT (R$)"})
            )
            marcas_linha["% SOBRE LINHA"] = marcas_linha["FAT (R$)"].apply(lambda x: (x / total_linha * 100) if total_linha else None)

            top_m = marcas_linha.head(15).copy()
            top_m_show = top_m.copy()
            top_m_show["FAT (R$)"] = top_m_show["FAT (R$)"].map(format_brl)
            top_m_show["% SOBRE LINHA"] = top_m["% SOBRE LINHA"].apply(fmt_pct)
            st.metric("Total da linha (período)", format_brl(total_linha))
            st.dataframe(top_m_show, use_container_width=True, hide_index=True)
            botao_download_pdf(top_m_show, f"Drill Linha - {linha_sel}", f"drill_linha_{str(linha_sel).replace(' ', '_')}.pdf")
            add_pdf_section(f"Drill Linha Selecionada - {linha_sel}", top_m_show)

            resto_m = marcas_linha.iloc[15:].copy()
            if not resto_m.empty:
                with st.expander("Ver demais marcas na linha"):
                    resto_m_show = resto_m.copy()
                    resto_m_show["FAT (R$)"] = resto_m_show["FAT (R$)"].map(format_brl)
                    resto_m_show["% SOBRE LINHA"] = resto_m["% SOBRE LINHA"].apply(fmt_pct)
                    st.dataframe(resto_m_show, use_container_width=True, hide_index=True)
                    botao_download_pdf(resto_m_show, f"Demais Marcas na Linha - {linha_sel}", f"demais_marcas_linha_{str(linha_sel).replace(' ', '_')}.pdf")
                    add_pdf_section(f"Drill - Demais Marcas na Linha {linha_sel}", resto_m_show)
else:
    st.info("Sem dados (ou coluna LINHA ausente) para montar Top 10 Linhas no período/vendedor selecionado.")

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
            botao_download_pdf(cli_reg_show, "Clientes por Região Selecionada", "clientes_regiao_selecionada.pdf")
            add_pdf_section("Clientes por Região Selecionada", cli_reg_show)
    st.divider()
    # ===== Evolução de Clientes (DRILL) =====
    st.subheader("Evolução de Clientes (drill)")
    if not df_periodo.empty and "CLIENTE" in df_periodo.columns:
        evo = df_periodo.copy()
        evo["CLIENTE"] = evo["CLIENTE"].fillna("N/I").astype(str).map(norm_text)

        # Base mensal (ANO + MES + CLIENTE) para montar a tabela no formato Jan..Dez
        evo_base = (
            evo.groupby(["ANO", "MES", "CLIENTE"], as_index=False)["VR_TOTAL"]
            .sum()
            .rename(columns={"VR_TOTAL": "FAT_NUM"})
        )

        def fmt_num_ptbr(v):
            try:
                return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except Exception:
                return "0,00"

        with st.expander("Abrir evolução (cliente → meses Jan..Dez)"):
            anos_disp = sorted(evo_base["ANO"].dropna().unique().tolist())
            ano_pick = st.selectbox(
                "Ano",
                options=anos_disp,
                index=(len(anos_disp) - 1) if anos_disp else 0,
                key="EVO_ANO"
            )

            evo_f = evo_base[evo_base["ANO"] == int(ano_pick)].copy() if anos_disp else evo_base.copy()

            busca = st.text_input("Buscar cliente (opcional)", value="", key="EVO_BUSCA").strip()
            if busca:
                evo_f = evo_f[evo_f["CLIENTE"].str.contains(busca, case=False, na=False)].copy()

            # Pivot: CLIENTE x MESES (Jan..Dez) + Total
            evo_pivot = (
                evo_f.pivot_table(index="CLIENTE", columns="MES", values="FAT_NUM", aggfunc="sum", fill_value=0.0)
                if not evo_f.empty
                else pd.DataFrame(index=pd.Index([], name="CLIENTE"))
            )

            # Garantir colunas Jan..Dez e ordem correta
            for m in MESES_PT:
                if m not in evo_pivot.columns:
                    evo_pivot[m] = 0.0
            evo_pivot = evo_pivot[MESES_PT].copy()
            evo_pivot["Total Geral"] = evo_pivot.sum(axis=1)

            evo_pivot = evo_pivot.sort_values("Total Geral", ascending=False)

            evo_show = evo_pivot.reset_index()
            for m in MESES_PT + ["Total Geral"]:
                evo_show[m] = evo_show[m].apply(fmt_num_ptbr)

            st.dataframe(evo_show, use_container_width=True, hide_index=True)
            botao_download_pdf(evo_show, f"Evolução de Clientes {ano_pick}", f"evolucao_clientes_{ano_pick}.pdf", max_rows=None)
            add_pdf_section(f"Evolução de Clientes {ano_pick}", evo_show, max_rows=None)
    else:
        st.info("Sem dados/coluna CLIENTE para montar Evolução de Clientes.")


# =========================
# SEÇÃO 6 — Ranking de Clientes (Top clientes + marca/linha preferida + drill por linha → marca)
# =========================
st.divider()
st.markdown("## Ranking de Clientes")

if (not df_periodo.empty) and ("CLIENTE" in df_periodo.columns):
    df_cli = df_periodo.copy()
    df_cli["CLIENTE"] = df_cli["CLIENTE"].fillna("N/I").astype(str).map(norm_text)

    total_cli_geral = float(df_cli["VR_TOTAL"].sum()) if len(df_cli) else 0.0
    base_cli = (
        df_cli.groupby("CLIENTE", as_index=False)["VR_TOTAL"].sum()
        .rename(columns={"VR_TOTAL": "FAT (R$)"})
        .sort_values("FAT (R$)", ascending=False)
    )
    base_cli["% SOBRE TOTAL"] = base_cli["FAT (R$)"].apply(lambda x: (x / total_cli_geral * 100) if total_cli_geral else None)

    # Top marca por cliente (se existir)
    if "MARCA" in df_cli.columns:
        df_cli["MARCA"] = df_cli["MARCA"].fillna("N/I").astype(str).map(norm_text)
        cli_marca = (
            df_cli.groupby(["CLIENTE", "MARCA"], as_index=False)["VR_TOTAL"].sum()
            .sort_values(["CLIENTE", "VR_TOTAL"], ascending=[True, False])
        )
        idx = cli_marca.groupby("CLIENTE")["VR_TOTAL"].idxmax()
        top_marca_cli = cli_marca.loc[idx, ["CLIENTE", "MARCA"]].rename(columns={"MARCA": "MARCA TOP"})
        base_cli = base_cli.merge(top_marca_cli, on="CLIENTE", how="left")
    else:
        base_cli["MARCA TOP"] = "N/I"

    # Top linha por cliente (se existir)
    if "LINHA" in df_cli.columns:
        df_cli["LINHA"] = df_cli["LINHA"].fillna("N/I").astype(str).map(norm_text)
        cli_linha = (
            df_cli.groupby(["CLIENTE", "LINHA"], as_index=False)["VR_TOTAL"].sum()
            .sort_values(["CLIENTE", "VR_TOTAL"], ascending=[True, False])
        )
        idx2 = cli_linha.groupby("CLIENTE")["VR_TOTAL"].idxmax()
        top_linha_cli = cli_linha.loc[idx2, ["CLIENTE", "LINHA"]].rename(columns={"LINHA": "LINHA TOP"})
        base_cli = base_cli.merge(top_linha_cli, on="CLIENTE", how="left")
    else:
        base_cli["LINHA TOP"] = "N/I"
    # Mostrar TODOS os clientes do período (ordenado por faturamento)
    base_cli_show = base_cli.copy()
    base_cli_show["FAT (R$)"] = base_cli_show["FAT (R$)"].map(format_brl)
    base_cli_show["% SOBRE TOTAL"] = base_cli["% SOBRE TOTAL"].apply(fmt_pct)
    ranking_clientes_pdf = base_cli_show[["CLIENTE", "FAT (R$)", "% SOBRE TOTAL", "MARCA TOP", "LINHA TOP"]].copy()
    st.dataframe(
        ranking_clientes_pdf,
        use_container_width=True,
        hide_index=True
    )
    botao_download_pdf(ranking_clientes_pdf, "Ranking de Clientes", "ranking_clientes.pdf", max_rows=None)
    add_pdf_section("Ranking de Clientes", ranking_clientes_pdf, max_rows=None)


    with st.expander("Drill do cliente: (1) top marca/linha + (2) dentro da linha → marcas que ele compra"):
        cli_opts = base_cli["CLIENTE"].tolist()
        if not cli_opts:
            st.info("Sem clientes para detalhar.")
        else:
            cli_sel = st.selectbox("Selecionar cliente", options=cli_opts, index=0, key="CLI_DRILL_SEL")
            df_c = df_cli[df_cli["CLIENTE"] == cli_sel].copy()
            fat_cliente = float(df_c["VR_TOTAL"].sum()) if not df_c.empty else 0.0

            col1, col2, col3 = st.columns(3)
            col1.metric("Faturamento do cliente (período)", format_brl(fat_cliente))
            col2.metric("Marca TOP", (base_cli[base_cli["CLIENTE"] == cli_sel]["MARCA TOP"].iloc[0] if "MARCA TOP" in base_cli.columns else "N/I"))
            col3.metric("Linha TOP", (base_cli[base_cli["CLIENTE"] == cli_sel]["LINHA TOP"].iloc[0] if "LINHA TOP" in base_cli.columns else "N/I"))

            # Tabelas auxiliares do cliente
            if "MARCA" in df_c.columns:
                marcas_c = (
                    df_c.groupby("MARCA", as_index=False)["VR_TOTAL"].sum()
                    .sort_values("VR_TOTAL", ascending=False)
                    .rename(columns={"VR_TOTAL": "FAT (R$)"})
                )
                marcas_c["% SOBRE CLIENTE"] = marcas_c["FAT (R$)"].apply(lambda x: (x / fat_cliente * 100) if fat_cliente else None)
                marcas_c_show = marcas_c.head(15).copy()
                marcas_c_show["FAT (R$)"] = marcas_c_show["FAT (R$)"].map(format_brl)
                marcas_c_show["% SOBRE CLIENTE"] = marcas_c.head(15)["% SOBRE CLIENTE"].apply(fmt_pct)
                st.markdown("**Marcas mais compradas pelo cliente (TOP 15)**")
                st.dataframe(marcas_c_show, use_container_width=True, hide_index=True)
                botao_download_pdf(marcas_c_show, f"Marcas do Cliente - {cli_sel}", f"marcas_cliente_{str(cli_sel).replace(' ', '_')}.pdf")
                add_pdf_section(f"Drill Cliente - Marcas - {cli_sel}", marcas_c_show)

            if "LINHA" in df_c.columns:
                linhas_c = (
                    df_c.groupby("LINHA", as_index=False)["VR_TOTAL"].sum()
                    .sort_values("VR_TOTAL", ascending=False)
                    .rename(columns={"VR_TOTAL": "FAT (R$)"})
                )
                linhas_c["% SOBRE CLIENTE"] = linhas_c["FAT (R$)"].apply(lambda x: (x / fat_cliente * 100) if fat_cliente else None)
                linhas_c_show = linhas_c.head(15).copy()
                linhas_c_show["FAT (R$)"] = linhas_c_show["FAT (R$)"].map(format_brl)
                linhas_c_show["% SOBRE CLIENTE"] = linhas_c.head(15)["% SOBRE CLIENTE"].apply(fmt_pct)
                st.markdown("**Linhas mais compradas pelo cliente (TOP 15)**")
                st.dataframe(linhas_c_show, use_container_width=True, hide_index=True)
                botao_download_pdf(linhas_c_show, f"Linhas do Cliente - {cli_sel}", f"linhas_cliente_{str(cli_sel).replace(' ', '_')}.pdf")
                add_pdf_section(f"Drill Cliente - Linhas - {cli_sel}", linhas_c_show)

                # Dentro da linha → marcas do cliente
                if "MARCA" in df_c.columns:
                    linhas_opts = linhas_c["LINHA"].tolist()
                    if linhas_opts:
                        linha_cli_sel = st.selectbox("Dentro da linha, ver marcas compradas pelo cliente", options=linhas_opts, index=0, key="CLI_LINHA_SEL")
                        df_cl = df_c[df_c["LINHA"] == linha_cli_sel].copy()
                        total_linha_cli = float(df_cl["VR_TOTAL"].sum()) if not df_cl.empty else 0.0
                        marcas_in_linha = (
                            df_cl.groupby("MARCA", as_index=False)["VR_TOTAL"].sum()
                            .sort_values("VR_TOTAL", ascending=False)
                            .rename(columns={"VR_TOTAL": "FAT (R$)"})
                        )
                        marcas_in_linha["% SOBRE LINHA (CLIENTE)"] = marcas_in_linha["FAT (R$)"].apply(
                            lambda x: (x / total_linha_cli * 100) if total_linha_cli else None
                        )
                        marcas_in_linha_show = marcas_in_linha.copy()
                        marcas_in_linha_show["FAT (R$)"] = marcas_in_linha_show["FAT (R$)"].map(format_brl)
                        marcas_in_linha_show["% SOBRE LINHA (CLIENTE)"] = marcas_in_linha["% SOBRE LINHA (CLIENTE)"].apply(fmt_pct)
                        st.metric("Total do cliente na linha selecionada", format_brl(total_linha_cli))
                        st.dataframe(marcas_in_linha_show, use_container_width=True, hide_index=True)
                        botao_download_pdf(marcas_in_linha_show, f"Marcas do Cliente na Linha - {linha_cli_sel}", f"marcas_cliente_linha_{str(linha_cli_sel).replace(' ', '_')}.pdf")
                        add_pdf_section(f"Drill Cliente - Marcas na Linha {linha_cli_sel}", marcas_in_linha_show)
                    else:
                        st.info("O cliente não tem linhas registradas no filtro atual.")
                else:
                    st.info("Coluna MARCA ausente: não dá para detalhar marcas dentro da linha do cliente.")
else:
    st.info("Sem dados (ou coluna CLIENTE ausente) para montar o Ranking de Clientes.")

# =========================
# SEÇÃO 7 — Análise por Marca (Clientes → Linhas do cliente dentro da marca)
# =========================
st.divider()
st.markdown("## Análise por Marca (Clientes e Linhas por Cliente)")

if (not df_periodo.empty) and ("MARCA" in df_periodo.columns) and ("CLIENTE" in df_periodo.columns) and ("LINHA" in df_periodo.columns):

    df_m = df_periodo.copy()
    df_m["MARCA"] = df_m["MARCA"].fillna("N/I").astype(str).map(norm_text)
    df_m["CLIENTE"] = df_m["CLIENTE"].fillna("N/I").astype(str).map(norm_text)
    df_m["LINHA"] = df_m["LINHA"].fillna("N/I").astype(str).map(norm_text)

    marcas_opts = sorted(df_m["MARCA"].dropna().unique().tolist(), key=lambda x: x.upper())
    marca_sel = st.selectbox("Selecionar marca", options=marcas_opts, index=0, key="MARCA_DRILL")

    df_marca = df_m[df_m["MARCA"] == marca_sel].copy()
    total_marca = float(df_marca["VR_TOTAL"].sum()) if not df_marca.empty else 0.0
    st.metric("Total da marca no período", format_brl(total_marca))

    col1, col2 = st.columns([1.15, 0.85])

    # ---- (1) Ranking de Clientes da Marca ----
    with col1:
        st.subheader("Clientes que mais compram esta marca")

        cli_marca = (
            df_marca.groupby("CLIENTE", as_index=False)["VR_TOTAL"].sum()
            .sort_values("VR_TOTAL", ascending=False)
            .rename(columns={"VR_TOTAL": "FAT (R$)"})
        )
        cli_marca["% SOBRE A MARCA"] = cli_marca["FAT (R$)"].apply(
            lambda x: (x / total_marca * 100) if total_marca else None
        )

        cli_show = cli_marca.head(30).copy()
        cli_show["FAT (R$)"] = cli_show["FAT (R$)"].map(format_brl)
        cli_show["% SOBRE A MARCA"] = cli_show["% SOBRE A MARCA"].apply(fmt_pct)

        st.dataframe(cli_show, use_container_width=True, hide_index=True)
        botao_download_pdf(cli_show, f"Clientes da Marca - {marca_sel}", f"clientes_marca_{str(marca_sel).replace(' ', '_')}.pdf")
        add_pdf_section(f"Análise por Marca - Clientes - {marca_sel}", cli_show)

    # ---- (2) Seleciona Cliente → Linhas dentro da Marca ----
    with col2:
        st.subheader("Selecionar cliente (para ver linhas dentro da marca)")

        clientes_opts = cli_marca["CLIENTE"].tolist()
        if not clientes_opts:
            st.info("Sem clientes para esta marca no filtro atual.")
        else:
            # Opção de NÃO SELEÇÃO (Todos): ao não escolher um cliente específico,
            # os drills passam a considerar TODOS os clientes dentro da marca e filtros atuais.
            clientes_select_opts = ["(Todos)"] + clientes_opts

            cliente_sel = st.selectbox(
                "Cliente",
                options=clientes_select_opts,
                index=0,
                key="MARCA_CLIENTE_SEL"
            )

            if cliente_sel == "(Todos)":
                df_marca_cli = df_marca.copy()
                cliente_lbl = "Todos os clientes"
            else:
                df_marca_cli = df_marca[df_marca["CLIENTE"] == cliente_sel].copy()
                cliente_lbl = cliente_sel

            total_marca_cli = float(df_marca_cli["VR_TOTAL"].sum()) if not df_marca_cli.empty else 0.0

            st.metric("Total (período) dentro da marca", format_brl(total_marca_cli))

            linhas_cli = (
                df_marca_cli.groupby("LINHA", as_index=False)["VR_TOTAL"].sum()
                .sort_values("VR_TOTAL", ascending=False)
                .rename(columns={"VR_TOTAL": "FAT (R$)"})
            )
            linhas_cli["% SOBRE A MARCA (CLIENTE)"] = linhas_cli["FAT (R$)"].apply(
                lambda x: (x / total_marca_cli * 100) if total_marca_cli else None
            )

            linhas_show = linhas_cli.head(25).copy()
            linhas_show["FAT (R$)"] = linhas_show["FAT (R$)"].map(format_brl)
            linhas_show["% SOBRE A MARCA (CLIENTE)"] = linhas_show["% SOBRE A MARCA (CLIENTE)"].apply(fmt_pct)

            st.markdown(f"**Linhas mais compradas por {cliente_lbl} dentro da marca {marca_sel}**")
            st.dataframe(linhas_show, use_container_width=True, hide_index=True)
            botao_download_pdf(linhas_show, f"Linhas na Marca - {marca_sel}", f"linhas_marca_{str(marca_sel).replace(' ', '_')}.pdf")
            add_pdf_section(f"Análise por Marca - Linhas - {marca_sel} - {cliente_lbl}", linhas_show)


            # ---- (3) Produtos dentro da linha (para o cliente selecionado, dentro da marca) ----
            st.subheader("Produtos (dentro da linha)")
            cod_col = find_col(
                df_marca_cli.columns,
                exact=["CODIGO", "COD_PRODUTO", "COD PRODUTO", "CODITEM", "COD_ITEM", "CODIGOITEM", "CODIGO_ITEM", "COD. PRODUTO", "COD. PROD", "COD_PROD"],
                must_contain=["COD"]
            )
            desc_col = find_col(
                df_marca_cli.columns,
                exact=["DESCRICAO", "DESCRICAO_PRODUTO", "DESCRICAO PRODUTO", "DESC", "DESCR", "DESCR. PRODUTO", "DESCR. PROD"],
                must_contain=["DESCR"]
            )

            qtd_col = find_col(
                df_marca_cli.columns,
                exact=["QTD", "QTDE", "QUANTIDADE", "QTD_ITEM", "QTDITEM", "QTD. ITEM"],
                must_contain=["QTD"]
            )

            if (cod_col is not None) and (desc_col is not None):
                linhas_prod_opts = linhas_cli["LINHA"].tolist()
                if not linhas_prod_opts:
                    st.info("Sem linhas para detalhar produtos.")
                else:
                    linha_prod_sel = st.selectbox(
                        "Selecionar linha (para ver produtos dentro da marca e do cliente)",
                        options=linhas_prod_opts,
                        index=0,
                        key="MARCA_CLIENTE_LINHA_PROD_SEL"
                    )

                    df_marca_cli_linha = df_marca_cli[df_marca_cli["LINHA"] == linha_prod_sel].copy()

                    # Normaliza colunas de produto (aceita nomes variados na base)
                    df_marca_cli_linha["_CODIGO_PROD"] = df_marca_cli_linha[cod_col]
                    df_marca_cli_linha["_DESCRICAO_PROD"] = df_marca_cli_linha[desc_col]
                    if qtd_col is not None:
                        df_marca_cli_linha["_QTD_PROD"] = pd.to_numeric(df_marca_cli_linha[qtd_col], errors="coerce").fillna(0)
                    else:
                        df_marca_cli_linha["_QTD_PROD"] = 0
                    total_linha_cli = float(df_marca_cli_linha["VR_TOTAL"].sum()) if not df_marca_cli_linha.empty else 0.0
                    st.metric("Total na linha (dentro da marca)", format_brl(total_linha_cli))

                    # Dimensão de produto (CÓDIGO -> DESCRIÇÃO sintetizada)
                    prod_dim = build_product_dictionary(df_marca_cli_linha, "_CODIGO_PROD", "_DESCRICAO_PROD")

                    prod_tbl = (
                        df_marca_cli_linha.groupby("_CODIGO_PROD", as_index=False)
                        .agg({"VR_TOTAL": "sum", "_QTD_PROD": "sum"})
                        .sort_values("VR_TOTAL", ascending=False)
                        .rename(columns={"VR_TOTAL": "FAT (R$)", "_QTD_PROD": "QTD"})
                    )
                                        # Garantir mesmo tipo na chave (evita ValueError de merge por tipos distintos)
                    prod_tbl["_CODIGO_PROD"] = prod_tbl["_CODIGO_PROD"].astype(str)
                    prod_dim["_CODIGO_PROD"] = prod_dim["_CODIGO_PROD"].astype(str)
                    prod_tbl = prod_tbl.merge(prod_dim, on="_CODIGO_PROD", how="left")
                    prod_tbl = prod_tbl.rename(columns={"_CODIGO_PROD": "CODIGO", "_DESCRICAO_PROD": "DESCRICAO"})
                    prod_tbl["DESCRICAO"] = prod_tbl["DESCRICAO"].fillna("N/I").astype(str).map(norm_text)

                    prod_tbl["% SOBRE LINHA (CLIENTE)"] = prod_tbl["FAT (R$)"].apply(
                        lambda x: (x / total_linha_cli * 100) if total_linha_cli else None
                    )

                    prod_show = prod_tbl.head(50).copy()
                    prod_show["FAT (R$)"] = prod_show["FAT (R$)"].map(format_brl)
                    prod_show["% SOBRE LINHA (CLIENTE)"] = prod_show["% SOBRE LINHA (CLIENTE)"].apply(fmt_pct)
                    # Formatar quantidade (padrão BR: 1.000,00)
                    prod_show["QTD"] = prod_show["QTD"].apply(lambda v: "-" if pd.isna(v) else f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

                    # Mostrar descrição no dashboard (código é a chave)
                    produtos_marca_pdf = prod_show[["DESCRICAO", "CODIGO", "QTD", "FAT (R$)", "% SOBRE LINHA (CLIENTE)"]].copy()
                    st.dataframe(
                        produtos_marca_pdf,
                        use_container_width=True,
                        hide_index=True
                    )
                    botao_download_pdf(produtos_marca_pdf, f"Produtos - {marca_sel} - {linha_prod_sel}", f"produtos_{str(marca_sel).replace(' ', '_')}_{str(linha_prod_sel).replace(' ', '_')}.pdf")
                    add_pdf_section(f"Análise por Marca - Produtos - {marca_sel} - {linha_prod_sel}", produtos_marca_pdf)

                    resto_p = prod_tbl.iloc[50:].copy()
                    if not resto_p.empty:
                        with st.expander("Ver demais produtos da linha"):
                            resto_p_show = resto_p.copy()
                            resto_p_show["FAT (R$)"] = resto_p_show["FAT (R$)"].map(format_brl)
                            resto_p_show["% SOBRE LINHA (CLIENTE)"] = resto_p_show["% SOBRE LINHA (CLIENTE)"].apply(fmt_pct)
                            resto_p_show["QTD"] = resto_p_show["QTD"].apply(lambda v: "-" if pd.isna(v) else f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                            demais_produtos_pdf = resto_p_show[["DESCRICAO", "CODIGO", "QTD", "FAT (R$)", "% SOBRE LINHA (CLIENTE)"]].copy()
                            st.dataframe(
                                demais_produtos_pdf,
                                use_container_width=True,
                                hide_index=True
                            )
                            botao_download_pdf(demais_produtos_pdf, f"Demais Produtos - {marca_sel} - {linha_prod_sel}", f"demais_produtos_{str(marca_sel).replace(' ', '_')}_{str(linha_prod_sel).replace(' ', '_')}.pdf")
                            add_pdf_section(f"Análise por Marca - Demais Produtos - {marca_sel} - {linha_prod_sel}", demais_produtos_pdf)
            else:
                st.info("Não encontrei colunas de **código** e/ou **descrição** do produto na base para detalhar produtos dentro da linha. (Procurei por variações de 'COD*' e 'DESCR*' após normalização.)")
else:
    st.info("Preciso das colunas MARCA, CLIENTE e LINHA para montar a análise por marca.")





# =========================
# AGENTE DE BI — INTENÇÕES GERENCIAIS
# =========================
st.divider()
st.markdown("## ChatBI Única — Perguntas com Gemini")
st.caption(
    "Pergunte qualquer coisa em linguagem natural. O Gemini sempre interpreta e responde; quando houver pergunta de BI, o Python/Pandas calcula os números e o Gemini transforma em análise consultiva."
)


# -------------------------------------------------
# Normalização e motor de intenções
# -------------------------------------------------
def _agent_normalizar_pergunta(txt: str) -> str:
    txt = "" if txt is None else str(txt)
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii")
    txt = txt.lower().strip()
    txt = re.sub(r"[^a-z0-9\s\-/]", " ", txt)
    txt = re.sub(r"\s+", " ", txt)
    return txt


def _tem(p: str, termos) -> bool:
    return any(t in p for t in termos)


def _score_termos(p: str, termos) -> int:
    return sum(1 for t in termos if t in p)


# Mais de 30 intenções por conceito, não por pergunta exata.
# Cada intenção combina: assunto, período e tipo de análise.
INTENCOES_BI = {
    "venda_hoje": {
        "acao": ["venda", "vendeu", "faturamento", "faturou", "receita", "total"],
        "tempo": ["hoje", "dia", "diario"],
        "entidade": []
    },
    "venda_mes": {
        "acao": ["venda", "vendeu", "faturamento", "faturou", "receita", "total"],
        "tempo": ["mes", "mensal"],
        "entidade": []
    },
    "venda_periodo": {
        "acao": ["venda", "vendeu", "faturamento", "faturou", "receita", "total"],
        "tempo": ["periodo", "filtro", "selecionado"],
        "entidade": []
    },
    "previsao_fechamento": {
        "acao": ["previsao", "projecao", "fechamento", "fechar", "deve fechar", "vamos fechar", "ritmo"],
        "tempo": ["mes", "mensal", "fechamento"],
        "entidade": []
    },
    "meta_falta": {
        "acao": ["falta", "precisa", "bater", "atingir", "alcançar", "alcancar"],
        "tempo": ["mes", "mensal", "meta"],
        "entidade": ["meta"]
    },
    "meta_percentual": {
        "acao": ["percentual", "porcentagem", "%", "atingido", "atingimos", "realizado"],
        "tempo": ["mes", "mensal", "meta"],
        "entidade": ["meta"]
    },
    "meta_projecao": {
        "acao": ["vamos bater", "bate", "bater", "projecao", "previsao", "tendencia"],
        "tempo": ["mes", "mensal", "meta"],
        "entidade": ["meta"]
    },
    "meta_dia": {
        "acao": ["por dia", "diaria", "diario", "precisa vender", "vender por dia"],
        "tempo": ["mes", "mensal", "meta"],
        "entidade": ["meta"]
    },
    "ano1_falta": {
        "acao": ["falta", "superar", "crescer", "passar", "bater"],
        "tempo": ["ano passado", "ano 1", "ano-1", "ano anterior"],
        "entidade": []
    },
    "ano1_comparativo": {
        "acao": ["comparar", "comparativo", "contra", "crescimento", "diferença", "diferenca", "variacao"],
        "tempo": ["ano passado", "ano 1", "ano-1", "ano anterior"],
        "entidade": []
    },
    "ano1_projecao": {
        "acao": ["previsao", "projecao", "vamos superar", "tendencia", "fechamento"],
        "tempo": ["ano passado", "ano 1", "ano-1", "ano anterior"],
        "entidade": []
    },
    "cliente_hoje": {
        "acao": ["top", "ranking", "maior", "melhor", "principais", "cliente", "clientes"],
        "tempo": ["hoje", "dia"],
        "entidade": ["cliente", "clientes"]
    },
    "cliente_mes": {
        "acao": ["top", "ranking", "maior", "melhor", "principais", "cliente", "clientes"],
        "tempo": ["mes", "mensal"],
        "entidade": ["cliente", "clientes"]
    },
    "cliente_periodo": {
        "acao": ["top", "ranking", "maior", "melhor", "principais", "cliente", "clientes"],
        "tempo": ["periodo", "filtro", "selecionado"],
        "entidade": ["cliente", "clientes"]
    },
    "clientes_quantidade_hoje": {
        "acao": ["quantos", "quantidade", "ativos", "compraram"],
        "tempo": ["hoje", "dia"],
        "entidade": ["cliente", "clientes"]
    },
    "clientes_quantidade_mes": {
        "acao": ["quantos", "quantidade", "ativos", "compraram"],
        "tempo": ["mes", "mensal"],
        "entidade": ["cliente", "clientes"]
    },
    "marca_hoje": {
        "acao": ["top", "ranking", "mais vendeu", "mais venderam", "maior", "principais", "marca", "marcas"],
        "tempo": ["hoje", "dia"],
        "entidade": ["marca", "marcas"]
    },
    "marca_mes": {
        "acao": ["top", "ranking", "mais vendeu", "mais venderam", "maior", "principais", "marca", "marcas"],
        "tempo": ["mes", "mensal"],
        "entidade": ["marca", "marcas"]
    },
    "marca_periodo": {
        "acao": ["top", "ranking", "mais vendeu", "mais venderam", "maior", "principais", "marca", "marcas"],
        "tempo": ["periodo", "filtro", "selecionado"],
        "entidade": ["marca", "marcas"]
    },
    "linha_hoje": {
        "acao": ["top", "ranking", "mais vendeu", "mais venderam", "maior", "principais", "linha", "linhas"],
        "tempo": ["hoje", "dia"],
        "entidade": ["linha", "linhas"]
    },
    "linha_mes": {
        "acao": ["top", "ranking", "mais vendeu", "mais venderam", "maior", "principais", "linha", "linhas"],
        "tempo": ["mes", "mensal"],
        "entidade": ["linha", "linhas"]
    },
    "linha_periodo": {
        "acao": ["top", "ranking", "mais vendeu", "mais venderam", "maior", "principais", "linha", "linhas"],
        "tempo": ["periodo", "filtro", "selecionado"],
        "entidade": ["linha", "linhas"]
    },
    "produto_hoje": {
        "acao": ["top", "ranking", "mais vendido", "mais vendidos", "produto", "produtos", "item", "itens"],
        "tempo": ["hoje", "dia"],
        "entidade": ["produto", "produtos", "item", "itens"]
    },
    "produto_mes": {
        "acao": ["top", "ranking", "mais vendido", "mais vendidos", "produto", "produtos", "item", "itens"],
        "tempo": ["mes", "mensal"],
        "entidade": ["produto", "produtos", "item", "itens"]
    },
    "produto_periodo": {
        "acao": ["top", "ranking", "mais vendido", "mais vendidos", "produto", "produtos", "item", "itens"],
        "tempo": ["periodo", "filtro", "selecionado"],
        "entidade": ["produto", "produtos", "item", "itens"]
    },
    "vendedor_hoje": {
        "acao": ["top", "ranking", "maior", "melhor", "quem mais", "vendedor", "vendedores"],
        "tempo": ["hoje", "dia"],
        "entidade": ["vendedor", "vendedores"]
    },
    "vendedor_mes": {
        "acao": ["top", "ranking", "maior", "melhor", "quem mais", "vendedor", "vendedores"],
        "tempo": ["mes", "mensal"],
        "entidade": ["vendedor", "vendedores"]
    },
    "vendedor_periodo": {
        "acao": ["top", "ranking", "maior", "melhor", "quem mais", "vendedor", "vendedores"],
        "tempo": ["periodo", "filtro", "selecionado"],
        "entidade": ["vendedor", "vendedores"]
    },
    "margem_hoje": {
        "acao": ["margem", "lucro bruto", "rentabilidade"],
        "tempo": ["hoje", "dia"],
        "entidade": []
    },
    "margem_mes": {
        "acao": ["margem", "lucro bruto", "rentabilidade"],
        "tempo": ["mes", "mensal"],
        "entidade": []
    },
    "ticket_hoje": {
        "acao": ["ticket", "ticket medio", "media por cliente"],
        "tempo": ["hoje", "dia"],
        "entidade": []
    },
    "ticket_mes": {
        "acao": ["ticket", "ticket medio", "media por cliente"],
        "tempo": ["mes", "mensal"],
        "entidade": []
    },
    "resumo_executivo": {
        "acao": ["resumo", "analise", "gerencial", "executivo", "como esta", "diagnostico"],
        "tempo": ["mes", "mensal", "periodo"],
        "entidade": []
    },
    "oportunidade": {
        "acao": ["oportunidade", "oportunidades", "onde crescer", "potencial"],
        "tempo": ["mes", "mensal", "periodo"],
        "entidade": []
    },
    "risco": {
        "acao": ["risco", "riscos", "alerta", "problema", "atenção", "atencao"],
        "tempo": ["mes", "mensal", "periodo"],
        "entidade": []
    }
}


SINONIMOS_ENTIDADE = {
    "cliente": ["cliente", "clientes", "comprador", "compradores"],
    "marca": ["marca", "marcas", "fabricante", "fornecedor"],
    "linha": ["linha", "linhas", "categoria", "categorias", "segmento", "segmentos"],
    "produto": ["produto", "produtos", "item", "itens", "sku", "mercadoria", "mercadorias"],
    "vendedor": ["vendedor", "vendedores", "consultor", "consultores", "representante", "representantes"],
    "meta": ["meta", "metas", "objetivo"],
    "ano1": ["ano passado", "ano anterior", "ano 1", "ano-1", "2025"],
    "margem": ["margem", "lucro bruto", "rentabilidade"],
    "ticket": ["ticket", "ticket medio", "media por cliente"],
}

SINONIMOS_TEMPO = {
    "hoje": ["hoje", "dia", "diario", "diaria"],
    "mes": ["mes", "mensal", "mes atual", "este mes", "do mes"],
    "periodo": ["periodo", "filtro", "selecionado", "geral"],
}

SINONIMOS_ACAO = {
    "top": ["top", "ranking", "rank", "maior", "maiores", "melhor", "melhores", "principal", "principais", "quem mais", "mais vendeu", "mais venderam"],
    "total": ["quanto", "total", "venda", "vendas", "vendeu", "faturamento", "faturou", "receita"],
    "previsao": ["previsao", "projecao", "tendencia", "fechamento", "fechar", "ritmo", "deve fechar", "vamos fechar"],
    "falta": ["falta", "faltam", "precisa", "necessario", "necessario", "bater", "atingir", "superar", "crescer"],
    "comparar": ["comparar", "comparativo", "contra", "versus", "vs", "crescimento", "diferença", "diferenca", "variacao"],
    "quantidade": ["quantos", "quantidade", "qtd", "ativos", "compraram"],
    "analise": ["analise", "resumo", "gerencial", "executivo", "diagnostico", "como esta"],
}


def _detectar_entidade(p: str) -> str | None:
    scores = {ent: _score_termos(p, termos) for ent, termos in SINONIMOS_ENTIDADE.items()}
    ent, score = max(scores.items(), key=lambda x: x[1])
    return ent if score > 0 else None


def _detectar_tempo(p: str) -> str:
    # 'hoje' precisa ter prioridade sobre 'dia' genérico quando houver conflito.
    if _tem(p, ["hoje"]):
        return "hoje"
    if _tem(p, SINONIMOS_TEMPO["mes"]):
        return "mes"
    if _tem(p, SINONIMOS_TEMPO["periodo"]):
        return "periodo"
    if _tem(p, ["dia", "diario", "diaria"]):
        return "hoje"
    return "mes"


def _detectar_acao(p: str) -> str:
    scores = {acao: _score_termos(p, termos) for acao, termos in SINONIMOS_ACAO.items()}
    acao, score = max(scores.items(), key=lambda x: x[1])
    if score == 0:
        return "top"
    return acao


INTENTS_PERMITIDAS_GEMINI = [
    "venda_hoje", "venda_mes", "venda_periodo",
    "previsao_fechamento",
    "meta_falta", "meta_percentual", "meta_projecao", "meta_dia",
    "ano1_falta", "ano1_comparativo", "ano1_projecao",
    "cliente_hoje", "cliente_mes", "cliente_periodo",
    "clientes_quantidade_hoje", "clientes_quantidade_mes",
    "marca_hoje", "marca_mes", "marca_periodo",
    "linha_hoje", "linha_mes", "linha_periodo",
    "produto_hoje", "produto_mes", "produto_periodo",
    "vendedor_hoje", "vendedor_mes", "vendedor_periodo",
    "margem_hoje", "margem_mes",
    "ticket_hoje", "ticket_mes",
    "resumo_executivo", "oportunidade", "risco",
    "nao_mapeada",
]


def _gemini_api_key():
    """Lê a chave do Gemini pelo Secrets do Streamlit ou por variável de ambiente."""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return str(st.secrets["GEMINI_API_KEY"]).strip()
    except Exception:
        pass
    return os.getenv("GEMINI_API_KEY", "").strip()


def _gemini_model_name():
    """
    Modelo padrão do Gemini.
    Pode ser alterado no Streamlit Secrets com:
    GEMINI_MODEL = "gemini-2.5-flash"
    """
    try:
        if "GEMINI_MODEL" in st.secrets:
            return str(st.secrets["GEMINI_MODEL"]).strip()
    except Exception:
        pass
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()


def _gemini_disponivel():
    return bool(_gemini_api_key()) and (genai_new is not None or genai_legacy is not None)




MESES_NOME_NUM = {
    "janeiro": 1, "jan": 1,
    "fevereiro": 2, "fev": 2,
    "marco": 3, "mar": 3, "março": 3,
    "abril": 4, "abr": 4,
    "maio": 5, "mai": 5,
    "junho": 6, "jun": 6,
    "julho": 7, "jul": 7,
    "agosto": 8, "ago": 8,
    "setembro": 9, "set": 9,
    "outubro": 10, "out": 10,
    "novembro": 11, "nov": 11,
    "dezembro": 12, "dez": 12,
}


def _norm_match(v) -> str:
    s = "" if v is None else str(v)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.upper().strip()
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _extrair_ano_mes(pergunta_original: str, p_normalizada: str) -> dict:
    filtros = {}
    anos = re.findall(r"(20\d{2})", pergunta_original or "") + re.findall(r"(20\d{2})", p_normalizada or "")
    if anos:
        filtros["ano"] = int(anos[-1])
    for nome, num in MESES_NOME_NUM.items():
        if re.search(rf"{re.escape(nome)}", p_normalizada):
            filtros["mes"] = num
            break
    return filtros


def _valores_coluna_para_prompt(coluna: str, limite: int = 80) -> list[str]:
    try:
        if coluna not in df.columns:
            return []
        vals = df[coluna].dropna().astype(str).map(norm_text)
        vals = vals[vals.str.strip() != ""].drop_duplicates().tolist()
        return sorted(vals, key=lambda x: x.upper())[:limite]
    except Exception:
        return []


def _detectar_valor_dimensional(pergunta_original: str, p_normalizada: str, coluna: str) -> str | None:
    if coluna not in df.columns:
        return None
    texto_norm = _norm_match((pergunta_original or "") + " " + (p_normalizada or ""))
    vals = df[coluna].dropna().astype(str).map(norm_text).drop_duplicates().tolist()
    candidatos = []
    for val in vals:
        val_limpo = norm_text(val)
        if not val_limpo:
            continue
        vnorm = _norm_match(val_limpo)
        if not vnorm:
            continue
        if re.search(rf"(^|\s){re.escape(vnorm)}($|\s)", texto_norm):
            candidatos.append((len(vnorm), val_limpo))
        elif len(vnorm) >= 4 and vnorm in texto_norm:
            candidatos.append((len(vnorm), val_limpo))
    if not candidatos:
        return None
    candidatos.sort(reverse=True)
    return candidatos[0][1]


def _extrair_filtros_pergunta(pergunta_original: str, p_normalizada: str) -> dict:
    filtros = _extrair_ano_mes(pergunta_original, p_normalizada)
    for chave, coluna in {"marca":"MARCA", "linha":"LINHA", "segmento":"SEGMENTO", "cliente":"CLIENTE", "vendedor":"VENDEDOR"}.items():
        val = _detectar_valor_dimensional(pergunta_original, p_normalizada, coluna)
        if val:
            filtros[chave] = val
    try:
        cod_col, desc_col, _ = _agent_coluna_produto(df)
    except Exception:
        cod_col, desc_col = None, None
    produto_val = _detectar_valor_dimensional(pergunta_original, p_normalizada, desc_col) if desc_col else None
    if produto_val:
        filtros["produto"] = produto_val
    return filtros


def _mes_int_para_nome(mes: int | str | None) -> str:
    try:
        return month_key_from_monthnum(int(mes))
    except Exception:
        return ""

def _classificar_intencao_regras(p: str) -> dict:
    """Fallback local: mantém o app funcionando mesmo sem Gemini/API."""
    entidade = _detectar_entidade(p)
    tempo = _detectar_tempo(p)
    acao = _detectar_acao(p)

    if acao == "analise" or _tem(p, ["resumo executivo", "analise gerencial", "como esta o negocio", "diagnostico"]):
        return {"intent": "resumo_executivo", "entidade": entidade, "tempo": tempo, "acao": "analise", "origem": "regras"}
    if entidade == "meta" and acao == "falta":
        if _tem(p, ["por dia", "diaria", "diario", "vender por dia"]):
            return {"intent": "meta_dia", "entidade": entidade, "tempo": tempo, "acao": acao, "origem": "regras"}
        return {"intent": "meta_falta", "entidade": entidade, "tempo": tempo, "acao": acao, "origem": "regras"}
    if entidade == "meta" and acao == "previsao":
        return {"intent": "meta_projecao", "entidade": entidade, "tempo": tempo, "acao": acao, "origem": "regras"}
    if entidade == "meta":
        return {"intent": "meta_percentual", "entidade": entidade, "tempo": tempo, "acao": acao, "origem": "regras"}
    if entidade == "ano1" and acao == "previsao":
        return {"intent": "ano1_projecao", "entidade": entidade, "tempo": tempo, "acao": acao, "origem": "regras"}
    if entidade == "ano1" and acao == "falta":
        return {"intent": "ano1_falta", "entidade": entidade, "tempo": tempo, "acao": acao, "origem": "regras"}
    if entidade == "ano1":
        return {"intent": "ano1_comparativo", "entidade": entidade, "tempo": tempo, "acao": acao, "origem": "regras"}
    if acao == "previsao":
        return {"intent": "previsao_fechamento", "entidade": entidade, "tempo": tempo, "acao": acao, "origem": "regras"}
    if entidade == "margem":
        return {"intent": f"margem_{tempo if tempo in ['hoje', 'mes'] else 'mes'}", "entidade": entidade, "tempo": tempo, "acao": acao, "origem": "regras"}
    if entidade == "ticket":
        return {"intent": f"ticket_{tempo if tempo in ['hoje', 'mes'] else 'mes'}", "entidade": entidade, "tempo": tempo, "acao": acao, "origem": "regras"}
    if entidade == "cliente" and acao == "quantidade":
        return {"intent": f"clientes_quantidade_{tempo if tempo in ['hoje', 'mes'] else 'mes'}", "entidade": entidade, "tempo": tempo, "acao": acao, "origem": "regras"}
    if entidade is None and acao == "total":
        return {"intent": f"venda_{tempo}", "entidade": entidade, "tempo": tempo, "acao": acao, "origem": "regras"}
    if entidade in ["cliente", "marca", "linha", "produto", "vendedor"]:
        sufixo = tempo if tempo in ["hoje", "mes", "periodo"] else "mes"
        return {"intent": f"{entidade}_{sufixo}", "entidade": entidade, "tempo": sufixo, "acao": acao, "origem": "regras"}
    if _tem(p, ["oportunidade", "oportunidades", "onde crescer", "potencial"]):
        return {"intent": "oportunidade", "entidade": entidade, "tempo": tempo, "acao": acao, "origem": "regras"}
    if _tem(p, ["risco", "riscos", "alerta", "problema", "atencao"]):
        return {"intent": "risco", "entidade": entidade, "tempo": tempo, "acao": acao, "origem": "regras"}
    return {"intent": "nao_mapeada", "entidade": entidade, "tempo": tempo, "acao": acao, "origem": "regras"}


def _extrair_json_gemini(texto: str) -> dict | None:
    if not texto:
        return None
    try:
        return json.loads(texto)
    except Exception:
        pass
    m = re.search(r"\{.*\}", texto, flags=re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def _classificar_intencao_gemini(pergunta_original: str, p_normalizada: str) -> dict | None:
    """Usa Gemini para interpretar a pergunta e devolver uma intenção estruturada em JSON."""
    api_key = _gemini_api_key()
    if not _gemini_disponivel():
        return None

    model_name = _gemini_model_name()

    prompt = f"""
Você é um classificador de perguntas para um dashboard comercial em Python/Pandas.
Sua tarefa é transformar a pergunta do usuário em uma intenção de BI.

Regras obrigatórias:
1. Responda somente em JSON válido.
2. Não calcule valores.
3. Não invente dados.
4. Sua função é apenas classificar a pergunta para que o Python faça os cálculos.
5. Se a pergunta pedir análise, diagnóstico, resumo, risco ou oportunidade, use uma intenção executiva.
6. Se não houver segurança, use "nao_mapeada".

Intenções permitidas:
{json.dumps(INTENTS_PERMITIDAS_GEMINI, ensure_ascii=False)}

Valores conhecidos para ajudar a preencher filtros:
- marcas: {json.dumps(_valores_coluna_para_prompt("MARCA", 120), ensure_ascii=False)}
- linhas: {json.dumps(_valores_coluna_para_prompt("LINHA", 120), ensure_ascii=False)}
- segmentos: {json.dumps(_valores_coluna_para_prompt("SEGMENTO", 80), ensure_ascii=False)}

Campos permitidos:
- intent: uma das intenções permitidas
- entidade: cliente, marca, linha, produto, vendedor, meta, ano1, margem, ticket ou null
- tempo: hoje, mes ou periodo
- acao: top, total, falta, percentual, previsao, comparativo, analise, quantidade, ticket, margem ou null
- filtros: objeto JSON com os filtros encontrados na pergunta. Use as chaves marca, linha, segmento, produto, cliente, vendedor, ano, mes. Se não houver filtro, use {{}}.
- comparar_ano1: true ou false quando a pergunta pedir comparação contra Ano-1, ano passado ou 2025
- confianca: número de 0 a 1

Exemplos:
Pergunta: "quanto vendeu hoje?"
Resposta: {{"intent":"venda_hoje","entidade":null,"tempo":"hoje","acao":"total","confianca":0.95}}

Pergunta: "top clientes do mês"
Resposta: {{"intent":"cliente_mes","entidade":"cliente","tempo":"mes","acao":"top","filtros":{{}},"comparar_ano1":false,"confianca":0.95}}

Pergunta: "qual cliente mais comprou produtos da marca 3M em 2026?"
Resposta: {{"intent":"cliente_periodo","entidade":"cliente","tempo":"periodo","acao":"top","filtros":{{"marca":"3M","ano":2026}},"comparar_ano1":false,"confianca":0.98}}

Pergunta: "quais produtos da linha abrasivos venderam mais em maio de 2026?"
Resposta: {{"intent":"produto_mes","entidade":"produto","tempo":"mes","acao":"top","filtros":{{"linha":"abrasivos","ano":2026,"mes":5}},"comparar_ano1":false,"confianca":0.98}}

Pergunta: "quais marcas venderam mais no período?"
Resposta: {{"intent":"marca_periodo","entidade":"marca","tempo":"periodo","acao":"top","confianca":0.95}}

Pergunta: "quanto falta para bater a meta?"
Resposta: {{"intent":"meta_falta","entidade":"meta","tempo":"mes","acao":"falta","confianca":0.95}}

Pergunta original:
{pergunta_original}

Pergunta normalizada:
{p_normalizada}
""".strip()

    try:
        # SDK novo: package google-genai
        if genai_new is not None:
            client = genai_new.Client(api_key=api_key)
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={
                    "temperature": 0,
                    "response_mime_type": "application/json",
                },
            )
            txt = getattr(resp, "text", "") or ""
        else:
            # SDK antigo: package google-generativeai
            genai_legacy.configure(api_key=api_key)
            model = genai_legacy.GenerativeModel(model_name)
            resp = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0,
                    "response_mime_type": "application/json",
                },
            )
            txt = getattr(resp, "text", "") or ""

        dados = _extrair_json_gemini(txt)
        if not isinstance(dados, dict):
            return None

        intent = str(dados.get("intent", "nao_mapeada")).strip()
        if intent not in INTENTS_PERMITIDAS_GEMINI:
            return None

        tempo = str(dados.get("tempo", "mes")).strip().lower()
        if tempo not in ["hoje", "mes", "periodo"]:
            tempo = "mes"

        entidade = dados.get("entidade", None)
        if entidade is not None:
            entidade = str(entidade).strip().lower()
            if entidade in ["", "none", "null", "nenhuma"]:
                entidade = None

        acao = dados.get("acao", "analise")
        if acao is not None:
            acao = str(acao).strip().lower()
            if acao in ["", "none", "null"]:
                acao = "analise"

        filtros = dados.get("filtros", {})
        if not isinstance(filtros, dict):
            filtros = {}

        return {
            "intent": intent,
            "entidade": entidade,
            "tempo": tempo,
            "acao": acao,
            "filtros": filtros,
            "comparar_ano1": bool(dados.get("comparar_ano1", False)),
            "origem": "Gemini",
            "modelo": model_name,
            "confianca": dados.get("confianca", None),
        }

    except Exception as e:
        # Em produção, não quebra o dashboard se a API falhar.
        st.session_state["ultimo_erro_gemini"] = str(e)
        return None



def _classificar_intencao(pergunta_original: str) -> dict:
    p = _agent_normalizar_pergunta(pergunta_original)
    filtros_local = _extrair_filtros_pergunta(pergunta_original, p)
    cls_gemini = _classificar_intencao_gemini(pergunta_original, p)
    if cls_gemini:
        filtros_gemini = cls_gemini.get("filtros", {})
        if not isinstance(filtros_gemini, dict):
            filtros_gemini = {}
        filtros = {**filtros_local, **{k: v for k, v in filtros_gemini.items() if v not in [None, "", [], {}]}}
        cls_gemini["filtros"] = filtros
        if filtros.get("ano") and not filtros.get("mes") and cls_gemini.get("tempo") == "mes":
            cls_gemini["tempo"] = "periodo"
            if str(cls_gemini.get("intent", "")).endswith("_mes"):
                cls_gemini["intent"] = str(cls_gemini["intent"]).replace("_mes", "_periodo")
        return cls_gemini
    cls = _classificar_intencao_regras(p)
    cls["filtros"] = filtros_local
    cls["comparar_ano1"] = bool(_tem(p, ["ano 1", "ano-1", "ano passado", "ano anterior"]))
    if filtros_local.get("ano") and not filtros_local.get("mes") and cls.get("tempo") == "mes":
        cls["tempo"] = "periodo"
        if str(cls.get("intent", "")).endswith("_mes"):
            cls["intent"] = str(cls["intent"]).replace("_mes", "_periodo")
    return cls


# -------------------------------------------------
# Funções de cálculo do agente
# -------------------------------------------------
def _agent_coluna_produto(df_ref: pd.DataFrame):
    cols = list(df_ref.columns)
    desc_col = find_col(cols, exact=["DESCRICAO", "DESCRICAO DO ITEM", "PRODUTO", "ITEM", "NOME DO PRODUTO", "DESCRIÇÃO"], must_contain=["DESCR"])
    cod_col = find_col(cols, exact=["CODIGO", "COD", "COD. ITEM", "CODIGO ITEM", "CÓDIGO"], must_contain=["COD"])
    qtd_col = find_col(cols, exact=["QTD", "QTDE", "QUANTIDADE", "QUANT."], must_contain=["QTD"])
    if desc_col is None and "PRODUTO" in cols:
        desc_col = "PRODUTO"
    if desc_col is None and "ITEM" in cols:
        desc_col = "ITEM"
    return cod_col, desc_col, qtd_col


def _agent_base(vendedor: str = "TODOS") -> pd.DataFrame:
    base = df.copy()
    if vendedor != "TODOS" and "VENDEDOR" in base.columns:
        base = base[base["VENDEDOR"].fillna("").astype(str).map(norm_text) == norm_text(vendedor)].copy()
    return base


def _agent_datas_ref(base: pd.DataFrame):
    if base.empty:
        return None, None, None, ""
    hoje_real = datetime.now().date()
    datas = set(base["DIA"].dropna().tolist())
    hoje_base = hoje_real if hoje_real in datas else base["DIA"].max()
    ano_ref = int(pd.to_datetime(hoje_base).year)
    mes_num_ref = int(pd.to_datetime(hoje_base).month)
    mes_ref = month_key_from_monthnum(mes_num_ref)
    return hoje_base, ano_ref, mes_num_ref, mes_ref


def _agent_recortes(base: pd.DataFrame):
    hoje_base, ano_ref, mes_num_ref, mes_ref = _agent_datas_ref(base)
    if hoje_base is None:
        return base.copy(), base.copy(), base.copy(), hoje_base, ano_ref, mes_num_ref, mes_ref
    df_hoje = base[base["DIA"] == hoje_base].copy()
    df_mes = base[(base["ANO"] == ano_ref) & (base["MES_NUM"] == mes_num_ref)].copy()
    # período atual do filtro lateral, respeitando vendedor
    df_periodo_agent = df_periodo.copy() if "df_periodo" in globals() else df_mes.copy()
    return df_hoje, df_mes, df_periodo_agent, hoje_base, ano_ref, mes_num_ref, mes_ref


def _agent_escolher_recorte(tempo: str, df_hoje: pd.DataFrame, df_mes: pd.DataFrame, df_periodo_agent: pd.DataFrame) -> pd.DataFrame:
    if tempo == "hoje":
        return df_hoje
    if tempo == "periodo":
        return df_periodo_agent
    return df_mes


def _agent_total(base_ref: pd.DataFrame) -> float:
    return float(base_ref["VR_TOTAL"].sum()) if base_ref is not None and not base_ref.empty else 0.0


def _agent_periodo_label(tempo: str, hoje_base, mes_ref: str, ano_ref: int) -> str:
    if tempo == "hoje":
        return pd.to_datetime(hoje_base).strftime("%d/%m/%Y")
    if tempo == "periodo":
        return "período filtrado"
    return f"{mes_ref}/{ano_ref}"


def _agent_top(base_ref: pd.DataFrame, coluna: str, titulo_coluna: str, n: int = 10) -> str:
    if base_ref is None or base_ref.empty:
        return "Não encontrei vendas para esse recorte."
    if coluna not in base_ref.columns:
        return f"Não encontrei a coluna {coluna} na base para responder essa intenção."
    t = base_ref.copy()
    t[coluna] = t[coluna].fillna("N/I").astype(str).map(norm_text)
    t = t[t[coluna].astype(str).str.strip() != ""].copy()
    if t.empty:
        return f"Não encontrei dados válidos de {titulo_coluna.lower()} nesse recorte."
    rank = (
        t.groupby(coluna, as_index=False)["VR_TOTAL"].sum()
        .sort_values("VR_TOTAL", ascending=False)
        .head(n)
    )
    total_recorte = _agent_total(base_ref)
    linhas = []
    for i, row in rank.iterrows():
        nome = row[coluna]
        valor = float(row["VR_TOTAL"])
        pct = (valor / total_recorte * 100) if total_recorte else None
        linhas.append(f"{i+1}. {nome}: {format_brl(valor)} ({fmt_pct(pct)})")
    return "\n".join(linhas)


def _agent_top_produtos(base_ref: pd.DataFrame, n: int = 10) -> str:
    if base_ref is None or base_ref.empty:
        return "Não encontrei vendas para esse recorte."
    cod_col, desc_col, qtd_col = _agent_coluna_produto(base_ref)
    if desc_col is None:
        return "Não encontrei uma coluna de descrição/produto na base para montar o ranking de produtos."
    t = base_ref.copy()
    t[desc_col] = t[desc_col].fillna("N/I").astype(str).map(norm_text)
    agg = {"VR_TOTAL": "sum"}
    if qtd_col is not None:
        t[qtd_col] = pd.to_numeric(t[qtd_col], errors="coerce").fillna(0)
        agg[qtd_col] = "sum"
    rank = t.groupby(desc_col, as_index=False).agg(agg).sort_values("VR_TOTAL", ascending=False).head(n)
    total_recorte = _agent_total(base_ref)
    linhas = []
    for i, row in rank.iterrows():
        qtd_txt = ""
        if qtd_col is not None:
            qtd_txt = f" | Qtd: {float(row[qtd_col]):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        pct = (float(row["VR_TOTAL"]) / total_recorte * 100) if total_recorte else None
        linhas.append(f"{i+1}. {row[desc_col]}: {format_brl(row['VR_TOTAL'])} ({fmt_pct(pct)}){qtd_txt}")
    return "\n".join(linhas)


def _agent_margem(base_ref: pd.DataFrame) -> str:
    fat = _agent_total(base_ref)
    custo = float(base_ref["CUSTO_NUM"].sum()) if base_ref is not None and not base_ref.empty and "CUSTO_NUM" in base_ref.columns else 0.0
    margem = fat - custo
    margem_pct = (margem / fat * 100) if fat else None
    return f"Margem bruta: {format_brl(margem)} ({fmt_pct(margem_pct)}) | Faturamento: {format_brl(fat)} | Custo: {format_brl(custo)}"


def _agent_previsao(df_mes_ref: pd.DataFrame, mes_ref: str) -> tuple[float, float, int, int]:
    dias_uteis = int(DIAS_UTEIS_MENSAL.get(mes_ref, 0))
    if df_mes_ref is None or df_mes_ref.empty:
        return 0.0, 0.0, dias_uteis, 0
    vendas_dia = df_mes_ref.groupby("DIA", as_index=False)["VR_TOTAL"].sum()
    vendas_dia = vendas_dia[vendas_dia["VR_TOTAL"] > 0]
    dias_com_venda = int(len(vendas_dia))
    media = float(vendas_dia["VR_TOTAL"].mean()) if not vendas_dia.empty else 0.0
    return media * dias_uteis, media, dias_uteis, dias_com_venda


def _agent_meta_mes(df_mes_ref: pd.DataFrame, mes_ref: str) -> tuple[float, float, float, float]:
    real = _agent_total(df_mes_ref)
    meta = float(METAS_MENSAL.get(mes_ref, 0.0))
    falta = max(meta - real, 0.0)
    pct = (real / meta * 100) if meta else 0.0
    return real, meta, falta, pct


def _agent_ano1_mes(df_mes_ref: pd.DataFrame, mes_ref: str) -> tuple[float, float, float, float]:
    real = _agent_total(df_mes_ref)
    ano1 = float(ANO_1_MENSAL.get(mes_ref, 0.0))
    falta = max(ano1 - real, 0.0)
    cresc = ((real - ano1) / ano1 * 100) if ano1 else None
    return real, ano1, falta, cresc


def _agent_ticket_medio(base_ref: pd.DataFrame) -> str:
    if base_ref is None or base_ref.empty:
        return "Não encontrei vendas para calcular ticket médio."
    fat = _agent_total(base_ref)
    if "CLIENTE" in base_ref.columns:
        clientes = base_ref["CLIENTE"].fillna("").astype(str).map(norm_text).replace("", pd.NA).dropna().nunique()
        ticket = fat / clientes if clientes else 0.0
        return f"Ticket médio por cliente: {format_brl(ticket)} | Faturamento: {format_brl(fat)} | Clientes: {clientes:,}".replace(",", ".")
    qtd_docs = len(base_ref)
    ticket = fat / qtd_docs if qtd_docs else 0.0
    return f"Ticket médio por lançamento: {format_brl(ticket)} | Faturamento: {format_brl(fat)} | Lançamentos: {qtd_docs:,}".replace(",", ".")


def _agent_quantidade_clientes(base_ref: pd.DataFrame) -> str:
    if base_ref is None or base_ref.empty:
        return "Não encontrei vendas para contar clientes."
    if "CLIENTE" not in base_ref.columns:
        return "Não encontrei a coluna CLIENTE na base."
    clientes = base_ref["CLIENTE"].fillna("").astype(str).map(norm_text).replace("", pd.NA).dropna().nunique()
    return f"Clientes únicos no recorte: {clientes:,}.".replace(",", ".")


def _agent_resumo_executivo(base: pd.DataFrame) -> str:
    df_hoje, df_mes_ref, df_periodo_agent, hoje_base, ano_ref, mes_num_ref, mes_ref = _agent_recortes(base)
    real, meta, falta_meta, pct_meta = _agent_meta_mes(df_mes_ref, mes_ref)
    prev, media, dias_uteis, dias_com_venda = _agent_previsao(df_mes_ref, mes_ref)
    _, ano1, falta_ano1, cresc = _agent_ano1_mes(df_mes_ref, mes_ref)
    top_cliente = _agent_top(df_mes_ref, "CLIENTE", "Cliente", 1) if "CLIENTE" in df_mes_ref.columns else "Cliente líder: coluna CLIENTE não encontrada"
    top_marca = _agent_top(df_mes_ref, "MARCA", "Marca", 1) if "MARCA" in df_mes_ref.columns else "Marca líder: coluna MARCA não encontrada"
    top_linha = _agent_top(df_mes_ref, "LINHA", "Linha", 1) if "LINHA" in df_mes_ref.columns else "Linha líder: coluna LINHA não encontrada"
    status_meta = "tende a bater a meta" if prev >= meta and meta else "precisa acelerar para bater a meta"
    status_ano1 = "tende a superar o Ano-1" if prev >= ano1 and ano1 else "ainda está abaixo da referência Ano-1"
    return (
        f"Resumo executivo do mês {mes_ref}/{ano_ref}:\n"
        f"- Venda de hoje: {format_brl(_agent_total(df_hoje))}\n"
        f"- Venda do mês: {format_brl(real)}\n"
        f"- Previsão de fechamento: {format_brl(prev)} (média diária: {format_brl(media)} em {dias_com_venda} dias com venda x {dias_uteis} dias úteis)\n"
        f"- Meta: {format_brl(meta)} | Atingido: {fmt_pct(pct_meta)} | Falta: {format_brl(falta_meta)}\n"
        f"- Ano-1 ({ANO_1}): {format_brl(ano1)} | Crescimento atual: {fmt_pct(cresc)} | Falta para superar: {format_brl(falta_ano1)}\n"
        f"- Cliente líder: {top_cliente.split(': ', 1)[-1] if ': ' in top_cliente else top_cliente}\n"
        f"- Marca líder: {top_marca.split(': ', 1)[-1] if ': ' in top_marca else top_marca}\n"
        f"- Linha líder: {top_linha.split(': ', 1)[-1] if ': ' in top_linha else top_linha}\n"
        f"- Leitura gerencial: a operação {status_meta} e {status_ano1}."
    )


def _agent_oportunidade(df_mes_ref: pd.DataFrame, mes_ref: str, ano_ref: int) -> str:
    linhas = [f"Oportunidades comerciais do mês {mes_ref}/{ano_ref}:"]
    if "CLIENTE" in df_mes_ref.columns:
        linhas.append("\nClientes com maior peso no mês:\n" + _agent_top(df_mes_ref, "CLIENTE", "Cliente", 5))
    if "MARCA" in df_mes_ref.columns:
        linhas.append("\nMarcas com maior tração:\n" + _agent_top(df_mes_ref, "MARCA", "Marca", 5))
    if "LINHA" in df_mes_ref.columns:
        linhas.append("\nLinhas com maior tração:\n" + _agent_top(df_mes_ref, "LINHA", "Linha", 5))
    linhas.append("\nLeitura: use os líderes acima para montar ações de reforço, combos comerciais e direcionamento da equipe de vendas.")
    return "\n".join(linhas)


def _agent_risco(df_mes_ref: pd.DataFrame, mes_ref: str, ano_ref: int) -> str:
    real, meta, falta_meta, pct_meta = _agent_meta_mes(df_mes_ref, mes_ref)
    prev, media, dias_uteis, dias_com_venda = _agent_previsao(df_mes_ref, mes_ref)
    _, ano1, falta_ano1, cresc = _agent_ano1_mes(df_mes_ref, mes_ref)
    riscos = [f"Alertas gerenciais do mês {mes_ref}/{ano_ref}:"]
    if meta and prev < meta:
        riscos.append(f"- Risco de não bater meta: previsão {format_brl(prev)} x meta {format_brl(meta)}. Diferença projetada: {format_brl(prev - meta)}.")
    if ano1 and prev < ano1:
        riscos.append(f"- Risco de fechar abaixo do Ano-1: previsão {format_brl(prev)} x Ano-1 {format_brl(ano1)}. Diferença projetada: {format_brl(prev - ano1)}.")
    if dias_com_venda <= 3:
        riscos.append("- Poucos dias com venda no mês para uma previsão estatisticamente confortável; acompanhe a média diária com cautela.")
    if len(riscos) == 1:
        riscos.append("- Não identifiquei alerta crítico com base em meta, previsão e Ano-1. Continue acompanhando ritmo diário, marcas, linhas e clientes líderes.")
    return "\n".join(riscos)



def _resolver_valor_coluna(base_ref: pd.DataFrame, coluna: str, valor) -> tuple[pd.Series, str]:
    if coluna not in base_ref.columns or valor in [None, ""]:
        return pd.Series([True] * len(base_ref), index=base_ref.index), ""
    alvo = _norm_match(valor)
    serie_norm = base_ref[coluna].fillna("").astype(str).map(_norm_match)
    mask = serie_norm == alvo
    if not mask.any() and alvo:
        mask = serie_norm.str.contains(re.escape(alvo), na=False)
    return mask, str(valor)


def _base_por_tempo_e_filtros(base: pd.DataFrame, tempo: str, filtros: dict, df_hoje: pd.DataFrame, df_mes_ref: pd.DataFrame, df_periodo_agent: pd.DataFrame, hoje_base, ano_ref: int, mes_num_ref: int) -> tuple[pd.DataFrame, str, list[str]]:
    filtros = filtros or {}
    aplicados = []
    try:
        ano_f = int(filtros.get("ano")) if filtros.get("ano") not in [None, ""] else None
    except Exception:
        ano_f = None
    try:
        mes_f = int(filtros.get("mes")) if filtros.get("mes") not in [None, ""] else None
    except Exception:
        mes_f = None

    if ano_f or mes_f:
        calc = base.copy()
        ano_usado = ano_f or ano_ref
        calc = calc[calc["ANO"] == ano_usado].copy()
        aplicados.append(f"Ano={ano_usado}")
        if mes_f:
            calc = calc[calc["MES_NUM"] == mes_f].copy()
            aplicados.append(f"Mês={_mes_int_para_nome(mes_f)}/{ano_usado}")
        label = f"{_mes_int_para_nome(mes_f)}/{ano_usado}" if mes_f else f"ano {ano_usado}"
    else:
        calc = _agent_escolher_recorte(tempo, df_hoje, df_mes_ref, df_periodo_agent).copy()
        label = _agent_periodo_label(tempo, hoje_base, month_key_from_monthnum(mes_num_ref), ano_ref)

    for chave, coluna in {"marca":"MARCA", "linha":"LINHA", "segmento":"SEGMENTO", "cliente":"CLIENTE", "vendedor":"VENDEDOR"}.items():
        val = filtros.get(chave)
        if val not in [None, ""] and coluna in calc.columns:
            mask, label_val = _resolver_valor_coluna(calc, coluna, val)
            calc = calc[mask].copy()
            aplicados.append(f"{chave.capitalize()}={label_val}")

    produto = filtros.get("produto")
    if produto not in [None, ""]:
        cod_col, desc_col, _ = _agent_coluna_produto(calc)
        masks = []
        if desc_col:
            masks.append(_resolver_valor_coluna(calc, desc_col, produto)[0])
        if cod_col:
            masks.append(_resolver_valor_coluna(calc, cod_col, produto)[0])
        if masks:
            mask_final = masks[0]
            for m in masks[1:]:
                mask_final = mask_final | m
            calc = calc[mask_final].copy()
            aplicados.append(f"Produto={produto}")

    return calc, label, aplicados


def _contexto_filtros(aplicados: list[str]) -> str:
    return " | Filtros: " + ", ".join(aplicados) if aplicados else ""


def _agent_ano1_com_filtros(base: pd.DataFrame, filtros: dict, ano_ref: int) -> tuple[float, float, float | None]:
    filtros = dict(filtros or {})
    ano_atual_calc = int(filtros.get("ano") or ano_ref)
    atual = base[base["ANO"] == ano_atual_calc].copy()
    anterior = base[base["ANO"] == ANO_1].copy()
    if filtros.get("mes"):
        atual = atual[atual["MES_NUM"] == int(filtros["mes"])].copy()
        anterior = anterior[anterior["MES_NUM"] == int(filtros["mes"])].copy()
    for chave, coluna in {"marca":"MARCA", "linha":"LINHA", "segmento":"SEGMENTO", "cliente":"CLIENTE", "vendedor":"VENDEDOR"}.items():
        val = filtros.get(chave)
        if val not in [None, ""]:
            if coluna in atual.columns:
                atual = atual[_resolver_valor_coluna(atual, coluna, val)[0]].copy()
            if coluna in anterior.columns:
                anterior = anterior[_resolver_valor_coluna(anterior, coluna, val)[0]].copy()
    produto = filtros.get("produto")
    if produto not in [None, ""]:
        for qual in ["atual", "anterior"]:
            d = atual if qual == "atual" else anterior
            cod_col, desc_col, _ = _agent_coluna_produto(d)
            mask_final = None
            for col in [desc_col, cod_col]:
                if col:
                    m = _resolver_valor_coluna(d, col, produto)[0]
                    mask_final = m if mask_final is None else (mask_final | m)
            d = d[mask_final].copy() if mask_final is not None else d.iloc[0:0].copy()
            if qual == "atual":
                atual = d
            else:
                anterior = d
    real = _agent_total(atual)
    ano1 = _agent_total(anterior)
    cresc = ((real - ano1) / ano1 * 100) if ano1 else None
    return real, ano1, cresc


def _gerar_contexto_geral_chatbi(base: pd.DataFrame | None = None, recorte: pd.DataFrame | None = None, label: str = "") -> str:
    """
    Monta um contexto leve para o Gemini responder qualquer pergunta, inclusive perguntas gerais.
    Não manda a base inteira: só indicadores consolidados e dimensões disponíveis.
    """
    try:
        base_ref = base if isinstance(base, pd.DataFrame) and not base.empty else df
        rec_ref = recorte if isinstance(recorte, pd.DataFrame) and recorte is not None else base_ref
        if rec_ref is None or rec_ref.empty:
            rec_ref = base_ref

        partes = []
        partes.append(f"Dashboard: Única Atacadista / ChatBI Comercial.")
        if label:
            partes.append(f"Recorte atual: {label}.")
        partes.append(f"Vendedor filtrado: {vendedor_sel}.")
        partes.append(f"Linhas disponíveis no recorte: {len(rec_ref):,}.".replace(',', '.'))
        if 'VR_TOTAL' in rec_ref.columns:
            partes.append(f"Faturamento do recorte: {format_brl(float(rec_ref['VR_TOTAL'].sum()))}.")
        if 'CLIENTE' in rec_ref.columns:
            partes.append(f"Clientes ativos no recorte: {rec_ref['CLIENTE'].fillna('').astype(str).map(norm_text).replace('', pd.NA).dropna().nunique():,}.".replace(',', '.'))
        if 'MARCA' in rec_ref.columns and 'VR_TOTAL' in rec_ref.columns:
            top_marcas = (rec_ref.groupby('MARCA', as_index=False)['VR_TOTAL'].sum().sort_values('VR_TOTAL', ascending=False).head(5))
            partes.append('Top marcas no recorte: ' + '; '.join([f"{str(r['MARCA'])}: {format_brl(r['VR_TOTAL'])}" for _, r in top_marcas.iterrows()]) + '.')
        if 'CLIENTE' in rec_ref.columns and 'VR_TOTAL' in rec_ref.columns:
            top_clientes = (rec_ref.groupby('CLIENTE', as_index=False)['VR_TOTAL'].sum().sort_values('VR_TOTAL', ascending=False).head(5))
            partes.append('Top clientes no recorte: ' + '; '.join([f"{str(r['CLIENTE'])}: {format_brl(r['VR_TOTAL'])}" for _, r in top_clientes.iterrows()]) + '.')
        if 'LINHA' in rec_ref.columns and 'VR_TOTAL' in rec_ref.columns:
            top_linhas = (rec_ref.groupby('LINHA', as_index=False)['VR_TOTAL'].sum().sort_values('VR_TOTAL', ascending=False).head(5))
            partes.append('Top linhas no recorte: ' + '; '.join([f"{str(r['LINHA'])}: {format_brl(r['VR_TOTAL'])}" for _, r in top_linhas.iterrows()]) + '.')
        return '\n'.join(partes)
    except Exception as e:
        return f"Contexto geral indisponível: {e}"


def _responder_gemini_livre(pergunta: str, contexto_geral: str = "") -> str | None:
    """
    Resposta livre do Gemini. Usada para QUALQUER pergunta que não caia numa rota de cálculo.
    Não existe mais bloqueio por intenção: o Gemini sempre deve tentar responder.
    """
    if not _gemini_disponivel():
        return None
    api_key = _gemini_api_key()
    model_name = _gemini_model_name()
    prompt = f"""
Você é o ChatBI da Única Atacadista, um assistente de BI e consultor comercial conectado ao dashboard.

OBJETIVO:
Responder TUDO que o usuário perguntar, em português do Brasil, com linguagem clara, natural e consultiva.

REGRAS:
1. Se a pergunta for geral, responda normalmente.
2. Se a pergunta for sobre o funcionamento do ChatBI, explique como você interpreta dados: primeiro entende a pergunta, depois usa os dados/cálculos disponíveis e transforma em leitura gerencial.
3. Se a pergunta pedir números específicos e eles não estiverem no contexto abaixo, explique que precisa calcular pelo Pandas ou peça um recorte mais específico, mas NUNCA diga “não consegui classificar”.
4. Não invente números. Use apenas os números do contexto quando existirem.
5. Use tom de consultoria empresarial: explique o que o resultado significa, riscos, oportunidades e próximos passos quando fizer sentido.

CONTEXTO DISPONÍVEL DO DASHBOARD:
{contexto_geral}

PERGUNTA DO USUÁRIO:
{pergunta}
""".strip()
    try:
        if genai_new is not None:
            client = genai_new.Client(api_key=api_key)
            resp = client.models.generate_content(model=model_name, contents=prompt, config={"temperature": 0.35})
            return (getattr(resp, "text", "") or "").strip()
        if genai_legacy is not None:
            genai_legacy.configure(api_key=api_key)
            model = genai_legacy.GenerativeModel(model_name)
            resp = model.generate_content(prompt, generation_config={"temperature": 0.35})
            return (getattr(resp, "text", "") or "").strip()
    except Exception as e:
        st.session_state["ultimo_erro_gemini"] = str(e)
    return None

def _gerar_texto_consultivo_gemini(pergunta: str, dados_calculados: str, contexto_tecnico: str = "") -> str | None:
    """
    Usa o Gemini como camada final de consultoria.
    O Python/Pandas calcula os números; o Gemini interpreta e transforma em resposta executiva.
    """
    if not _gemini_disponivel():
        return None

    api_key = _gemini_api_key()
    model_name = _gemini_model_name()

    prompt = f"""
Você é o ChatBI da Única Atacadista, atuando como consultor empresarial sênior.

Sua função é transformar os dados calculados pelo Python/Pandas em uma resposta executiva, consultiva e clara para diretoria comercial.

REGRAS OBRIGATÓRIAS:
1. Não invente números, clientes, marcas, produtos, percentuais ou conclusões que não estejam sustentadas nos dados abaixo.
2. Preserve os valores calculados. Não recalcule mentalmente se não houver base suficiente.
3. Use linguagem natural, gerencial e objetiva.
4. Não responda apenas em lista crua; explique o que os números indicam.
5. Quando fizer sentido, destaque: principal resultado, concentração, risco, oportunidade e ação recomendada.
6. Se os dados forem insuficientes ou vazios, diga isso de forma clara e sugira uma pergunta mais específica.
7. Responda sempre em português do Brasil.
8. Não mencione que os dados vieram de prompt, código, função, API ou modelo.

PERGUNTA DO USUÁRIO:
{pergunta}

DADOS CALCULADOS PELO PYTHON/PANDAS:
{dados_calculados}

CONTEXTO TÉCNICO DO RECORTE:
{contexto_tecnico}

FORMATO DE RESPOSTA ESPERADO:
- Comece com a resposta direta.
- Depois traga uma leitura gerencial.
- Depois, quando aplicável, traga riscos/oportunidades.
- Feche com uma ação recomendada.
""".strip()

    try:
        if genai_new is not None:
            client = genai_new.Client(api_key=api_key)
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"temperature": 0.35},
            )
            return (getattr(resp, "text", "") or "").strip()
        if genai_legacy is not None:
            genai_legacy.configure(api_key=api_key)
            model = genai_legacy.GenerativeModel(model_name)
            resp = model.generate_content(prompt, generation_config={"temperature": 0.35})
            return (getattr(resp, "text", "") or "").strip()
    except Exception as e:
        st.session_state["ultimo_erro_gemini"] = str(e)
    return None


def _finalizar_resposta_chatbi(pergunta: str, dados_calculados: str, contexto: str, usar_gemini: bool = True) -> str:
    """
    Camada final do ChatBI: sempre tenta usar Gemini para redigir a resposta consultiva.
    Se a API falhar, entrega os dados calculados pelo Pandas como fallback.
    """
    contexto_gemini = contexto.replace("Motor:", "Motor de cálculo:")
    if usar_gemini:
        texto_ia = _gerar_texto_consultivo_gemini(pergunta, dados_calculados, contexto_gemini)
        if texto_ia:
            return f"{texto_ia}\n\n{contexto.replace('Motor: ' + contexto.split('Motor: ')[-1].rstrip('.'), 'Motor: Gemini + Pandas')}"
    return f"{dados_calculados}{contexto}\n\nObservação: o cálculo foi feito pelo Python/Pandas, mas o Gemini não conseguiu redigir a análise final neste momento."


def responder_agente_bi(pergunta: str) -> str:
    base = _agent_base(vendedor_sel)
    df_hoje, df_mes_ref, df_periodo_agent, hoje_base, ano_ref, mes_num_ref, mes_ref = _agent_recortes(base)
    if hoje_base is None:
        return "Não encontrei dados válidos na base."

    cls = _classificar_intencao(pergunta)
    intent = cls["intent"]
    entidade = cls.get("entidade")
    tempo = cls.get("tempo", "mes")
    filtros = cls.get("filtros", {}) if isinstance(cls.get("filtros", {}), dict) else {}
    recorte, label, filtros_aplicados = _base_por_tempo_e_filtros(
        base, tempo, filtros, df_hoje, df_mes_ref, df_periodo_agent, hoje_base, ano_ref, mes_num_ref
    )
    origem_cls = cls.get("origem", "Gemini/regras")
    contexto = f"\n\nInterpretação: {intent} | Recorte: {label}{_contexto_filtros(filtros_aplicados)} | Vendedor: {vendedor_sel} | Motor: Gemini + Pandas."

    dados_calculados = None

    # Perguntas gerais / não mapeadas: quem responde é SEMPRE o Gemini.
    # Não existe mais bloqueio do tipo "não consegui classificar".
    if intent == "nao_mapeada":
        contexto_geral = _gerar_contexto_geral_chatbi(base, recorte, label)
        resposta_livre = _responder_gemini_livre(pergunta, contexto_geral)
        if resposta_livre:
            contexto_livre = f"\n\nInterpretação: pergunta_livre | Recorte: {label}{_contexto_filtros(filtros_aplicados)} | Vendedor: {vendedor_sel} | Motor: Gemini."
            return f"{resposta_livre}{contexto_livre}"
        return (
            "O Gemini não conseguiu responder neste momento. Verifique a chave GEMINI_API_KEY, o modelo configurado e os logs do Streamlit."
            f"\n\nInterpretação: pergunta_livre | Recorte: {label}{_contexto_filtros(filtros_aplicados)} | Vendedor: {vendedor_sel} | Motor: Gemini indisponível."
        )

    # Comparação Ano-1 pode vir junto com filtros de marca/linha/produto/segmento.
    if cls.get("comparar_ano1") and intent not in ["ano1_falta", "ano1_comparativo", "ano1_projecao"]:
        real, ano1, cresc = _agent_ano1_com_filtros(base, filtros, ano_ref)
        dados_calculados = (
            f"Comparativo contra Ano-1:\n"
            f"Realizado: {format_brl(real)}\n"
            f"Ano-1 ({ANO_1}): {format_brl(ano1)}\n"
            f"Diferença: {format_brl(real - ano1)}\n"
            f"Crescimento: {fmt_pct(cresc)}"
        )
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)

    # Vendas totais
    if intent in ["venda_hoje", "venda_mes", "venda_periodo"]:
        dados_calculados = f"Venda no recorte {label}: {format_brl(_agent_total(recorte))}."
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)

    # Rankings por entidade
    if intent.startswith("cliente_") and not intent.startswith("clientes_quantidade"):
        dados_calculados = f"Ranking de clientes — {label}:\n{_agent_top(recorte, 'CLIENTE', 'Cliente', 10)}"
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)
    if intent.startswith("marca_"):
        dados_calculados = f"Ranking de marcas — {label}:\n{_agent_top(recorte, 'MARCA', 'Marca', 10)}"
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)
    if intent.startswith("linha_"):
        dados_calculados = f"Ranking de linhas — {label}:\n{_agent_top(recorte, 'LINHA', 'Linha', 10)}"
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)
    if intent.startswith("produto_"):
        dados_calculados = f"Ranking de produtos — {label}:\n{_agent_top_produtos(recorte, 10)}"
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)
    if intent.startswith("vendedor_"):
        dados_calculados = f"Ranking de vendedores — {label}:\n{_agent_top(recorte, 'VENDEDOR', 'Vendedor', 10)}"
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)

    # Quantidade de clientes
    if intent.startswith("clientes_quantidade"):
        dados_calculados = _agent_quantidade_clientes(recorte)
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)

    # Previsão
    if intent == "previsao_fechamento":
        prev, media, dias_uteis, dias_com_venda = _agent_previsao(df_mes_ref, mes_ref)
        real, meta, falta_meta, pct_meta = _agent_meta_mes(df_mes_ref, mes_ref)
        _, ano1, falta_ano1, cresc = _agent_ano1_mes(df_mes_ref, mes_ref)
        dados_calculados = (
            f"Previsão de fechamento de {mes_ref}/{ano_ref}: {format_brl(prev)}.\n"
            f"Realizado: {format_brl(real)}\n"
            f"Média diária: {format_brl(media)}\n"
            f"Dias com venda: {dias_com_venda}\n"
            f"Dias úteis considerados: {dias_uteis}\n"
            f"Meta: {format_brl(meta)}\n"
            f"Percentual projetado da meta: {fmt_pct((prev / meta * 100) if meta else None)}\n"
            f"Ano-1: {format_brl(ano1)}\n"
            f"Crescimento projetado contra Ano-1: {fmt_pct(((prev - ano1) / ano1 * 100) if ano1 else None)}"
        )
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)

    # Meta
    if intent == "meta_falta":
        real, meta, falta, pct = _agent_meta_mes(df_mes_ref, mes_ref)
        dados_calculados = (
            f"Meta de {mes_ref}/{ano_ref}: {format_brl(meta)}\n"
            f"Realizado: {format_brl(real)}\n"
            f"Falta para bater a meta: {format_brl(falta)}\n"
            f"Percentual atingido: {fmt_pct(pct)}"
        )
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)
    if intent == "meta_percentual":
        real, meta, falta, pct = _agent_meta_mes(df_mes_ref, mes_ref)
        dados_calculados = (
            f"Percentual da meta atingido em {mes_ref}/{ano_ref}: {fmt_pct(pct)}\n"
            f"Realizado: {format_brl(real)}\n"
            f"Meta: {format_brl(meta)}\n"
            f"Falta: {format_brl(falta)}"
        )
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)
    if intent == "meta_projecao":
        prev, media, dias_uteis, dias_com_venda = _agent_previsao(df_mes_ref, mes_ref)
        real, meta, falta, pct = _agent_meta_mes(df_mes_ref, mes_ref)
        status = "Pela previsão atual tende a bater a meta." if prev >= meta and meta else "Pela previsão atual ainda não bate a meta."
        dados_calculados = (
            f"{status}\n"
            f"Previsão: {format_brl(prev)}\n"
            f"Meta: {format_brl(meta)}\n"
            f"Diferença projetada: {format_brl(prev - meta)}\n"
            f"Realizado atual: {format_brl(real)}"
        )
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)
    if intent == "meta_dia":
        real, meta, falta, pct = _agent_meta_mes(df_mes_ref, mes_ref)
        prev, media, dias_uteis, dias_com_venda = _agent_previsao(df_mes_ref, mes_ref)
        dias_restantes_estimados = max(dias_uteis - dias_com_venda, 1)
        necessidade_dia = falta / dias_restantes_estimados if falta else 0.0
        dados_calculados = (
            f"Para bater a meta de {mes_ref}/{ano_ref}, falta {format_brl(falta)}.\n"
            f"Necessidade média estimada por dia útil restante: {format_brl(necessidade_dia)}\n"
            f"Realizado: {format_brl(real)}\n"
            f"Meta: {format_brl(meta)}\n"
            f"Dias úteis restantes estimados: {dias_restantes_estimados}"
        )
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)

    # Ano-1
    if intent == "ano1_falta":
        real, ano1, cresc = _agent_ano1_com_filtros(base, filtros, ano_ref)
        falta = max(ano1 - real, 0)
        dados_calculados = (
            f"Falta para superar o Ano-1: {format_brl(falta)}\n"
            f"Realizado: {format_brl(real)}\n"
            f"Ano-1 ({ANO_1}): {format_brl(ano1)}\n"
            f"Crescimento atual: {fmt_pct(cresc)}"
        )
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)
    if intent == "ano1_comparativo":
        real, ano1, cresc = _agent_ano1_com_filtros(base, filtros, ano_ref)
        dados_calculados = (
            f"Comparativo contra Ano-1:\n"
            f"Realizado: {format_brl(real)}\n"
            f"Ano-1 ({ANO_1}): {format_brl(ano1)}\n"
            f"Diferença: {format_brl(real - ano1)}\n"
            f"Crescimento: {fmt_pct(cresc)}"
        )
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)
    if intent == "ano1_projecao":
        prev, media, dias_uteis, dias_com_venda = _agent_previsao(df_mes_ref, mes_ref)
        real, ano1, falta, cresc = _agent_ano1_mes(df_mes_ref, mes_ref)
        status = "tende a superar o Ano-1" if prev >= ano1 and ano1 else "ainda tende a fechar abaixo do Ano-1"
        dados_calculados = (
            f"Pela previsão atual, {status}.\n"
            f"Previsão: {format_brl(prev)}\n"
            f"Ano-1 ({ANO_1}): {format_brl(ano1)}\n"
            f"Diferença projetada: {format_brl(prev - ano1)}\n"
            f"Realizado atual: {format_brl(real)}"
        )
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)

    # Margem e ticket
    if intent.startswith("margem"):
        dados_calculados = _agent_margem(recorte)
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)
    if intent.startswith("ticket"):
        dados_calculados = _agent_ticket_medio(recorte)
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)

    # Executivo
    if intent == "resumo_executivo":
        dados_calculados = _agent_resumo_executivo(base)
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)
    if intent == "oportunidade":
        dados_calculados = _agent_oportunidade(df_mes_ref, mes_ref, ano_ref)
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)
    if intent == "risco":
        dados_calculados = _agent_risco(df_mes_ref, mes_ref, ano_ref)
        return _finalizar_resposta_chatbi(pergunta, dados_calculados, contexto)

    # Qualquer rota não prevista também vai para o Gemini.
    contexto_geral = _gerar_contexto_geral_chatbi(base, recorte, label)
    resposta_livre = _responder_gemini_livre(pergunta, contexto_geral)
    if resposta_livre:
        contexto_livre = f"\n\nInterpretação: pergunta_livre | Recorte: {label}{_contexto_filtros(filtros_aplicados)} | Vendedor: {vendedor_sel} | Motor: Gemini."
        return f"{resposta_livre}{contexto_livre}"

    return (
        "O Gemini não conseguiu responder neste momento. Verifique a chave GEMINI_API_KEY, o modelo configurado e os logs do Streamlit."
        f"\n\nInterpretação: pergunta_livre | Recorte: {label}{_contexto_filtros(filtros_aplicados)} | Vendedor: {vendedor_sel} | Motor: Gemini indisponível."
    )


with st.container():
    if genai_new is None and genai_legacy is None:
        st.warning("Biblioteca do Gemini não encontrada. Adicione `google-genai` no requirements.txt.")
    elif not _gemini_api_key():
        st.warning("Chave do Gemini não configurada. No Streamlit Cloud, adicione `GEMINI_API_KEY` em Secrets. Sem essa chave, o ChatBI não consegue responder tudo via Gemini.")
    else:
        st.success(f"Gemini configurado. Modelo ativo: `{_gemini_model_name()}`. O ChatBI responderá todas as perguntas via Gemini; quando necessário, usará Pandas para calcular os dados antes da resposta consultiva.")
        if "ultimo_erro_gemini" in st.session_state:
            with st.expander("Último erro do Gemini"):
                st.code(st.session_state["ultimo_erro_gemini"])

    exemplos_bi = [
        "Quanto vendeu hoje?",
        "Top clientes hoje",
        "Clientes do mês",
        "Top marcas hoje",
        "Marcas do mês",
        "Linhas hoje",
        "Linhas do mês",
        "Produtos do mês",
        "Top vendedores no período",
        "Quanto falta para bater a meta?",
        "Qual percentual da meta atingido?",
        "Quanto preciso vender por dia para bater a meta?",
        "Quanto falta para superar o ano passado?",
        "Comparativo contra Ano-1",
        "Previsão de fechamento",
        "Margem do mês",
        "Ticket médio hoje",
        "Quantos clientes compraram no mês?",
        "Faça uma análise gerencial",
        "Quais os riscos do mês?",
        "Quais as oportunidades?",
    ]

    with st.expander("Ver exemplos de perguntas por intenção"):
        st.write(" | ".join(exemplos_bi))
        st.caption("O Gemini interpreta a pergunta e envia uma intenção estruturada para o Python calcular com Pandas. Se a chave/API não estiver configurada, o app usa um fallback por regras.")

    pergunta_bi = st.chat_input("Pergunte ao ChatBI da Única com Gemini...")
    if "historico_agente_bi" not in st.session_state:
        st.session_state["historico_agente_bi"] = []

    if pergunta_bi:
        resposta_bi = responder_agente_bi(pergunta_bi)
        st.session_state["historico_agente_bi"].append({"role": "user", "content": pergunta_bi})
        st.session_state["historico_agente_bi"].append({"role": "assistant", "content": resposta_bi})

    if not st.session_state["historico_agente_bi"]:
        st.info("Digite uma pergunta no campo abaixo. Exemplo: Qual foi o top cliente do mês?")

    for msg in st.session_state["historico_agente_bi"][-10:]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])



# =========================
# EXPORTAÇÃO PDF — DASH COMPLETO
# =========================
st.divider()
st.markdown("## Exportar Dashboard Completo")
st.caption("O PDF completo consolida os indicadores, tabelas principais e os drills/tabelas atualmente selecionados no dashboard.")
try:
    pdf_dash = dashboard_to_pdf_bytes(
        st.session_state.get("pdf_sections", []),
        titulo="Dashboard Completo - Única",
        subtitulo=f"Período: {dt_ini} a {dt_fim} | Vendedor: {vendedor_sel} | Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    st.download_button(
        label="Baixar PDF - Dashboard Completo",
        data=pdf_dash,
        file_name="dashboard_completo_unica.pdf",
        mime="application/pdf",
        use_container_width=False,
    )
except Exception as e:
    st.warning(str(e))
