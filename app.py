import streamlit as st
import pandas as pd
import requests
import io
import time

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="UpdateBase Pro | Carte Jeune", page_icon="🎓", layout="wide")

# Style CSS pour une interface pro
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #004a99; color: white; font-weight: bold; }
    .main { background-color: #f5f7f9; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTION DE RÉCUPÉRATION DU FICHIER ---
def get_file_from_portal():
    try:
        # Création d'une session pour gérer les cookies de connexion
        s = requests.Session()
        
        # Récupération des accès depuis les Secrets simplifiés
        LOGIN_URL = st.secrets["login_url"]
        DOWNLOAD_URL = st.secrets["download_url"]
        
        # Préparation des identifiants (Login/Password)
        payload = {
            'Login': st.secrets["user"],
            'Password': st.secrets["password"]
        }

        # 1. Connexion au portail
        with st.spinner("Authentification sur le portail Région..."):
            login_req = s.post(LOGIN_URL, data=payload, timeout=20)
            login_req.raise_for_status()

        # 2. Téléchargement du fichier généré
        with st.spinner("Téléchargement de l'export en cours..."):
            response = s.get(DOWNLOAD_URL, timeout=30)
            response.raise_for_status()
            
        # 3. Conversion du contenu binaire en DataFrame Pandas
        # On utilise cp1252 car c'est le format standard des exports Windows en France
        df = pd.read_csv(io.BytesIO(response.content), sep=';', encoding='cp1252', encoding_errors='replace')
        return df

    except Exception as e:
        st.error(f"❌ Erreur technique : {e}")
        st.info("Astuce : Si le serveur est en maintenance, utilisez l'import manuel ci-dessous.")
        return None

# --- INTERFACE UTILISATEUR ---
st.title("🎓 Mise à jour Automatisée des Badges")
st.caption("Outil de synchronisation entre le Portail Région et votre Base Locale")

st.divider()

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("### 📄 Étape 1 : Source Élèves (A)")
    mode_auto = st.toggle("Activer la récupération automatique", value=True)
    
    df_a = None
    if mode_auto:
        if st.button("🔄 Lancer l'import depuis le Portail"):
            df_a = get_file_from_portal()
            if df_a is not None:
                st.session_state['df_a'] = df_a
                st.success("Données élèves importées avec succès !")
    else:
        file_a = st.file_uploader("Glisser le fichier A.csv ici", type=['csv'])
        if file_a:
            df_a = pd.read_csv(file_a, sep=';', encoding='cp1252')
            st.session_state['df_a'] = df_a

with col_b:
    st.markdown("### 🗄️ Étape 2 : Base Actuelle (B)")
    file_b = st.file_uploader("Glisser votre fichier B.csv (badges actuels)", type=['csv'])
    if file_b:
        df_b = pd.read_csv(file_b, sep=';', encoding='cp1252', encoding_errors='replace')
        st.session_state['df_b'] = df_b

# --- TRAITEMENT ET FUSION ---
if 'df_a' in st.session_state and 'df_b' in st.session_state:
    st.divider()
    if st.button("⚡ CRÉER LA NOUVELLE BASE MISE À JOUR"):
        try:
            with st.status("Traitement des fichiers...") as status:
                df_a = st.session_state['df_a']
                df_b = st.session_state['df_b']
                
                # Nettoyage des noms de colonnes (espaces invisibles)
                df_a.columns = df_a.columns.str.strip()
                df_b.columns = df_b.columns.str.strip()

                # Extraction (Position 1=Nom, 2=Prénom, 10=Badge)
                df_a_extrait = df_a.iloc[:, [1, 2, 10]].copy()
                df_a_extrait.columns = ['NOM', 'PRENOM', 'BADGE']
                df_a_extrait['FAMILLE'] = 'eleve'

                # Nettoyage et formatage Badge sur 13 chiffres
                df_a_extrait['BADGE'] = df_a_extrait['BADGE'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.zfill(13)

                # Conservation des personnels dans le fichier B
                df_b['FAMILLE'] = df_b['FAMILLE'].fillna('').astype(str).str.strip()
                df_b_conserve = df_b[df_b['FAMILLE'].str.lower() != 'eleve'].copy()

                # Fusion des deux listes
                df_final = pd.concat([df_b_conserve, df_a_extrait], ignore_index=True)
                df_final = df_final[['NOM', 'PRENOM', 'FAMILLE', 'BADGE']]

                status.update(label="Base de données prête !", state="complete")

            # Rapport de synthèse
            st.markdown("### 📊 Synthèse des modifications")
            res1, res2, res3 = st.columns(3)
            res1.metric("Élèves importés (A)", len(df_a_extrait))
            res2.metric("Personnels conservés (B)", len(df_b_conserve))
            res3.metric("Total lignes final", len(df_final))

            # Bouton de téléchargement final
            csv_data = io.BytesIO()
            df_final.to_csv(csv_data, index=False, sep=';', encoding='utf-8-sig')
            
            st.download_button(
                label="📥 TÉLÉCHARGER LE FICHIER B FINAL",
                data=csv_data.getvalue(),
                file_name="Base_Badges_MAJ.csv",
                mime="text/csv",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Erreur pendant la fusion : {e}")
else:
    st.info("💡 En attente des données A et B pour activer le bouton de fusion.")
