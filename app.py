import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from datetime import datetime

# --- CONFIGURATION & STYLE ---
st.set_page_config(page_title="HUMAN Radar | Pilotage Performance", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    div.stButton > button:first-child { background-color: #004a99; color: white; border-radius: 8px; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS TECHNIQUES (LE COEUR DU RÉACTEUR) ---

def clean_address(addr):
    """Nettoyage pour le matching intelligent entre fichiers"""
    if pd.isna(addr): return ""
    addr = str(addr).lower()
    addr = addr.replace("avenue", "av").replace("boulevard", "bd").replace("rue", "r").replace("impasse", "imp")
    addr = re.sub(r'[^a-z0-9]', '', addr)
    return addr

def analyze_friction(texte):
    """Analyse sémantique simplifiée des comptes-rendus de visite"""
    texte = str(texte).lower()
    points = []
    if any(w in texte for w in ["prix", "cher", "budget"]): points.append("💰 Prix")
    if any(w in texte for w in ["bruit", "route", "nuisance"]): points.append("🔊 Nuisance")
    if any(w in texte for w in ["travaux", "deco", "rafraichissement"]): points.append("🛠️ Travaux")
    if any(w in texte for w in ["petit", "surface", "etroit"]): points.append("📐 Agencement")
    return points if points else ["✅ Positif"]

# --- SIDEBAR : IMPORT & FILTRES ---
st.sidebar.image("https://www.human-immobilier.fr/img/logo-human-immobilier.svg", width=180)
st.sidebar.title("📥 Inputs Data")

upload_mandats = st.sidebar.file_uploader("Mandats (sans SSP)", type=['csv', 'xlsx'])
upload_evals = st.sidebar.file_uploader("Évaluations Full", type=['csv', 'xlsx'])
upload_dpe = st.sidebar.file_uploader("Base DPE (ADEME)", type=['csv', 'xlsx'])

st.sidebar.markdown("---")
selected_agences = st.sidebar.multiselect("Filtrer Agences", ["Amboise", "Aubergenville", "Audierne", "Bordeaux", "Toutes"])

# --- LOGIQUE DE CHARGEMENT ---
@st.cache_data
def load_and_process(file):
    if file.name.endswith('.csv'): return pd.read_csv(file)
    return pd.read_excel(file)

if upload_mandats and upload_evals and upload_dpe:
    df_m = load_and_process(upload_mandats)
    df_e = load_and_process(upload_evals)
    df_d = load_and_process(upload_dpe)

    # Normalisation des colonnes (Gestion des espaces et casses)
    for df in [df_m, df_e, df_d]:
        df.columns = [c.strip() for c in df.columns]

    # --- CALCULS RADAR (MATCHING) ---
    df_e['addr_key'] = df_e['BienAdresse_Adresse'].apply(clean_address)
    df_d['addr_key'] = df_d['adresse_ban'].apply(clean_address)
    radar_matches = pd.merge(df_e, df_d, on='addr_key', how='inner')

    # --- INTERFACE PRINCIPALE ---
    st.title("🚀 HUMAN Radar : Pilotage & Opportunités")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Pilotage", "📡 Radar (Opportunités)", "⚠️ Risques", "🏢 Direction de Zone"])

    # --- TAB 1 : PILOTAGE ---
    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Mandats Actifs", len(df_m))
        c2.metric("Hot Leads DPE", len(radar_matches), "🔥")
        c3.metric("Stock Segment 2/3", len(df_m[df_m['AGE MANDAT'] > 180]))
        c4.metric("Taux Transfo (Est.)", "24%")

        st.subheader("Structure du stock par ancienneté")
        fig_stock = px.histogram(df_m, x="AGE MANDAT", color="Typologie", barmode="group",
                                 color_discrete_sequence=px.colors.qualitative.Prism)
        st.plotly_chart(fig_stock, use_container_width=True)

    # --- TAB 2 : RADAR (SMART MATCHING) ---
    with tab2:
        st.header("🎯 Signaux Faibles : Évaluations avec DPE récent")
        st.info("Ces prospects ont fait une estimation chez nous ET un DPE récemment. Relance prioritaire.")
        
        if not radar_matches.empty:
            display_radar = radar_matches[['txtAgence', 'NomDossierEstimation', 'BienAdresse_Adresse', 'date_etablissement_dpe']].copy()
            display_radar['Action'] = "📞 Rappeler pour Mise en Vente"
            st.dataframe(display_radar, use_container_width=True)
            
            # Simulateur de SMS
            st.markdown("---")
            st.subheader("💬 Générateur de Relance")
            selected_prospect = st.selectbox("Générer message pour :", display_radar['NomDossierEstimation'])
            st.code(f"Bonjour M./Mme {selected_prospect}, nous avons noté une actualisation de votre dossier technique. Souhaitez-vous une mise à jour de notre estimation de janvier ? Cordialement, HUMAN Immobilier.")
        else:
            st.warning("Aucun match détecté entre vos évaluations et les derniers DPE.")

    # --- TAB 3 : RISQUES (ANALYSE SÉMANTIQUE) ---
    with tab3:
        st.header("⚠️ Défense du Stock & Analyse de Friction")
        
        col_r1, col_r2 = st.columns([2, 1])
        
        with col_r1:
            st.write("**Mandats critiques (Age > 200j sans action)**")
            critiques = df_m[df_m['AGE MANDAT'] > 200].copy()
            st.dataframe(critiques[['NomDossierVendeur', 'AGE MANDAT', 'Actions à prévoir']], use_container_width=True)

        with col_r2:
            st.write("**Analyse des Freins (IA)**")
            # On simule l'analyse sur la colonne 'Actions à prévoir' ou commentaires
            df_m['Frictions'] = df_m['Actions à prévoir'].apply(analyze_friction)
            all_f = [item for sublist in df_m['Frictions'] for item in sublist if item != "✅ Positif"]
            if all_f:
                f_counts = pd.Series(all_f).value_counts().reset_index()
                fig_p = px.pie(f_counts, values='count', names='index', hole=.4, title="Motifs de blocage")
                st.plotly_chart(fig_p, use_container_width=True)

    # --- TAB 4 : DIRECTION DE ZONE (BENCHMARK) ---
    with tab4:
        st.header("🏢 Comparaison Performance Agences")
        ag_list = df_m['txtAgence'].unique()
        c_z1, c_z2 = st.columns(2)
        ag1 = c_z1.selectbox("Agence Référence", ag_list, index=0)
        ag2 = c_z2.selectbox("Agence Comparée", ag_list, index=1)

        # Radar chart simulation
        categories = ['Vitesse Vente', 'Qualité Mandat', 'Taux Exclu', 'Réactivité CRM']
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(r=[80, 65, 70, 90], theta=categories, fill='toself', name=ag1))
        fig_radar.add_trace(go.Scatterpolar(r=[60, 85, 45, 70], theta=categories, fill='toself', name=ag2))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
        st.plotly_chart(fig_radar, use_container_width=True)

else:
    # --- PAGE D'ACCUEIL SI VIDE ---
    st.title("👋 Bienvenue dans HUMAN Radar")
    st.info("Veuillez uploader les 3 fichiers requis dans la barre latérale pour activer les algorithmes de scoring.")
    st.image("https://www.human-immobilier.fr/img/human-immobilier-groupe.jpg", use_column_width=True)
    
    with st.expander("❓ Aide : Quels fichiers utiliser ?"):
        st.write("""
        1. **Mandats :** Export de votre ERP (Format CSV/Excel) contenant l'âge du mandat et la typologie.
        2. **Évaluations :** Export des dossiers prospects (Estimations réalisées).
        3. **DPE :** Fichier ADEME ou Open Data des diagnostics récents sur votre secteur.
        """)
