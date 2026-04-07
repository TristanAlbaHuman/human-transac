import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from datetime import datetime, timedelta

# --- CONFIGURATION UI ---
st.set_page_config(page_title="HUMAN RADAR - Pilotage Économique", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    .stTabs [aria-selected="true"] { background-color: #004a99 !important; color: white !important; font-weight: bold; }
    .main { background-color: #f8f9fb; }
    </style>
""", unsafe_allow_html=True)

# --- FONCTIONS "CERVEAU" ---

def robust_read(file):
    """Lecture multi-format avec détection automatique."""
    if file is None: return None
    name = file.name.lower()
    try:
        if name.endswith(('.xlsx', '.xls')):
            return pd.read_excel(file, sheet_name=None) # Retourne un dictionnaire de feuilles
        elif name.endswith('.csv'):
            df = pd.read_csv(file, sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip')
            return {"Unique": df}
        else:
            df = pd.read_csv(file, sep=None, engine='python', on_bad_lines='skip')
            return {"Unique": df}
    except Exception as e:
        st.error(f"Erreur de lecture sur {name}: {e}")
        return None

def clean_cols(df):
    """Uniformisation des noms de colonnes."""
    df.columns = [str(c).strip().upper().replace(' ', '_') for c in df.columns]
    return df

def find_col(df, keywords):
    """Trouve une colonne par mots-clés (ex: ['AGE', 'MANDAT'])."""
    for col in df.columns:
        if all(k.upper() in col.upper() for k in keywords): return col
    return None

def clean_addr(addr):
    """Clé de matching d'adresse pour le radar."""
    if pd.isna(addr): return ""
    addr = str(addr).lower()
    addr = addr.replace("avenue", "av").replace("boulevard", "bd").replace("rue", "r").replace("impasse", "imp")
    return re.sub(r'[^a-z0-9]', '', addr)

# --- SIDEBAR : LES 2 LOADERS ---
st.sidebar.image("https://www.human-immobilier.fr/img/logo-human-immobilier.svg", width=180)

st.sidebar.header("📥 1. DATA CRM (Interne)")
file_crm = st.sidebar.file_uploader("Mandats & Évaluations", type=['xlsx', 'csv', 'txt', 'tsv'])

st.sidebar.header("📥 2. DATA MARCHÉ (Externe)")
file_dpe = st.sidebar.file_uploader("Fichier DPE ADEME", type=['csv', 'xlsx'])

# --- TRAITEMENT DES DONNÉES ---
if file_crm:
    data_crm = robust_read(file_crm)
    sheets_crm = list(data_crm.keys())
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Mapping des flux")
    sh_m = st.sidebar.selectbox("Feuille MANDATS", sheets_crm, index=0)
    sh_e = st.sidebar.selectbox("Feuille ÉVALUATIONS", sheets_crm, index=min(1, len(sheets_crm)-1))
    
    df_m = clean_cols(data_crm[sh_m])
    df_e = clean_cols(data_crm[sh_e])

    # --- FILTRES FACETTES ---
    c_ag = find_col(df_m, ["AGENCE"])
    c_cp = find_col(df_m, ["CP"]) or find_col(df_m, ["CODE", "POSTAL"])
    c_bien = find_col(df_m, ["TYPE", "BIEN"])
    
    st.sidebar.markdown("---")
    f_ag = st.sidebar.multiselect("Filtrer Agences", df_m[c_ag].unique() if c_ag else [])
    f_cp = st.sidebar.multiselect("Filtrer Codes Postaux", df_m[c_cp].unique() if c_cp else [])
    
    if f_ag: df_m = df_m[df_m[c_ag].isin(f_ag)]
    if f_cp: df_m = df_m[df_m[c_cp].isin(f_cp)]

    # --- IHM PRINCIPALE ---
    st.title("🚀 HUMAN Performance Radar")
    view_type = st.radio("Mode de vue :", ["🌐 Réseau", "🏠 Agence", "👤 Agent"], horizontal=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🌪️ Funnel & Éco", "🏠 Mandats", "📊 Évaluations", "📡 Radar DPE"])

    # --- TAB 1 : FUNNEL & ÉCO ---
    with tab1:
        st.subheader("Entonnoir de Conversion Économique")
        nb_mandats = len(df_m)
        nb_evals = len(df_e)
        
        fig_funnel = go.Figure(go.Funnel(
            y = ["Évaluations (Prospects)", "Mandats en Stock"],
            x = [nb_evals, nb_mandats],
            textinfo = "value+percent initial",
            marker = {"color": ["#5ea1e6", "#004a99"]}
        ))
        st.plotly_chart(fig_funnel, use_container_width=True)
        
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Taux de Transformation", f"{round((nb_mandats/nb_evals)*100, 1)}%")
        col_m2.metric("Volume de Stock", nb_mandats)

    # --- TAB 2 : MANDATS ---
    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            c_type_m = find_col(df_m, ["TYPE", "MANDAT"]) or find_col(df_m, ["TYPOLOGIE"])
            if c_type_m:
                st.plotly_chart(px.pie(df_m, names=c_type_m, hole=0.4, title="Volume par Type de Mandat"), use_container_width=True)
        with c2:
            c_date_m = find_col(df_m, ["DATE", "SAISIE"]) or find_col(df_m, ["DATE", "CREATION"])
            if c_date_m:
                df_m[c_date_m] = pd.to_datetime(df_m[c_date_m])
                st.plotly_chart(px.histogram(df_m, x=c_date_m, title="Stock par Date de Création"), use_container_width=True)

        st.subheader("⚠️ Mandats sans suivi (Alertes)")
        c_suivi = find_col(df_m, ["SUIVI"]) or find_col(df_m, ["ACTION"])
        df_ns = df_m[df_m[c_suivi].isna()] if c_suivi else df_m
        st.plotly_chart(px.histogram(df_ns, x=c_date_m, color_discrete_sequence=['#ff4b4b'], title="Mandats sans action renseignée"), use_container_width=True)

        st.subheader("📋 Liste des Relances & Prévisions")
        df_m['DATE_PROBABLE_VENTE'] = df_m[c_date_m] + timedelta(days=90)
        st.dataframe(df_m.head(20), use_container_width=True)

    # --- TAB 3 : ÉVALUATIONS ---
    with tab3:
        st.subheader("Performance du flux Évaluations")
        ce1, ce2 = st.columns(2)
        c_date_e = find_col(df_e, ["DATE"])
        if c_date_e:
            df_e[c_date_e] = pd.to_datetime(df_e[c_date_e])
            ce1.plotly_chart(px.histogram(df_e, x=c_date_e, title="Flux d'Evaluations Créées"), use_container_width=True)
        
        c_statut = find_col(df_e, ["STATUT"]) or find_col(df_e, ["ACTIF"])
        if c_statut:
            ce2.plotly_chart(px.pie(df_e, names=c_statut, hole=0.4, title="Évals Actives vs Inactives"), use_container_width=True)

    # --- TAB 4 : RADAR DPE ---
    with tab4:
        st.header("📡 Radar : Match Mandats/Évals vs DPE Marché")
        if file_dpe:
            data_dpe = robust_read(file_dpe)
            df_dpe = clean_cols(list(data_dpe.values())[0])
            
            c_addr_m = find_col(df_m, ["ADRESSE"])
            c_addr_d = find_col(df_dpe, ["ADRESSE"]) or find_col(df_dpe, ["BAN"])
            
            if c_addr_m and c_addr_d:
                df_m['KEY'] = df_m[c_addr_m].apply(clean_addr)
                df_dpe['KEY'] = df_dpe[c_addr_d].apply(clean_addr)
                matches = pd.merge(df_m, df_dpe, on='KEY', how='inner')
                st.warning(f"🎯 {len(matches)} de vos mandats/évals ont un DPE récent émis sur le marché !")
                st.dataframe(matches, use_container_width=True)
        else:
            st.info("💡 Chargez un fichier DPE (Loader 2) pour comparer votre base avec les signaux de mise en vente réels.")

else:
    st.info("👋 Bienvenue. Veuillez charger vos données CRM (Loader 1) pour démarrer.")