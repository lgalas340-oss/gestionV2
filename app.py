import streamlit as st
import pandas as pd
import requests
import io

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="UpdateBase Pro | Restauration", page_icon="🎓", layout="wide")

def get_file_from_portal():
    try:
        s = requests.Session()
        
        # 1. Récupération des secrets
        LOGIN_URL = st.secrets["server_access"]["login_url"]
        DOWNLOAD_URL = st.secrets["server_access"]["download_url"]
        payload = {
            'UserName': st.secrets["server_access"]["user"], # Vérifiez le nom exact du champ (UserName, Login...)
            'Password': st.secrets["server_access"]["password"]
        }

        # 2. Simulation de la connexion
        with st.spinner("Connexion au portail de restauration..."):
            login_req = s.post(LOGIN_URL, data=payload, timeout=15)
            login_req.raise_for_status()

        # 3. Téléchargement du fichier
        with st.spinner("Génération de l'export CSV..."):
            response = s.get(DOWNLOAD_URL, timeout=30)
            response.raise_for_status()
            
        # 4. Lecture des données
        df = pd.read_csv(io.BytesIO(response.content), sep=';', encoding='cp1252', encoding_errors='replace')
        return df

    except Exception as e:
        st.error(f"❌ Erreur de connexion au portail : {e}")
        st.info("Vérifiez que l'URL de login et les noms des champs sont corrects.")
        return None

# --- INTERFACE ---
st.title("🎓 Mise à jour Automatisée des Badges")
st.write("Ce module se connecte au portail pour récupérer l'export accès/restauration.")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📄 Source A (Portail)")
    if st.button("🔄 Récupérer l'export automatique"):
        df_a = get_file_from_portal()
        if df_a is not None:
            st.session_state['df_a'] = df_a
            st.success("Données élèves importées !")

with col2:
    st.markdown("### 🗄️ Base B (Locale)")
    file_b = st.file_uploader("Fichier B.csv actuel", type=['csv'])
    if file_b:
        st.session_state['df_b'] = pd.read_csv(file_b, sep=';', encoding='cp1252')

# --- LOGIQUE DE FUSION ---
if 'df_a' in st.session_state and 'df_b' in st.session_state:
    st.divider()
    if st.button("⚡ LANCER LA MISE À JOUR"):
        df_a = st.session_state['df_a']
        df_b = st.session_state['df_b']
        
        # Traitement identique aux étapes précédentes
        df_a.columns = df_a.columns.str.strip()
        df_b.columns = df_b.columns.str.strip()

        # Extraction (Position : 1=Nom, 2=Prénom, 10=Badge)
        df_a_extrait = df_a.iloc[:, [1, 2, 10]].copy()
        df_a_extrait.columns = ['NOM', 'PRENOM', 'BADGE']
        df_a_extrait['FAMILLE'] = 'eleve'
        df_a_extrait['BADGE'] = df_a_extrait['BADGE'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.zfill(13)

        # Nettoyage B
        df_b_conserve = df_b[df_b['FAMILLE'].astype(str).str.lower() != 'eleve'].copy()

        # Fusion
        df_final = pd.concat([df_b_conserve, df_a_extrait], ignore_index=True)
        df_final = df_final[['NOM', 'PRENOM', 'FAMILLE', 'BADGE']]

        st.success("Fusion terminée !")
        
        # Téléchargement
        output = io.BytesIO()
        df_final.to_csv(output, index=False, sep=';', encoding='utf-8-sig')
        st.download_button("📥 Télécharger Base_MAJ.csv", output.getvalue(), "Base_MAJ.csv", "text/csv")
