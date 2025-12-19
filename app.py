import streamlit as st
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
import io
import time

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="UpdateBase Pro | Lycée", page_icon="🎓", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #004a99; color: white; font-weight: bold; }
    .main { background-color: #f5f7f9; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTION DE CONNEXION AU SERVEUR ---
def get_remote_file_a():
    try:
        url = st.secrets["server_access"]["url"]
        user = st.secrets["server_access"]["user"]
        pwd = st.secrets["server_access"]["password"]
        
        response = requests.get(url, auth=HTTPBasicAuth(user, pwd), timeout=15)
        response.raise_for_status()
        
        # Lecture du flux de données
        df = pd.read_csv(io.BytesIO(response.content), sep=';', encoding='cp1252', encoding_errors='replace')
        return df
    except Exception as e:
        st.error(f"❌ Erreur de connexion au serveur : {e}")
        return None

# --- INTERFACE PRINCIPALE ---
st.title("🎓 Mise à jour Automatisée des Badges")
st.divider()

col_left, col_right = st.columns([1, 1])

with col_left:
    st.markdown("### 📄 Source Élèves (Fichier A)")
    source_method = st.radio("Méthode de récupération :", ["Serveur distant (Auto)", "Téléchargement manuel"])
    
    df_a = None
    if source_method == "Serveur distant (Auto)":
        if st.button("🔄 Récupérer depuis le serveur"):
            with st.spinner("Connexion au serveur en cours..."):
                df_a = get_remote_file_a()
                if df_a is not None:
                    st.session_state['df_a'] = df_a
                    st.success("Données récupérées !")
    else:
        file_a = st.file_uploader("Choisir le fichier A.csv", type=['csv'])
        if file_a:
            df_a = pd.read_csv(file_a, sep=';', encoding='cp1252', encoding_errors='replace')
            st.session_state['df_a'] = df_a

with col_right:
    st.markdown("### 🗄️ Base Globale (Fichier B)")
    file_b = st.file_uploader("Choisir le fichier B.csv actuel", type=['csv'])
    if file_b:
        df_b = pd.read_csv(file_b, sep=';', encoding='cp1252', encoding_errors='replace')
        st.session_state['df_b'] = df_b

# --- TRAITEMENT DES DONNÉES ---
if 'df_a' in st.session_state and 'df_b' in st.session_state:
    st.divider()
    if st.button("⚡ LANCER LA FUSION ET LA MISE À JOUR"):
        try:
            with st.status("Traitement en cours...", expanded=True) as status:
                df_a = st.session_state['df_a']
                df_b = st.session_state['df_b']
                
                # Nettoyage noms de colonnes
                df_a.columns = df_a.columns.str.strip()
                df_b.columns = df_b.columns.str.strip()

                # Extraction par position (A)
                df_a_extrait = df_a.iloc[:, [1, 2, 10]].copy()
                df_a_extrait.columns = ['NOM', 'PRENOM', 'BADGE']
                df_a_extrait['FAMILLE'] = 'eleve'

                # Formatage Badge (13 chiffres)
                df_a_extrait['BADGE'] = df_a_extrait['BADGE'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.zfill(13)

                # Conservation des agents/profs (B)
                df_b['FAMILLE'] = df_b['FAMILLE'].fillna('').astype(str).str.strip()
                df_b_conserve = df_b[df_b['FAMILLE'].str.lower() != 'eleve'].copy()

                # Fusion finale
                df_final = pd.concat([df_b_conserve, df_a_extrait], ignore_index=True)
                df_final = df_final[['NOM', 'PRENOM', 'FAMILLE', 'BADGE']]

                status.update(label="Traitement terminé !", state="complete")

            # Affichage du rapport
            st.markdown("### 📊 Rapport d'exécution")
            m1, m2, m3 = st.columns(3)
            m1.metric("Nouveaux élèves (A)", len(df_a_extrait))
            m2.metric("Personnel conservé (B)", len(df_b_conserve))
            m3.metric("Total base finale", len(df_final))

            # Préparation du téléchargement
            output = io.BytesIO()
            df_final.to_csv(output, index=False, sep=';', encoding='utf-8-sig')
            
            st.download_button(
                label="📥 TÉLÉCHARGER LA BASE MISE À JOUR",
                data=output.getvalue(),
                file_name="Base_Badges_MAJ.csv",
                mime="text/csv",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Erreur durant la fusion : {e}")

else:
    st.info("💡 En attente des deux sources de données pour activer la fusion.")
