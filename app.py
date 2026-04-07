import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="HUMAN RADAR | Pilotage & Performance", layout="wide")

# Style Corporate
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    .stTabs [aria-selected="true"] { background-color: #004a99 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- FONCTIONS DE NETTOYAGE ---

def clean_cols(df):
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df

def find_smart_col(df, keywords):
    for col in df.columns:
        if all(k.upper() in col.upper() for k in keywords):
            return col
    return None

def clean_addr(addr):
    if pd.isna(addr): return ""
    addr = str(addr).lower()
    replacements = {"avenue": "av", "boulevard": "bd", "rue": "r", "impasse": "imp", "chemin": "ch"}
    for k, v in replacements.items():
        addr = addr.replace(k, v)
    return re.sub(r'[^a-z0-9]', '', addr)

# --- LOGIQUE D'IMPORTATION SÉCURISÉE ---

def robust_read_csv(file):
    """Lit un CSV en détectant automatiquement le séparateur et l'encodage."""
    try:
        # On tente de lire les premières lignes pour détecter le format
        return pd.read_csv(file, sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip')
    except:
        # Si échec (souvent dû à l'encodage Windows), on tente le latin-1
        file.seek(0)
        return pd.read_csv(file, sep=None, engine='python', encoding='latin-1', on_bad_lines='skip')

# --- SIDEBAR ---
st.sidebar.image("https://www.human-immobilier.fr/img/logo-human-immobilier.svg", width=180)
st.sidebar.title("🏢 Pilotage Data")

main_file = st.sidebar.file_uploader("📂 Fichier CRM (Excel multi-onglets)", type=['xlsx'])
dpe_file = st.sidebar.file_uploader("⚡ Base DPE ADEME (CSV)", type=['csv'])

if main_file:
    xls = pd.ExcelFile(main_file)
    sheets = xls.sheet_names
    st.sidebar.markdown("---")
    sh_m = st.sidebar.selectbox("Onglet MANDATS", sheets, index=0)
    sh_e = st.sidebar.selectbox("Onglet ÉVALUATIONS", sheets, index=min(1, len(sheets)-1))

    df_m = clean_cols(pd.read_excel(main_file, sheet_name=sh_m))
    df_e = clean_cols(pd.read_excel(main_file, sheet_name=sh_e))

    # Détection des colonnes
    c_age = find_smart_col(df_m, ["AGE", "MANDAT"])
    c_typo = find_smart_col(df_m, ["TYPOLOGIE"])
    c_agence = find_smart_col(df_m, ["AGENCE"])
    c_addr_e = find_smart_col(df_e, ["ADRESSE"])

    # --- MATCHING RADAR ---
    radar_matches = pd.DataFrame()
    if dpe_file:
        df_dpe = robust_read_csv(dpe_file) # Utilisation de la fonction robuste
        df_dpe = clean_cols(df_dpe)
        c_addr_d = find_smart_col(df_dpe, ["ADRESSE"]) or find_smart_col(df_dpe, ["BAN"])
        
        if c_addr_e and c_addr_d:
            df_e['MATCH_KEY'] = df_e[c_addr_e].apply(clean_addr)
            df_dpe['MATCH_KEY'] = df_dpe[c_addr_d].apply(clean_addr)
            radar_matches = pd.merge(df_e, df_dpe, on='MATCH_KEY', how='inner')

    # --- DASHBOARD ---
    st.title("🚀 HUMAN Radar | Prototype Performance")
    
    t1, t2, t3 = st.tabs(["📈 Pilotage", "📡 Radar DPE", "🏢 Zone"])

    with t1:
        col1, col2, col3 = st.columns(3)
        col1.metric("Stock Mandats", len(df_m))
        col2.metric("Évaluations", len(df_e))
        col3.metric("Match DPE", len(radar_matches))

        if c_age:
            fig = px.histogram(df_m, x=c_age, color=c_typo, barmode="group",
                               title="Analyse de l'Ancienneté du Stock",
                               labels={c_age: "Jours de Mandat"})
            st.plotly_chart(fig, use_container_width=True)

    with t2:
        st.header("🎯 Opportunités Radar (Match ADEME)")
        if not radar_matches.empty:
            st.success(f"Détecté : {len(radar_matches)} prospects avec un DPE récent !")
            st.dataframe(radar_matches, use_container_width=True)
        else:
            st.info("Aucun match trouvé ou attente du fichier DPE.")

    with t3:
        st.header("🏢 Benchmark Agences")
        if c_agence and c_age:
            perf = df_m.groupby(c_agence)[c_age].mean().reset_index().sort_values(c_age)
            fig_bar = px.bar(perf, x=c_agence, y=c_age, color=c_age, color_continuous_scale='RdYlGn_r')
            st.plotly_chart(fig_bar, use_container_width=True)

else:
    st.info("👋 Chargez le fichier Excel pour démarrer.")