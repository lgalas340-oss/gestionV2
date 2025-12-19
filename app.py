import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup  # Nécessaire pour extraire le jeton de sécurité
import io

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="UpdateBase Pro | Carte Jeune", page_icon="🎓", layout="wide")

# --- FONCTION DE RÉCUPÉRATION AVANCÉE ---
def get_file_from_portal():
    try:
        s = requests.Session()
        # On se fait passer pour un navigateur moderne
        s.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        LOGIN_URL = st.secrets["login_url"]
        DOWNLOAD_URL = st.secrets["download_url"]

        # 1. Charger la page de login pour récupérer le jeton anti-contrefaçon (__RequestVerificationToken)
        with st.spinner("Initialisation de la session sécurisée..."):
            response = s.get(LOGIN_URL, timeout=20)
            soup = BeautifulSoup(response.text, 'html.parser')
            # Chercher le jeton caché dans le formulaire
            token = soup.find('input', {'name': '__RequestVerificationToken'})
            token_value = token['value'] if token else ""

        # 2. Préparation des identifiants avec le jeton de sécurité
        payload = {
            'Login': st.secrets["user"],
            'Password': st.secrets["password"],
            '__RequestVerificationToken': token_value,
            'RememberMe': 'false'
        }

        # 3. Connexion
        with st.spinner("Authentification sur le portail..."):
            login_req = s.post(LOGIN_URL, data=payload, timeout=20)
            if login_req.status_code == 400:
                st.error("Erreur 400 : Le portail refuse la connexion automatique.")
                st.info("Cause possible : Le site a détecté un script ou l'identifiant est incorrect.")
                return None
            login_req.raise_for_status()

        # 4. Téléchargement de l'export
        with st.spinner("Génération et téléchargement de l'export..."):
            response = s.get(DOWNLOAD_URL, timeout=30)
            response.raise_for_status()
            
        # 5. Lecture du fichier
        df = pd.read_csv(io.BytesIO(response.content), sep=';', encoding='cp1252', encoding_errors='replace')
        return df

    except Exception as e:
        st.error(f"❌ Erreur : {e}")
        return None

# --- INTERFACE UTILISATEUR ---
st.title("🎓 Mise à jour Automatisée des Badges")
st.divider()

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("### 📄 Source A (Portail Région)")
    auto_mode = st.toggle("Connexion automatique au portail", value=True)
    
    df_a = None
    if auto_mode:
        if st.button("🔄 Récupérer l'export maintenant"):
            df_a = get_file_from_portal()
            if df_a is not None:
                st.session_state['df_a'] = df_a
                st.success("Données élèves importées !")
    else:
        file_a = st.file_uploader("Importer manuellement A.csv", type=['csv'])
        if file_a:
            df_a = pd.read_csv(file_a, sep=';', encoding='cp1252')
            st.session_state['df_a'] = df_a

with col_b:
    st.markdown("### 🗄️ Source B (Fichier Local)")
    file_b = st.file_uploader("Importer fichier B.csv", type=['csv'])
    if file_b:
        st.session_state['df_b'] = pd.read_csv(file_b, sep=';', encoding='cp1252', encoding_errors='replace')

# --- LOGIQUE DE FUSION ---
if 'df_a' in st.session_state and 'df_b' in st.session_state:
    st.divider()
    if st.button("⚡ LANCER LA MISE À JOUR"):
        try:
            df_a = st.session_state['df_a']
            df_b = st.session_state['df_b']
            
            # Extraction positionnelle
            df_a_extrait = df_a.iloc[:, [1, 2, 10]].copy()
            df_a_extrait.columns = ['NOM', 'PRENOM', 'BADGE']
            df_a_extrait['FAMILLE'] = 'eleve'
            df_a_extrait['BADGE'] = df_a_extrait['BADGE'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.zfill(13)

            # Nettoyage B
            df_b_conserve = df_b[df_b['FAMILLE'].astype(str).str.lower() != 'eleve'].copy()

            # Fusion
            df_final = pd.concat([df_b_conserve, df_a_extrait], ignore_index=True)
            df_final = df_final[['NOM', 'PRENOM', 'FAMILLE', 'BADGE']]

            st.success(f"Fusion terminée : {len(df_final)} lignes au total.")
            
            output = io.BytesIO()
            df_final.to_csv(output, index=False, sep=';', encoding='utf-8-sig')
            st.download_button("📥 Télécharger la base finale", output.getvalue(), "Base_MAJ.csv", "text/csv", use_container_width=True)
        except Exception as e:
            st.error(f"Erreur de traitement : {e}")
