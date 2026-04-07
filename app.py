import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="HUMAN RADAR v4", layout="wide")

# --- OUTILS DE NETTOYAGE ---
def clean_column_names(df):
    """Nettoie les noms de colonnes : enlève espaces, met en majuscules pour uniformiser"""
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df

def clean_address(addr):
    if pd.isna(addr): return ""
    addr = str(addr).lower()
    addr = addr.replace("avenue", "av").replace("boulevard", "bd").replace("rue", "r").replace("impasse", "imp")
    return re.sub(r'[^a-z0-9]', '', addr)

# --- SIDEBAR ---
st.sidebar.title("🏢 HUMAN Data Center")
main_file = st.sidebar.file_uploader("📂 Charger fichier Data (Excel Multi-feuilles)", type=['xlsx'])
dpe_file = st.sidebar.file_uploader("📄 Charger fichier DPE ADEME", type=['csv', 'xlsx'])

if main_file:
    # Lecture du Excel
    all_sheets = pd.read_excel(main_file, sheet_name=None)
    sheet_names = list(all_sheets.keys())
    
    st.sidebar.success(f"Feuilles détectées : {len(sheet_names)}")
    
    # Sélection des feuilles
    sh_mandats = st.sidebar.selectbox("Feuille MANDATS", sheet_names, index=0)
    sh_evals = st.sidebar.selectbox("Feuille EVALUATIONS", sheet_names, index=min(1, len(sheet_names)-1))

    # Chargement et nettoyage immédiat des colonnes
    df_m = clean_column_names(all_sheets[sh_mandats])
    df_e = clean_column_names(all_sheets[sh_evals])

    # --- LOGIQUE RADAR (DPE) ---
    if dpe_file:
        df_dpe = pd.read_csv(dpe_file) if dpe_file.name.endswith('.csv') else pd.read_excel(dpe_file)
        df_dpe = clean_column_names(df_dpe)
        
        # On cherche les colonnes d'adresse de manière flexible
        col_addr_e = next((c for c in df_e.columns if 'ADRESSE' in c), None)
        col_addr_d = next((c for c in df_dpe.columns if 'ADRESSE' in c or 'BAN' in c), None)

        if col_addr_e and col_addr_d:
            df_e['ADDR_KEY'] = df_e[col_addr_e].apply(clean_address)
            df_dpe['ADDR_KEY'] = df_dpe[col_addr_d].apply(clean_address)
            radar_matches = pd.merge(df_e, df_dpe, on='ADDR_KEY', how='inner')
        else:
            radar_matches = pd.DataFrame()
    else:
        radar_matches = pd.DataFrame()

    # --- AFFICHAGE DASHBOARD ---
    st.title("🚀 Pilotage Commercial HUMAN")
    
    tab1, tab2, tab3 = st.tabs(["📈 Pilotage", "📡 Radar DPE", "🏢 Zone"])

    # --- TAB 1 : PILOTAGE ---
    with tab1:
        # On vérifie si les colonnes attendues existent (en Majuscules grâce au nettoyage)
        col_x = "AGE MANDAT" if "AGE MANDAT" in df_m.columns else None
        col_color = "TYPOLOGIE" if "TYPOLOGIE" in df_m.columns else None
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Stock Mandats", len(df_m))
        c2.metric("Total Évaluations", len(df_e))
        c3.metric("Matches DPE", len(radar_matches))

        if col_x:
            st.subheader("Répartition du stock par ancienneté")
            fig_evol = px.histogram(df_m, x=col_x, color=col_color, 
                                     title="Analyse de l'ancienneté du stock",
                                     labels={col_x: "Jours de mandat"})
            st.plotly_chart(fig_evol, use_container_width=True)
        else:
            st.error(f"❌ La colonne 'AGE MANDAT' est introuvable. Colonnes présentes : {list(df_m.columns)}")

    # --- TAB 2 : RADAR DPE ---
    with tab2:
        if not radar_matches.empty:
            st.success(f"🎯 {len(radar_matches)} opportunités détectées !")
            st.dataframe(radar_matches, use_container_width=True)
        else:
            st.info("Aucun match trouvé ou fichier DPE manquant.")

    # --- TAB 3 : ZONE ---
    with tab3:
        col_agence = next((c for c in df_m.columns if 'AGENCE' in c), None)
        if col_agence and col_x:
            perf_ag = df_m.groupby(col_agence)[col_x].mean().reset_index()
            fig_bar = px.bar(perf_ag, x=col_agence, y=col_x, title="Âge Moyen du Stock par Agence")
            st.plotly_chart(fig_bar, use_container_width=True)

else:
    st.info("👋 En attente du fichier Excel principal.")