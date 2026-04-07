import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="HUMAN COMMAND CENTER", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #dee2e6; }
    .agency-card { background-color: #fff; padding: 20px; border-radius: 10px; border-left: 5px solid #004a99; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .priority-text { color: #ff4b4b; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- FONCTIONS "CERVEAU" ---
def clean_cols(df):
    df.columns = [str(c).strip().upper().replace(' ', '_') for c in df.columns]
    return df

def find_col(df, keywords):
    for col in df.columns:
        if all(k.upper() in col.upper() for k in keywords): return col
    return None

def clean_addr(addr):
    if pd.isna(addr): return ""
    addr = str(addr).lower()
    addr = addr.replace("avenue", "av").replace("boulevard", "bd").replace("rue", "r").replace("impasse", "imp")
    return re.sub(r'[^a-z0-9]', '', addr)

# --- LOADERS SIDEBAR ---
st.sidebar.image("https://www.human-immobilier.fr/img/logo-human-immobilier.svg", width=150)
st.sidebar.title("📥 Chargement des Flux")

# Loader 1 : Interne
file_crm = st.sidebar.file_uploader("1. DATA CRM (Mandats, Evals)", type=['xlsx', 'csv'])
# Loader 2 : Externe
file_market = st.sidebar.file_uploader("2. DATA MARCHÉ (DPE, DVF)", type=['csv', 'xlsx'])

if file_crm:
    xls = pd.ExcelFile(file_crm)
    sh_m = st.sidebar.selectbox("Feuille MANDATS", xls.sheet_names, index=0)
    sh_e = st.sidebar.selectbox("Feuille ÉVALUATIONS", xls.sheet_names, index=min(1, len(xls.sheet_names)-1))
    
    df_m = clean_cols(pd.read_excel(file_crm, sheet_name=sh_m))
    df_e = clean_cols(pd.read_excel(file_crm, sheet_name=sh_e))

    # Colonnes clés
    c_age = find_col(df_m, ["AGE", "MANDAT"]) or find_col(df_m, ["DELAI"])
    c_ag = find_col(df_m, ["AGENCE"])
    c_reg = find_col(df_m, ["REGION"]) or find_col(df_m, ["SECTEUR"])
    c_neg = find_col(df_m, ["NEGOCIATEUR"]) or find_col(df_m, ["AGENT"])
    c_suivi = find_col(df_m, ["SUIVI"]) or find_col(df_m, ["ACTION"])
    c_addr = find_col(df_m, ["ADRESSE"])

    # --- FILTRES HIÉRARCHIQUES ---
    st.sidebar.markdown("---")
    f_reg = st.sidebar.multiselect("Régions", df_m[c_reg].unique() if c_reg else ["N/A"])
    if f_reg: df_m = df_m[df_m[c_reg].isin(f_reg)]
    
    f_ag = st.sidebar.multiselect("Agences", df_m[c_ag].unique() if c_ag else ["N/A"])
    if f_ag: df_m = df_m[df_m[c_ag].isin(f_ag)]

    # --- NAVIGATION PRINCIPALE ---
    view = st.radio("SÉLECTIONNER LE NIVEAU DE PILOTAGE :", ["🌐 RÉSEAU (Direction)", "🏢 AGENCE (Manager)", "👤 AGENT (Opérationnel)"], horizontal=True)

    # ==========================================
    # VUE 1 : RÉSEAU (MACRO)
    # ==========================================
    if view == "🌐 RÉSEAU (Direction)":
        st.title("📊 Performance Globale Réseau")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Mandats", len(df_m))
        col2.metric("Évals Actives", len(df_e))
        
        # Identification des retards par Région
        st.subheader("🚩 Zones à risque (Retards de suivi par Région)")
        if c_reg and c_suivi:
            delay_reg = df_m[df_m[c_suivi].isna()].groupby(c_reg).size().reset_index(name='NB_SANS_SUIVI')
            fig_reg = px.bar(delay_reg.sort_values('NB_SANS_SUIVI', ascending=False), x=c_reg, y='NB_SANS_SUIVI', 
                             color='NB_SANS_SUIVI', color_continuous_scale='Reds', title="Volume de Mandats 'Oubliés' par Région")
            st.plotly_chart(fig_reg, use_container_width=True)

    # ==========================================
    # VUE 2 : AGENCE (MÉZO)
    # ==========================================
    elif view == "🏢 AGENCE (Manager)":
        st.title("🏠 Pilotage de l'Agence")
        
        # Top Retards par Agent
        st.subheader("👨‍💼 Performance des Négociateurs")
        if c_neg and c_suivi:
            delay_neg = df_m[df_m[c_suivi].isna()].groupby(c_neg).size().reset_index(name='RETARDS')
            fig_neg = px.bar(delay_neg, x=c_neg, y='RETARDS', title="Nombre de dossiers sans suivi par agent", color_discrete_sequence=['#ff4b4b'])
            st.plotly_chart(fig_neg, use_container_width=True)

        st.subheader("📋 Dossiers critiques à débloquer")
        if c_age:
            critiques = df_m[df_m[c_age] > 180].sort_values(c_age, ascending=False)
            st.dataframe(critiques[[c_neg, c_ag, c_age, c_suivi]].head(20), use_container_width=True)

    # ==========================================
    # VUE 3 : AGENT (MICRO)
    # ==========================================
    else:
        st.title("👤 Mon Assistant d'Action")
        tab_work, tab_market = st.tabs(["📞 Mes Appels du jour", "🎯 Opportunités Marché (DVF x DPE)"])
        
        with tab_work:
            st.subheader("Mandats prioritaires")
            # Affichage en fiches
            for idx, row in df_m.head(5).iterrows():
                st.markdown(f"""
                <div class="agency-card">
                    <h4>{row.get('NOMDOSSIERVENDEUR', 'Client')}</h4>
                    <p><b>Ancienneté :</b> {row.get(c_age, 0)} jours | <b>Dernière action :</b> {row.get(c_suivi, 'Aucune')}</p>
                    <p>📍 {row.get(c_addr, 'Adresse N/C')}</p>
                </div>
                """, unsafe_allow_html=True)

        with tab_market:
            st.subheader("🔍 Matching DVF x DPE (Signaux de vente)")
            if file_market:
                # Lecture DPE/DVF
                df_market = pd.read_csv(file_market) if file_market.name.endswith('.csv') else pd.read_excel(file_market)
                df_market = clean_cols(df_market)
                
                # Matching
                c_addr_market = find_col(df_market, ["ADRESSE"]) or find_col(df_market, ["BAN"])
                if c_addr and c_addr_market:
                    df_m['KEY'] = df_m[c_addr].apply(clean_addr)
                    df_market['KEY'] = df_market[c_addr_market].apply(clean_addr)
                    matches = pd.merge(df_m, df_market, on='KEY', how='inner')
                    
                    st.success(f"🎯 {len(matches)} opportunités détectées !")
                    # Données pertinentes : Prix DVF, Date DPE, Consommation
                    cols_show = [c_addr, 'VALEUR_FONCIERE', 'DATE_MUTATION', 'CONSOMMATION_ENERGIE', 'CLASSE_DPE']
                    actual_cols = [c for c in cols_show if c in matches.columns]
                    st.dataframe(matches[actual_cols], use_container_width=True)
            else:
                st.info("💡 Chargez le fichier DPE/DVF pour voir qui vend sur votre secteur.")

else:
    st.info("👋 Bonjour ! Veuillez charger le fichier CRM pour activer la tour de contrôle.")