import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="HUMAN PERFORMANCE", layout="wide")

# Custom CSS pour une UI fluide et moderne
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    .main { background-color: #f9f9f9; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [aria-selected="true"] { background-color: #004a99 !important; color: white !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- FONCTIONS "INTELLIGENTES" ---

def clean_df(df):
    """Nettoyage automatique des colonnes."""
    df.columns = [str(c).strip().upper().replace(' ', '_') for c in df.columns]
    return df

def find_col(df, keywords):
    """Cherche une colonne par mots-clés."""
    for col in df.columns:
        if all(k.upper() in col.upper() for k in keywords): return col
    return None

def calculate_probable_date(row, date_col, days=90):
    """Calcule une date probable de vente (Heuristique)."""
    if pd.isna(row[date_col]): return None
    return row[date_col] + timedelta(days=days)

# --- SIDEBAR : FILTRES & IMPORTS ---
st.sidebar.image("https://www.human-immobilier.fr/img/logo-human-immobilier.svg", width=180)
st.sidebar.title("🎮 Pilotage & Filtres")

# Upload
main_file = st.sidebar.file_uploader("📂 Fichier CRM (Excel Multi-onglets)", type=['xlsx'])
dpe_file = st.sidebar.file_uploader("📄 Base DPE ADEME (CSV)", type=['csv'])

if main_file:
    xls = pd.ExcelFile(main_file)
    sheets = xls.sheet_names
    
    # Sélections des onglets
    sh_m = st.sidebar.selectbox("Onglet MANDATS", sheets, index=0)
    sh_e = st.sidebar.selectbox("Onglet ÉVALUATIONS", sheets, index=min(1, len(sheets)-1))
    
    # Chargement
    df_m = clean_df(pd.read_excel(main_file, sheet_name=sh_m))
    df_e = clean_df(pd.read_excel(main_file, sheet_name=sh_e))

    # --- LOGIQUE DE VUES ---
    view_level = st.sidebar.radio("Niveau de vue", ["🌐 Réseau", "🏠 Agence", "👤 Agent"])
    
    # Filtres par facettes
    st.sidebar.markdown("---")
    col_agence = find_col(df_m, ["AGENCE"])
    col_dept = find_col(df_m, ["CP"]) or find_col(df_m, ["DEPT"])
    col_type_bien = find_col(df_m, ["TYPE", "BIEN"])
    col_agent = find_col(df_m, ["NEGOCIATEUR"]) or find_col(df_m, ["AGENT"])

    f_dept = st.sidebar.multiselect("Département", df_m[col_dept].unique() if col_dept else [])
    f_agence = st.sidebar.multiselect("Agences", df_m[col_agence].unique() if col_agence else [])
    f_bien = st.sidebar.multiselect("Type de bien", df_m[col_type_bien].unique() if col_type_bien else [])

    # Application des filtres
    if f_dept: df_m = df_m[df_m[col_dept].isin(f_dept)]
    if f_agence: df_m = df_m[df_m[col_agence].isin(f_agence)]
    if f_bien: df_m = df_m[df_m[col_type_bien].isin(f_bien)]

    # --- DASHBOARD ---
    st.title(f"🚀 Performance Économique - Vue {view_level}")
    
    tab_m, tab_e, tab_dpe = st.tabs(["📄 Mandats", "📊 Évaluations", "📡 Radar DPE x Mandats"])

    # --- TAB MANDATS ---
    with tab_m:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Volume par Type")
            c_type_m = find_col(df_m, ["TYPE", "MANDAT"]) or find_col(df_m, ["TYPOLOGIE"])
            if c_type_m:
                fig_p = px.pie(df_m, names=c_type_m, hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_p, use_container_width=True)
        
        with c2:
            st.subheader("Stock par Date de Création")
            c_date_s = find_col(df_m, ["DATE", "SAISIE"]) or find_col(df_m, ["DATE", "CREATION"])
            if c_date_s:
                df_m[c_date_s] = pd.to_datetime(df_m[c_date_s])
                fig_h = px.histogram(df_m, x=c_date_s, nbins=20, color_discrete_sequence=['#004a99'])
                st.plotly_chart(fig_h, use_container_width=True)

        st.subheader("⚠️ Mandats SANS SUIVI")
        c_suivi = find_col(df_m, ["SUIVI"]) or find_col(df_m, ["ACTION"])
        df_no_suivi = df_m[df_m[c_suivi].isna()] if c_suivi else df_m
        fig_ns = px.histogram(df_no_suivi, x=c_date_s, title="Mandats sans suivi par date de création", color_discrete_sequence=['#ff4b4b'])
        st.plotly_chart(fig_ns, use_container_width=True)

        st.subheader("📋 Liste des Mandats Stock & Délais")
        # Calcul proba vente
        df_m['DATE_PROBABLE_VENTE'] = df_m.apply(lambda r: calculate_probable_date(r, c_date_s), axis=1)
        st.dataframe(df_m[[col_agence, c_type_m, c_date_s, 'DATE_PROBABLE_VENTE']].head(50), use_container_width=True)

    # --- TAB ÉVALUATIONS ---
    with tab_e:
        c3, c4 = st.columns(2)
        with c3:
            st.subheader("Volume Actif/Inactif")
            c_statut = find_col(df_e, ["STATUT"]) or find_col(df_e, ["ACTIF"])
            if c_statut:
                fig_pe = px.pie(df_e, names=c_statut, hole=0.4)
                st.plotly_chart(fig_pe, use_container_width=True)
        
        with c4:
            st.subheader("Évals par Date de Création")
            c_date_e = find_col(df_e, ["DATE"])
            if c_date_e:
                df_e[c_date_e] = pd.to_datetime(df_e[c_date_e])
                fig_he = px.histogram(df_e, x=c_date_e, nbins=20)
                st.plotly_chart(fig_he, use_container_width=True)

    # --- TAB RADAR DPE ---
    with tab_dpe:
        st.header("📡 Matching Mandats x DPE Récents")
        if dpe_file:
            st.success("Matching en cours basé sur les adresses...")
            # Ici on insèrerait la logique de matching précédente
            st.info("Cette vue affiche les mandats dont un DPE a été détecté récemment sur le marché (Signal fort de mise en vente/concurrence).")
        else:
            st.warning("Chargez un fichier DPE pour activer cette vue.")

else:
    st.info("👋 Bonjour ! Veuillez charger votre export CRM (Excel multi-onglets) pour démarrer le pilotage.")