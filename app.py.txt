import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="HUMAN RADAR v3", layout="wide")

st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 5px; padding: 10px; }
    .stTabs [aria-selected="true"] { background-color: #004a99; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- OUTILS DE NETTOYAGE ---
def clean_address(addr):
    if pd.isna(addr): return ""
    addr = str(addr).lower()
    addr = addr.replace("avenue", "av").replace("boulevard", "bd").replace("rue", "r").replace("impasse", "imp")
    return re.sub(r'[^a-z0-9]', '', addr)

# --- CHARGEMENT DES DONNÉES ---
st.sidebar.title("🏢 HUMAN Data Center")

# 1. Fichier Principal (Mandats + Evals)
main_file = st.sidebar.file_uploader("📂 Charger fichier Data (Excel Multi-feuilles)", type=['xlsx'])

# 2. Fichier DPE
dpe_file = st.sidebar.file_uploader("📄 Charger fichier DPE ADEME", type=['csv', 'xlsx'])

if main_file:
    # Lecture de toutes les feuilles d'un coup
    all_sheets = pd.read_excel(main_file, sheet_name=None)
    sheet_names = list(all_sheets.keys())
    
    st.sidebar.success(f"Feuilles détectées : {', '.join(sheet_names)}")
    
    # Sélection intelligente ou manuelle des feuilles
    sh_mandats = st.sidebar.selectbox("Sélectionner la feuille MANDATS", sheet_names, 
                                      index=sheet_names.index(next(s for s in sheet_names if 'mandat' in s.lower())) if any('mandat' in s.lower() for s in sheet_names) else 0)
    
    sh_evals = st.sidebar.selectbox("Sélectionner la feuille EVALUATIONS", sheet_names,
                                     index=sheet_names.index(next(s for s in sheet_names if 'eval' in s.lower())) if any('eval' in s.lower() for s in sheet_names) else 0)

    df_m = all_sheets[sh_mandats]
    df_e = all_sheets[sh_evals]
    
    # Nettoyage des noms de colonnes
    df_m.columns = [c.strip() for c in df_m.columns]
    df_e.columns = [c.strip() for c in df_e.columns]

    # --- LOGIQUE RADAR (DPE) ---
    if dpe_file:
        df_dpe = pd.read_csv(dpe_file) if dpe_file.name.endswith('.csv') else pd.read_excel(dpe_file)
        df_dpe.columns = [c.strip() for c in df_dpe.columns]
        
        # Matching intelligent
        df_e['addr_key'] = df_e['BienAdresse_Adresse'].apply(clean_address)
        df_dpe['addr_key'] = df_dpe['adresse_ban'].apply(clean_address)
        radar_matches = pd.merge(df_e, df_dpe, on='addr_key', how='inner')
    else:
        radar_matches = pd.DataFrame()

    # --- AFFICHAGE DASHBOARD ---
    st.title("🚀 Pilotage Commercial HUMAN Immobilier")
    
    tabs = st.tabs(["📈 Pilotage", "📡 Radar DPE", "⚠️ Risques Stock", "💎 Opportunités", "🏢 Zone"])

    # --- TAB 1 : PILOTAGE ---
    with tabs[0]:
        c1, c2, c3 = st.columns(3)
        c1.metric("Stock Mandats", len(df_m))
        c2.metric("Total Évaluations", len(df_e))
        c3.metric("Matches DPE", len(radar_matches))
        
        fig_evol = px.histogram(df_m, x="AGE MANDAT", color="Typologie", title="Répartition par Ancienneté")
        st.plotly_chart(fig_evol, use_container_width=True)

    # --- TAB 2 : RADAR DPE ---
    with tabs[1]:
        st.header("🔍 Radar de Conversion (Matching ADEME)")
        if not radar_matches.empty:
            st.success(f"Cibles Prioritaires : {len(radar_matches)} prospects ont émis un DPE !")
            st.dataframe(radar_matches[['txtAgence', 'NomDossierEstimation', 'BienAdresse_Adresse', 'date_etablissement_dpe']], use_container_width=True)
        else:
            st.warning("Aucun match trouvé. Importez un fichier DPE pour activer le radar.")

    # --- TAB 3 : RISQUES ---
    with tabs[2]:
        st.header("🚨 Analyse des Mandats à Risque")
        # Calcul probabilité de perte (Score basé sur Age et Actions)
        df_m['Score_Risque'] = df_m['AGE MANDAT'].apply(lambda x: "Critique" if x > 250 else ("Moyen" if x > 150 else "Sain"))
        
        fig_risk = px.sunburst(df_m, path=['txtAgence', 'Score_Risque', 'Typologie'], values='AGE MANDAT')
        st.plotly_chart(fig_risk, use_container_width=True)

    # --- TAB 4 : OPPORTUNITÉS ---
    with tabs[3]:
        st.header("💰 Opportunités de Relance (Next Action)")
        # Analyse des évaluations froides à réactiver
        df_e['Prochaine_Action'] = "Relance Estimation +6 mois"
        st.table(df_e[['NomDossierEstimation', 'DateSaisie', 'Prochaine_Action']].head(10))

    # --- TAB 5 : ZONE ---
    with tabs[4]:
        st.header("🏆 Benchmarking Inter-Agences")
        perf_ag = df_m.groupby('txtAgence')['AGE MANDAT'].mean().reset_index()
        fig_bar = px.bar(perf_ag, x='txtAgence', y='AGE MANDAT', title="Âge Moyen du Stock par Agence")
        st.plotly_chart(fig_bar, use_container_width=True)

else:
    st.info("👋 Veuillez charger votre fichier Excel principal (contenant les feuilles Mandats et Evaluations).")
    st.image("https://www.human-immobilier.fr/img/logo-human-immobilier.svg", width=300)