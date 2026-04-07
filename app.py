import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="HUMAN RADAR v6 | Funnels & Pilotage", layout="wide")

# --- STYLE ---
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    .sidebar .sidebar-content { background-image: linear-gradient(#2e7bcf,#2e7bcf); color: white; }
    </style>
""", unsafe_allow_html=True)

# --- FONCTIONS TECHNIQUES ---
def clean_cols(df):
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df

def find_col(df, keywords):
    for col in df.columns:
        if all(k.upper() in col.upper() for k in keywords): return col
    return None

def robust_read(file):
    if file.name.endswith('.csv'):
        return pd.read_csv(file, sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip')
    return pd.read_excel(file)

# --- SIDEBAR : IMPORTS & FILTRES DYNAMIQUES ---
st.sidebar.image("https://www.human-immobilier.fr/img/logo-human-immobilier.svg", width=180)
st.sidebar.title("🛠️ Paramètres")

main_file = st.sidebar.file_uploader("📂 Fichier CRM (Excel)", type=['xlsx'])
dpe_file = st.sidebar.file_uploader("⚡ Fichier DPE (CSV/Excel)", type=['csv', 'xlsx'])

if main_file:
    xls = pd.ExcelFile(main_file)
    sheets = xls.sheet_names
    sh_m = st.sidebar.selectbox("Onglet MANDATS", sheets, index=0)
    sh_e = st.sidebar.selectbox("Onglet ÉVALUATIONS", sheets, index=min(1, len(sheets)-1))

    # Chargement
    df_m = clean_cols(pd.read_excel(main_file, sheet_name=sh_m))
    df_e = clean_cols(pd.read_excel(main_file, sheet_name=sh_e))
    
    # Identification des colonnes pour les filtres
    c_agence = find_col(df_m, ["AGENCE"])
    c_cp = find_col(df_m, ["CODE", "POSTAL"]) or find_col(df_m, ["CP"])
    c_type_bien = find_col(df_m, ["TYPE", "BIEN"])
    c_type_mandat = find_col(df_m, ["TYPE", "MANDAT"]) or find_col(df_m, ["TYPOLOGIE"])
    c_age = find_col(df_m, ["AGE", "MANDAT"])

    # --- FILTRES GLOBAUX ---
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtres Croisés")
    
    f_agence = st.sidebar.multiselect("Agences", df_m[c_agence].unique() if c_agence else ["N/A"])
    f_type_bien = st.sidebar.multiselect("Type de bien", df_m[c_type_bien].unique() if c_type_bien else ["N/A"])
    
    # Application des filtres
    if f_agence:
        df_m = df_m[df_m[c_agence].isin(f_agence)]
        df_e = df_e[df_e[find_col(df_e, ["AGENCE"])].isin(f_agence)]
    if f_type_bien:
        df_m = df_m[df_m[c_type_bien].isin(f_type_bien)]

    # --- CALCUL DU FUNNEL ---
    # On définit les étapes du funnel vendeur
    # 1. Signaux (DPE) / 2. Prospects (Evaluations) / 3. Mandats (Contrats)
    nb_dpe = 0
    if dpe_file:
        df_dpe = robust_read(dpe_file)
        nb_dpe = len(df_dpe)
    
    nb_evals = len(df_e)
    nb_mandats = len(df_m)

    # --- DASHBOARD ---
    st.title("🚀 HUMAN Performance : Funnels & Pilotage")
    
    tab1, tab2, tab3 = st.tabs(["🌪️ Funnels de Conversion", "📡 Radar & Opportunités", "🏢 Analyse par Zone"])

    with tab1:
        st.subheader("Entonnoir de Transformation Vendeur")
        
        # Funnel Plotly
        fig_funnel = go.Figure(go.Funnel(
            y = ["Signaux Marché (DPE)", "Évaluations (Prospects)", "Mandats Actifs"],
            x = [nb_dpe if nb_dpe > 0 else nb_evals*1.5, nb_evals, nb_mandats],
            textinfo = "value+percent initial",
            marker = {"color": ["#e0e0e0", "#5ea1e6", "#004a99"]}
        ))
        st.plotly_chart(fig_funnel, use_container_width=True)
        
        st.info(f"💡 Votre taux de transformation global Évaluation -> Mandat est de **{round((nb_mandats/nb_evals)*100, 1)}%**")

    with tab2:
        st.header("🎯 Actions Prioritaires")
        # Ici on pourrait ajouter la logique de matching précédente
        st.write("Filtrez les données à gauche pour voir les opportunités par zone.")
        st.dataframe(df_m[[c_agence, c_type_bien, c_type_mandat, c_age]].head(20))

    with tab3:
        st.header("📊 Performance par Agence / CP")
        if c_agence and c_age:
            # Groupement pour voir où ça bloque
            perf_data = df_m.groupby(c_agence)[c_age].mean().reset_index()
            fig_bar = px.bar(perf_data, x=c_agence, y=c_age, color=c_age, 
                             title="Ancienneté moyenne du stock par Agence")
            st.plotly_chart(fig_bar, use_container_width=True)

else:
    st.info("👋 Chargez le fichier Excel pour générer les funnels.")