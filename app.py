import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from datetime import datetime, timedelta
import io

# --- CONFIGURATION UI ---
st.set_page_config(page_title="HUMAN PERFORMANCE RADAR", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    .stTabs [aria-selected="true"] { background-color: #004a99 !important; color: white !important; font-weight: bold; }
    .main { background-color: #f4f7f9; }
    </style>
""", unsafe_allow_html=True)

# --- FONCTIONS "CERVEAU" (NORMALISATION & DÉTECTION) ---

def clean_address(addr):
    """Clé de matching unique pour comparer les adresses de différentes sources."""
    if pd.isna(addr): return ""
    addr = str(addr).lower()
    addr = addr.replace("avenue", "av").replace("boulevard", "bd").replace("rue", "r").replace("chemin", "ch")
    return re.sub(r'[^a-z0-9]', '', addr)

def smart_col_finder(df, keywords):
    """Cherche une colonne par mots-clés de manière flexible."""
    for col in df.columns:
        if all(k.upper() in str(col).upper() for k in keywords):
            return col
    return None

def robust_read(uploaded_file):
    """Lit CSV, TSV, TXT, XLS, XLSX avec détection de format et multi-feuilles."""
    name = uploaded_file.name.lower()
    if name.endswith(('.xlsx', '.xls')):
        xls = pd.ExcelFile(uploaded_file)
        return {sheet: xls.parse(sheet) for sheet in xls.sheet_names}
    elif name.endswith('.csv'):
        return {"Default": pd.read_csv(uploaded_file, sep=None, engine='python', on_bad_lines='skip')}
    elif name.endswith(('.tsv', '.txt')):
        return {"Default": pd.read_csv(uploaded_file, sep='\t' if name.endswith('.tsv') else None, engine='python')}
    return {}

# --- SIDEBAR : CHARGEMENT ---
st.sidebar.image("https://www.human-immobilier.fr/img/logo-human-immobilier.svg", width=200)
st.sidebar.title("📥 Chargement Data")

files = st.sidebar.file_uploader("Importer fichiers (Mandats, Evals, DPE...)", accept_multiple_files=True)

# --- INITIALISATION DES DONNÉES ---
df_m, df_e, df_d = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

if files:
    all_data = {}
    for f in files:
        all_data.update(robust_read(f))
    
    st.sidebar.success(f"Dictionnaires chargés : {list(all_data.keys())}")
    
    # Mapping des feuilles
    with st.sidebar.expander("⚙️ Mapping des Onglets", expanded=True):
        sh_m = st.selectbox("Feuille MANDATS", list(all_data.keys()), index=0)
        sh_e = st.selectbox("Feuille ÉVALUATIONS", list(all_data.keys()), index=min(1, len(all_data)-1))
        sh_d = st.selectbox("Feuille DPE (Optionnel)", ["Aucune"] + list(all_data.keys()))
    
    df_m = all_data[sh_m].copy()
    df_e = all_data[sh_e].copy()
    if sh_d != "Aucune":
        df_d = all_data[sh_d].copy()

    # Nettoyage Colonnes
    for df in [df_m, df_e, df_d]:
        if not df.empty: df.columns = [str(c).strip().upper() for c in df.columns]

    # --- FILTRES GLOBAUX (FACETTES) ---
    st.sidebar.header("🔍 Filtres")
    c_ag = smart_col_finder(df_m, ["AGENCE"])
    c_cp = smart_col_finder(df_m, ["CP"]) or smart_col_finder(df_m, ["CODE", "POSTAL"])
    c_bien = smart_col_finder(df_m, ["TYPE", "BIEN"])
    
    f_ag = st.sidebar.multiselect("Agence", df_m[c_ag].unique() if c_ag else [])
    f_cp = st.sidebar.multiselect("Code Postal / Dpt", df_m[c_cp].unique() if c_cp else [])
    
    if f_ag: df_m = df_m[df_m[c_ag].isin(f_ag)]
    if f_cp: df_m = df_m[df_m[c_cp].isin(f_cp)]

    # --- CALCULS MÉTIER ---
    c_date_m = smart_col_finder(df_m, ["DATE", "SAISIE"]) or smart_col_finder(df_m, ["DATE", "CREATION"])
    c_date_e = smart_col_finder(df_e, ["DATE"])
    c_suivi = smart_col_finder(df_m, ["SUIVI"]) or smart_col_finder(df_m, ["ACTION"])
    
    now = datetime.now()
    if c_date_m:
        df_m[c_date_m] = pd.to_datetime(df_m[c_date_m])
        df_m['DELAI_CONTACT'] = (now - df_m[c_date_m]).dt.days
        df_m['DATE_PROBABLE_VENTE'] = df_m[c_date_m] + timedelta(days=90)
    
    # --- IHM PRINCIPALE ---
    st.title("🚀 HUMAN PERFORMANCE DASHBOARD")
    
    view_type = st.radio("Niveau de vue :", ["🌐 Réseau", "🏠 Agence", "👤 Agent"], horizontal=True)

    tab1, tab2, tab3 = st.tabs(["🌪️ Funnel & Pilotage", "🏠 Mandats (Vendeurs)", "📊 Évaluations (Prospects)"])

    with tab1:
        st.header("Entonnoir de Conversion")
        col_f1, col_f2 = st.columns([2, 1])
        
        nb_dpe = len(df_d) if not df_d.empty else len(df_e) * 1.5
        fig_funnel = go.Figure(go.Funnel(
            y = ["Marché (DPE)", "Prospects (Évals)", "Stock (Mandats)"],
            x = [nb_dpe, len(df_e), len(df_m)],
            textinfo = "value+percent initial",
            marker = {"color": ["#D3D3D3", "#5ea1e6", "#004a99"]}
        ))
        col_f1.plotly_chart(fig_funnel, use_container_width=True)
        col_f2.metric("Taux de Capture", f"{round((len(df_m)/len(df_e))*100, 1)}%", "Evals -> Mandats")

    with tab2:
        st.subheader("Analyse Économique Mandats")
        c1, c2 = st.columns(2)
        with c1:
            c_type_m = smart_col_finder(df_m, ["TYPE", "MANDAT"]) or smart_col_finder(df_m, ["TYPOLOGIE"])
            if c_type_m:
                st.plotly_chart(px.pie(df_m, names=c_type_m, hole=0.4, title="Volume par Type"), use_container_width=True)
        with c2:
            st.plotly_chart(px.histogram(df_m, x=c_date_m, title="Stock par Date de Création"), use_container_width=True)
        
        st.subheader("⚠️ Alertes : Mandats sans suivi")
        df_sans_suivi = df_m[df_m[c_suivi].isna()] if c_suivi else df_m
        st.plotly_chart(px.histogram(df_sans_suivi, x=c_date_m, color_discrete_sequence=['red'], title="Stock sans actions"), use_container_width=True)
        
        st.subheader("📋 Liste de Pilotage (Relances)")
        cols_to_show = [c for c in [c_ag, c_type_m, c_date_m, 'DELAI_CONTACT', 'DATE_PROBABLE_VENTE'] if c is not None]
        st.dataframe(df_m[cols_to_show].sort_values('DELAI_CONTACT', ascending=False), use_container_width=True)

    with tab3:
        st.subheader("Performance Évaluations")
        ce1, ce2 = st.columns(2)
        c_actif = smart_col_finder(df_e, ["ACTIF"]) or smart_col_finder(df_e, ["STATUT"])
        if c_actif:
            ce1.plotly_chart(px.pie(df_e, names=c_actif, hole=0.4, title="Evals Actifs vs Inactifs"), use_container_width=True)
        ce2.plotly_chart(px.histogram(df_e, x=c_date_e, title="Flux d'Evaluations"), use_container_width=True)
        
        # Radar DPE (Matching)
        if not df_d.empty:
            st.subheader("📡 Radar : Match Mandats x DPE Externes")
            c_addr_m = smart_col_finder(df_m, ["ADRESSE"])
            c_addr_d = smart_col_finder(df_d, ["ADRESSE"]) or smart_col_finder(df_d, ["BAN"])
            if c_addr_m and c_addr_d:
                df_m['KEY'] = df_m[c_addr_m].apply(clean_address)
                df_d['KEY'] = df_d[c_addr_d].apply(clean_address)
                matches = pd.merge(df_m, df_d, on='KEY', how='inner')
                st.warning(f"⚠️ {len(matches)} de vos mandats ont un DPE récent émis par un tiers sur le marché !")
                st.dataframe(matches)

else:
    st.info("👋 Bienvenue. Veuillez charger vos fichiers Excel/CSV/TXT pour démarrer le pilotage.")