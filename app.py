import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="HUMAN RADAR | Pilotage & Performance", layout="wide")

# Style CSS pour une interface "Corporate"
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); border: 1px solid #e0e0e0; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #f8f9fa; border-radius: 5px 5px 0 0; padding: 10px 20px; }
    .stTabs [aria-selected="true"] { background-color: #004a99 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- OUTILS DE DÉTECTION ET NETTOYAGE ---

def clean_column_names(df):
    """Uniformise les colonnes : Majuscules et suppression des espaces."""
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df

def find_col(df, keywords):
    """Détecteur intelligent de colonnes (ex: trouve 'AGE_MANDAT' avec ['AGE', 'MANDAT'])."""
    for col in df.columns:
        if all(k.upper() in col.upper() for k in keywords):
            return col
    return None

def clean_address(addr):
    """Clé de matching pour comparer les adresses CRM et ADEME."""
    if pd.isna(addr): return ""
    addr = str(addr).lower()
    addr = addr.replace("avenue", "av").replace("boulevard", "bd").replace("rue", "r").replace("impasse", "imp")
    return re.sub(r'[^a-z0-9]', '', addr)

def analyze_friction(texte):
    """Analyse sémantique simplifiée pour Benjamin Salah."""
    texte = str(texte).lower()
    points = []
    if any(w in texte for w in ["prix", "cher", "budget", "avenant"]): points.append("💰 Prix")
    if any(w in texte for w in ["travaux", "déco", "rafraichissement"]): points.append("🛠️ État")
    if any(w in texte for w in ["bruit", "route", "nuisance"]): points.append("🔊 Nuisance")
    return points if points else ["✅ RAS"]

# --- BARRE LATÉRALE : IMPORTS ---
st.sidebar.image("https://www.human-immobilier.fr/img/logo-human-immobilier.svg", width=180)
st.sidebar.title("📥 Sources de Données")

main_file = st.sidebar.file_uploader("Fichier CRM (Excel multi-onglets)", type=['xlsx'])
dpe_file = st.sidebar.file_uploader("Base DPE ADEME (CSV ou Excel)", type=['csv', 'xlsx'])

if main_file:
    # Lecture du fichier Excel global
    xls = pd.ExcelFile(main_file)
    sheets = xls.sheet_names
    
    st.sidebar.markdown("---")
    sh_mandats = st.sidebar.selectbox("Onglet MANDATS", sheets, index=0)
    sh_evals = st.sidebar.selectbox("Onglet ÉVALUATIONS", sheets, index=min(1, len(sheets)-1))

    # Chargement des DataFrames
    df_m = clean_column_names(pd.read_excel(main_file, sheet_name=sh_mandats))
    df_e = clean_column_names(pd.read_excel(main_file, sheet_name=sh_evals))

    # Détection dynamique des colonnes clés
    c_age = find_col(df_m, ["AGE", "MANDAT"])  # Détecte AGE_MANDAT ou AGE MANDAT
    c_typo = find_col(df_m, ["TYPOLOGIE"])
    c_agence = find_col(df_m, ["AGENCE"])
    c_action = find_col(df_m, ["ACTION"])
    c_addr_e = find_col(df_e, ["ADRESSE"])

    # --- LOGIQUE DE MATCHING RADAR (SI DPE PRÉSENT) ---
    radar_matches = pd.DataFrame()
    if dpe_file:
        df_dpe = pd.read_csv(dpe_file) if dpe_file.name.endswith('.csv') else pd.read_excel(dpe_file)
        df_dpe = clean_column_names(df_dpe)
        c_addr_d = find_col(df_dpe, ["ADRESSE"]) or find_col(df_dpe, ["BAN"])
        
        if c_addr_e and c_addr_d:
            df_e['MATCH_KEY'] = df_e[c_addr_e].apply(clean_address)
            df_dpe['MATCH_KEY'] = df_dpe[c_addr_d].apply(clean_address)
            radar_matches = pd.merge(df_e, df_dpe, on='MATCH_KEY', how='inner')

    # --- AFFICHAGE DASHBOARD ---
    st.title("🚀 HUMAN Radar | Pilotage Performance")
    
    t1, t2, t3, t4 = st.tabs(["📈 Pilotage Global", "📡 Radar (Match DPE)", "⚠️ Analyse Risques", "🏢 Direction de Zone"])

    # TAB 1 : PILOTAGE
    with t1:
        col1, col2, col3 = st.columns(3)
        col1.metric("Stock Mandats", len(df_m))
        col2.metric("Base Évaluations", len(df_e))
        col3.metric("Alertes Radar", len(radar_matches), delta="Match DPE", delta_color="normal")

        if c_age:
            st.subheader("Santé du Stock (Ancienneté)")
            fig = px.histogram(df_m, x=c_age, color=c_typo, barmode="group",
                               labels={c_age: "Jours de Mandat"},
                               color_discrete_sequence=px.colors.qualitative.Prism)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Colonne d'âge introuvable dans l'onglet Mandats.")

    # TAB 2 : RADAR (OPPORTUNITÉS)
    with t2:
        st.header("📡 Prospects Chauds (Match ADEME)")
        if not radar_matches.empty:
            st.success(f"Détecté : {len(radar_matches)} prospects avec un DPE récent !")
            # Filtrage des colonnes utiles pour l'affichage
            cols_to_show = [c for c in [c_agence, 'NOMDOSSIERESTIMATION', c_addr_e, 'DATE_ETABLISSEMENT_DPE'] if c in radar_matches.columns]
            st.dataframe(radar_matches[cols_to_show], use_container_width=True)
            
            st.markdown("---")
            st.subheader("💬 Action Immédiate")
            selected = st.selectbox("Générer message pour :", radar_matches['NOMDOSSIERESTIMATION'] if 'NOMDOSSIERESTIMATION' in radar_matches.columns else ["Client"])
            st.code(f"Bonjour, suite à notre estimation de votre bien, je reviens vers vous pour actualiser votre dossier technique. Pouvons-nous en parler ?")
        else:
            st.info("Veuillez charger un fichier DPE pour activer la détection intelligente.")

    # TAB 3 : ANALYSE DES RISQUES
    with t3:
        st.header("🕵️ Analyse de la Friction & Freins à la vente")
        if c_action:
            df_m['FRICTIONS'] = df_m[c_action].apply(analyze_friction)
            all_f = [f for sublist in df_m['FRICTIONS'] for f in sublist if f != "✅ RAS"]
            
            col_a, col_b = st.columns([2, 1])
            with col_a:
                st.write("**Dossiers bloqués (Age > 200j)**")
                st.table(df_m[df_m[c_age] > 200][[c_agence, find_col(df_m, ["NOM"]) or c_age, c_action]].head(10))
            with col_b:
                if all_f:
                    f_df = pd.Series(all_f).value_counts().reset_index()
                    fig_pie = px.pie(f_df, values='count', names='index', title="Motifs de non-transformation")
                    st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.warning("Activez l'analyse en incluant une colonne 'Actions' ou 'Compte-rendu'.")

    # TAB 4 : DIRECTION DE ZONE
    with t4:
        st.header("🏢 Benchmark Inter-Agences")
        if c_agence and c_age:
            perf = df_m.groupby(c_agence)[c_age].mean().reset_index().sort_values(by=c_age)
            fig_bar = px.bar(perf, x=c_agence, y=c_age, color=c_age, 
                             color_continuous_scale='RdYlGn_r',
                             title="Âge Moyen du Stock (Plus c'est rouge, plus c'est lent)")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.error("Données d'agences manquantes pour le benchmark.")

else:
    st.info("👋 En attente du fichier Excel HUMAN (Mandats + Évaluations).")
    st.image("https://www.human-immobilier.fr/img/human-immobilier-groupe.jpg")