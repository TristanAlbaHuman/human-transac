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
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #dee2e6; }
    .agency-card { background-color: #fff; padding: 15px; border-radius: 10px; border-left: 5px solid #004a99; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); margin-bottom:10px; }
    </style>
""", unsafe_allow_html=True)

# --- FONCTIONS SUPPORTS ---
def clean_cols(df):
    df.columns = [str(c).strip().upper().replace(' ', '_') for c in df.columns]
    return df

def find_col(df, keywords):
    """Cherche une colonne par mots-clés et retourne le nom exact ou None."""
    for col in df.columns:
        if all(k.upper() in col.upper() for k in keywords): return col
    return None

def clean_addr(addr):
    if pd.isna(addr): return ""
    addr = str(addr).lower()
    addr = addr.replace("avenue", "av").replace("boulevard", "bd").replace("rue", "r").replace("impasse", "imp")
    return re.sub(r'[^a-z0-9]', '', addr)

# --- SIDEBAR LOADERS ---
st.sidebar.image("https://www.human-immobilier.fr/img/logo-human-immobilier.svg", width=150)
st.sidebar.title("📥 Chargement des Flux")

file_crm = st.sidebar.file_uploader("1. DATA CRM (Mandats, Evals)", type=['xlsx', 'csv'])
file_market = st.sidebar.file_uploader("2. DATA MARCHÉ (DPE, DVF)", type=['csv', 'xlsx'])

if file_crm:
    # Lecture CRM
    if file_crm.name.endswith('.xlsx'):
        xls = pd.ExcelFile(file_crm)
        sh_m = st.sidebar.selectbox("Feuille MANDATS", xls.sheet_names, index=0)
        sh_e = st.sidebar.selectbox("Feuille ÉVALUATIONS", xls.sheet_names, index=min(1, len(xls.sheet_names)-1))
        df_m = clean_cols(pd.read_excel(file_crm, sheet_name=sh_m))
        df_e = clean_cols(pd.read_excel(file_crm, sheet_name=sh_e))
    else:
        df_m = clean_cols(pd.read_csv(file_crm, sep=None, engine='python'))
        df_e = pd.DataFrame()

    # --- DÉTECTION DYNAMIQUE ---
    c_age = find_col(df_m, ["AGE", "MANDAT"])
    c_ag = find_col(df_m, ["AGENCE"])
    c_reg = find_col(df_m, ["REGION"]) or find_col(df_m, ["SECTEUR"])
    c_neg = find_col(df_m, ["NEGOCIATEUR"]) or find_col(df_m, ["AGENT"])
    c_suivi = find_col(df_m, ["SUIVI"]) or find_col(df_m, ["ACTION"])
    c_addr = find_col(df_m, ["ADRESSE"])
    c_nom = find_col(df_m, ["NOM"]) or find_col(df_m, ["DOSSIER"])

    # --- FILTRES ---
    st.sidebar.markdown("---")
    f_reg = st.sidebar.multiselect("Régions", df_m[c_reg].unique() if c_reg else [])
    if f_reg: df_m = df_m[df_m[c_reg].isin(f_reg)]
    f_ag = st.sidebar.multiselect("Agences", df_m[c_ag].unique() if c_ag else [])
    if f_ag: df_m = df_m[df_m[c_ag].isin(f_ag)]

    view = st.radio("SÉLECTIONNER LE NIVEAU DE PILOTAGE :", ["🌐 RÉSEAU", "🏢 AGENCE", "👤 AGENT"], horizontal=True)

    # ==========================================
    # VUE 1 : RÉSEAU (MACRO)
    # ==========================================
    if view == "🌐 RÉSEAU":
        st.title("📊 Performance Économique Réseau")
        col1, col2 = st.columns(2)
        col1.metric("Mandats Actifs", len(df_m))
        col2.metric("Évaluations", len(df_e))
        
        st.subheader("🚩 Retards de suivi par Région / Agence")
        if c_reg and c_suivi:
            retards = df_m[df_m[c_suivi].isna()]
            fig = px.bar(retards.groupby(c_reg).size().reset_index(name='N'), x=c_reg, y='N', color='N', title="Mandats sans suivi par Région")
            st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # VUE 2 : AGENCE (MANAGEMENT)
    # ==========================================
    elif view == "🏢 AGENCE":
        st.title("🏠 Pilotage de l'Agence")
        if c_ag: st.info(f"Analyse pour : {', '.join(df_m[c_ag].unique()[:5])}...")

        c_top1, c_top2 = st.columns(2)
        with c_top1:
            if c_neg and c_suivi:
                retard_neg = df_m[df_m[c_suivi].isna()].groupby(c_neg).size().reset_index(name='NB')
                st.plotly_chart(px.bar(retard_neg, x=c_neg, y='NB', title="Retards par Agent"), use_container_width=True)
        
        with c_top2:
            st.write("**🚨 Dossiers critiques (+180 jours)**")
            # Sécurité : on ne garde que les colonnes qui ne sont pas None
            cols_to_show = [c for c in [c_neg, c_ag, c_age, c_suivi] if c is not None]
            if c_age and cols_to_show:
                critiques = df_m[df_m[c_age] > 180].sort_values(c_age, ascending=False)
                st.dataframe(critiques[cols_to_show].head(20), use_container_width=True)

    # ==========================================
    # VUE 3 : AGENT (ACTION)
    # ==========================================
    else:
        st.title("👤 Assistant de Prospection")
        t_calls, t_radar = st.tabs(["📞 Mes Appels", "📡 Radar DVF x DPE"])
        
        with t_calls:
            for _, row in df_m.head(10).iterrows():
                with st.container():
                    st.markdown(f"""<div class="agency-card">
                        <b>👤 {row.get(c_nom, 'Client')}</b> | 📍 {row.get(c_addr, 'N/C')}<br>
                        ⏱️ Age : {row.get(c_age, 'N/A')}j | 💬 Suivi : {row.get(c_suivi, 'N/A')}</div>""", unsafe_allow_html=True)

        with t_radar:
            if file_market:
                df_market = pd.read_csv(file_market) if file_market.name.endswith('.csv') else pd.read_excel(file_market)
                df_market = clean_cols(df_market)
                c_addr_m = find_col(df_market, ["ADRESSE"]) or find_col(df_market, ["BAN"])
                
                if c_addr and c_addr_m:
                    df_m['KEY'] = df_m[c_addr].apply(clean_addr)
                    df_market['KEY'] = df_market[c_addr_m].apply(clean_addr)
                    matches = pd.merge(df_m, df_market, on='KEY', how='inner')
                    
                    st.success(f"🎯 {len(matches)} opportunités détectées")
                    # On affiche les données DVF pertinentes
                    dvf_cols = [c_addr, 'VALEUR_FONCIERE', 'DATE_MUTATION', 'TYPE_LOCAL', 'CLASSE_DPE']
                    actual_dvf = [c for c in dvf_cols if c in matches.columns]
                    st.dataframe(matches[actual_dvf], use_container_width=True)
            else:
                st.info("💡 Chargez le fichier DPE/DVF pour voir les signaux marché.")

else:
    st.info("👋 Bonjour ! Chargez votre fichier CRM (Excel) dans la barre latérale.")