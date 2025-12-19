import streamlit as st
import pandas as pd
import requests
import io
import time

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="UpdateBase Pro | Carte Jeune",
    page_icon="🎓",
    layout="wide"
)

# Style CSS pour un look professionnel
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #004a99; color: white; font-weight: bold; }
    .main { background-color: #f5f7f9; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTION DE RÉCUPÉRATION DU FICHIER A ---
def get_file_from_portal():
    try:
        # Création d'une session pour maintenir la connexion (cookies)
        s = requests.Session()
        
        # Récupération des accès depuis les Secrets
        LOGIN_URL = st.secrets["server_access"]["login_url"]
        DOWNLOAD_URL = st.secrets["server_access"]["download_url"]
        
        # Payload spécifique pour le portail Carte Jeune
        payload = {
            'Login': st.secrets["server_access"]["user"],
            'Password': st.secrets["server_access"]["password"]
        }

        # 1. Connexion au portail
        with st.spinner("Connexion au portail régional..."):
            login_req = s.post(LOGIN_URL, data=payload, timeout=20)
            login_req.raise_for_status()

        # 2. Téléchargement de l'export
        with st.spinner("Téléchargement de l'export accès/restauration..."):
            response = s.get(DOWNLOAD_URL, timeout=30)
            response.raise_for_status()
            
        # 3. Conversion en DataFrame
        # On utilise io.BytesIO pour lire le contenu binaire en CSV
        df = pd.read_csv(io.BytesIO(response.content), sep=';', encoding='cp1252', encoding_errors='replace')
        return df

    except Exception as e:
        st.error(f"❌ Erreur de connexion au serveur : {e}")
        st.info("Note : Si l'erreur persiste, vérifiez que le portail accepte les connexions externes ou utilisez l'import manuel.")
        return None

# --- INTERFACE UTILISATEUR ---
st.title("🎓 Mise à jour Automatisée des Badges")
st.subheader("Portail Carte Jeune Région - Lycée")

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 📄 Source A (Portail)")
    # Option pour choisir entre auto et manuel
    method = st.toggle("Utiliser la récupération automatique", value=True)
    
    df_a = None
    if method:
        if st.button("🔄 Récupérer l'export automatique"):
            df_a = get_file_from_portal()
            if df_a is not None:
                st.session_state['df_a'] = df_a
                st.success("Données élèves récupérées !")
    else:
        file_a = st.file_uploader("Importer manuellement le fichier A.csv", type=['csv'])
        if file_a:
            df_a = pd.read_csv(file_a, sep=';', encoding='cp1252')
            st.session_state['df_a'] = df_a

with col_right:
    st.markdown("### 🗄️ Base B (Fichier Local)")
    file_b = st.file_uploader("Importer votre fichier B.csv actuel", type=['csv'])
    if file_b:
        df_b = pd.read_csv(file_b, sep=';', encoding='cp1252', encoding_errors='replace')
        st.session_state['df_b'] = df_b

# --- LOGIQUE DE FUSION ---
if 'df_a' in st.session_state and 'df_b' in st.session_state:
    st.divider()
    if st.button("⚡ EXECUTER LA FUSION DES DONNÉES"):
        try:
            with st.status("Traitement en cours...") as status:
                df_a = st.session_state['df_a']
                df_b = st.session_state['df_b']
                
                # Nettoyage des colonnes
                df_a.columns = df_a.columns.str.strip()
                df_b.columns = df_b.columns.str.strip()

                # Extraction par position (A) : Nom, Prénom, Badge
                df_a_extrait = df_a.iloc[:, [1, 2, 10]].copy()
                df_a_extrait.columns = ['NOM', 'PRENOM', 'BADGE']
                df_a_extrait['FAMILLE'] = 'eleve'

                # Formatage du Badge (13 chiffres)
                df_a_extrait['BADGE'] = df_a_extrait['BADGE'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.zfill(13)

                # Nettoyage de B : On garde tout sauf 'eleve'
                df_b['FAMILLE'] = df_b['FAMILLE'].fillna('').astype(str).str.strip()
                df_b_conserve = df_b[df_b['FAMILLE'].str.lower() != 'eleve'].copy()

                # Fusion finale
                df_final = pd.concat([df_b_conserve, df_a_extrait], ignore_index=True)
                df_final = df_final[['NOM', 'PRENOM', 'FAMILLE', 'BADGE']]

                status.update(label="Mise à jour réussie !", state="complete")

            # Rapport visuel
            st.markdown("### 📊 Rapport")
            m1, m2, m3 = st.columns(3)
            m1.metric("Élèves (A)", len(df_a_extrait))
            m2.metric("Personnel (B)", len(df_b_conserve))
            m3.metric("Total final", len(df_final))

            # Bouton de téléchargement
            output = io.BytesIO()
            df_final.to_csv(output, index=False, sep=';', encoding='utf-8-sig')
            
            st.download_button(
                label="📥 TÉLÉCHARGER LE NOUVEAU FICHIER B",
                data=output.getvalue(),
                file_name="Base_Badges_Complete.csv",
                mime="text/csv",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Erreur lors du traitement : {e}")
else:
    st.info("📢 Veuillez charger les deux sources de données pour commencer.")
