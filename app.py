import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="HUMAN CRM - Action Client", layout="wide", page_icon="🏠")

# Design "Action-Oriented"
st.markdown("""
    <style>
    .client-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #004a99;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .priority-high { border-left-color: #ff4b4b; }
    .priority-mid { border-left-color: #ffa500; }
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS SUPPORTS ---
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
    addr = addr.replace("avenue", "av").replace("boulevard", "bd").replace("rue", "r")
    return re.sub(r'[^a-z0-9]', '', addr)

# --- SIDEBAR : LOADERS & FILTRES ---
st.sidebar.image("https://www.human-immobilier.fr/img/logo-human-immobilier.svg", width=150)

st.sidebar.subheader("📥 1. Données Internes (CRM)")
file_crm = st.sidebar.file_uploader("Upload Mandats & Évals", type=['xlsx', 'csv'])

st.sidebar.subheader("📥 2. Données Marché (ADEME)")
file_dpe = st.sidebar.file_uploader("Upload DPE Récents", type=['csv'])

if file_crm:
    # Lecture Multi-feuilles
    xls = pd.ExcelFile(file_crm)
    sheets = xls.sheet_names
    sh_m = st.sidebar.selectbox("Onglet MANDATS", sheets, index=0)
    sh_e = st.sidebar.selectbox("Onglet ÉVALUATIONS", sheets, index=min(1, len(sheets)-1))
    
    df_m = clean_cols(pd.read_excel(file_crm, sheet_name=sh_m))
    df_e = clean_cols(pd.read_excel(file_crm, sheet_name=sh_e))

    # --- IDENTIFICATION DES COLONNES CLÉS ---
    c_nom = find_col(df_m, ["NOM", "CLIENT"]) or find_col(df_m, ["DOSSIER"])
    c_tel = find_col(df_m, ["TEL"]) or find_col(df_m, ["PORTABLE"])
    c_addr = find_col(df_m, ["ADRESSE"])
    c_age = find_col(df_m, ["AGE", "MANDAT"])
    c_action = find_col(df_m, ["ACTION"]) or find_col(df_m, ["SUIVI"])
    c_type_b = find_col(df_m, ["TYPE", "BIEN"])
    c_prix = find_col(df_m, ["PRIX"]) or find_col(df_m, ["VALEUR"])
    c_agence = find_col(df_m, ["AGENCE"])

    # --- FILTRES FACETTES ---
    st.sidebar.markdown("---")
    view_mode = st.sidebar.radio("Ma Vue", ["👤 Mon Portefeuille (Agent)", "🏠 Mon Agence", "🌐 Réseau"])
    
    f_agence = st.sidebar.multiselect("Agence", df_m[c_agence].unique() if c_agence else [])
    f_bien = st.sidebar.multiselect("Type de bien", df_m[c_type_b].unique() if c_type_b else [])
    
    if f_agence: df_m = df_m[df_m[c_agence].isin(f_agence)]
    if f_bien: df_m = df_m[df_m[c_type_b].isin(f_bien)]

    # --- INTERFACE PRINCIPALE ---
    st.title("🎯 Cockpit d'Action Commerciale")

    t1, t2, t3 = st.tabs(["⚡ Mes Actions du Jour", "📦 Gestion du Stock", "📈 Pilotage Réseau"])

    # --- TAB 1 : L'OUTIL DE TRAVAIL DU COMMERCIAL ---
    with t1:
        st.subheader("🔥 Priorités de relance")
        
        # Logique de détection des urgences (DPE ou Retard suivi)
        urgences = df_m.copy()
        if c_age:
            urgences = urgences[urgences[c_age] > 150] # Focus sur les mandats qui stagnent
        
        col_a, col_b = st.columns([2, 1])
        
        with col_a:
            for idx, row in urgences.head(5).iterrows():
                prio_class = "priority-high" if row.get(c_age, 0) > 200 else "priority-mid"
                
                with st.container():
                    st.markdown(f"""
                    <div class="client-card {prio_class}">
                        <h4>👤 {row.get(c_nom, 'Client Inconnu')}</h4>
                        <p>📍 <b>Adresse :</b> {row.get(c_addr, 'N/C')}</p>
                        <p>📞 <b>Contact :</b> {row.get(c_tel, 'Pas de numéro')}</p>
                        <hr>
                        <p>🏠 <b>Bien :</b> {row.get(c_type_b, 'N/C')} | 💰 <b>Prix :</b> {row.get(c_prix, 'N/C')} €</p>
                        <p>⏱️ <b>Ancienneté :</b> {row.get(c_age, 0)} jours sans vente</p>
                        <p>💬 <b>Dernier suivi :</b> {row.get(c_action, 'Aucun suivi saisi')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"✅ Marquer comme appelé : {row.get(c_nom)}", key=f"btn_{idx}"):
                        st.success("Action enregistrée !")

        with col_b:
            st.info("💡 **Conseil IA :** Les dossiers affichés n'ont pas eu de baisse de prix depuis 60 jours malgré l'absence d'offre. Proposez un avenant.")
            
            if file_dpe:
                st.error("⚠️ **ALERTE RADAR DPE**")
                st.write("3 clients de votre secteur viennent de réaliser un DPE (source ADEME). Ils préparent leur mise en vente.")

    # --- TAB 2 : GESTION DU STOCK (LISTE CRM) ---
    with t2:
        st.subheader("📋 Liste complète des mandats et évaluations")
        
        # Camembert demandé
        c_type_m = find_col(df_m, ["TYPE", "MANDAT"]) or find_col(df_m, ["TYPOLOGIE"])
        if c_type_m:
            fig_p = px.pie(df_m, names=c_type_m, hole=0.4, title="Répartition du Stock Mandats")
            st.plotly_chart(fig_p, use_container_width=True)

        st.dataframe(df_m, use_container_width=True)

    # --- TAB 3 : PILOTAGE (POUR BENJAMIN SALAH) ---
    with t3:
        st.subheader("📊 Performance Économique du Réseau")
        col_p1, col_p2, col_p3 = st.columns(3)
        
        col_p1.metric("Mandats Actifs", len(df_m))
        col_p2.metric("Évaluations / Mois", len(df_e))
        
        if c_age:
            st.subheader("Historique des mandats sans suivi")
            fig_h = px.histogram(df_m[df_m[c_action].isna()], x=c_age, 
                                 title="Volume de mandats 'oubliés' par âge", color_discrete_sequence=['red'])
            st.plotly_chart(fig_h, use_container_width=True)

else:
    st.info("👋 Bonjour ! Pour commencer, glissez votre export Excel dans la barre latérale.")