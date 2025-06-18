import streamlit as st
import os
import numpy as np
from datetime import datetime, time as dt_time
import pandas as pd
from deepface import DeepFace
from PIL import Image
import cv2
import time
from concurrent.futures import ThreadPoolExecutor
import hashlib

# Configuration des dossiers
DATA_DIR = "database"
FACES_DIR = os.path.join(DATA_DIR, "faces")
ATTENDANCE_FILE = os.path.join(DATA_DIR, "attendance.csv")
LATE_ATTENDANCE_FILE = os.path.join(DATA_DIR, "late_attendance.csv")

# Créer les dossiers si nécessaires
os.makedirs(FACES_DIR, exist_ok=True)
if not os.path.exists(ATTENDANCE_FILE):
    pd.DataFrame(columns=["Nom", "Service", "Date", "Heure", "Type", "Statut"]).to_csv(ATTENDANCE_FILE, index=False)
if not os.path.exists(LATE_ATTENDANCE_FILE):
    pd.DataFrame(columns=["Nom", "Service", "Date", "Heure Pointage", "Heure Officielle", "Type", "Retard (minutes)"]).to_csv(LATE_ATTENDANCE_FILE, index=False)

# Configuration
OFFICIAL_TIMES = {
    "Arrivée": dt_time(8, 30),
    "Départ": dt_time(17, 0)
}
RECOGNITION_THRESHOLD = 0.3  # Seuil de similarité
CACHE_EXPIRATION = 3600  # 1 heure en secondes

# Cache pour les visages enregistrés
face_cache = {
    'last_update': 0,
    'faces': []
}

# Cache pour les données de pointage
data_cache = {
    'attendance': None,
    'late_attendance': None,
    'last_update': 0
}

def get_cached_faces():
    """Récupère les visages avec cache pour éviter les accès disque fréquents"""
    current_time = time.time()
    if current_time - face_cache['last_update'] > CACHE_EXPIRATION or not face_cache['faces']:
        face_cache['faces'] = [f for f in os.listdir(FACES_DIR) if f.endswith(".jpg")]
        face_cache['last_update'] = current_time
    return face_cache['faces']

def get_cached_data(file_path, cache_key):
    """Récupère les données avec cache"""
    current_time = time.time()
    if data_cache[cache_key] is None or current_time - data_cache['last_update'] > CACHE_EXPIRATION:
        data_cache[cache_key] = pd.read_csv(file_path)
        data_cache['last_update'] = current_time
    return data_cache[cache_key]

def save_face_image(name, service, image):
    """Optimisée avec compression d'image"""
    filename = f"{hashlib.md5((name+service).encode()).hexdigest()}.jpg"
    path = os.path.join(FACES_DIR, filename)
    
    img_array = np.array(image)
    if len(img_array.shape) == 3 and img_array.shape[2] == 4:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
    else:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    # Compression de l'image pour réduire la taille
    cv2.imwrite(path, img_array, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    
    # Mettre à jour le cache
    face_cache['faces'] = [f for f in os.listdir(FACES_DIR) if f.endswith(".jpg")]
    face_cache['last_update'] = time.time()

def recognize_face_parallel(captured_img):
    """Version parallélisée de la reconnaissance faciale"""
    img_array = np.array(captured_img)
    if len(img_array.shape) == 3 and img_array.shape[2] == 4:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
    else:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    temp_path = os.path.join(FACES_DIR, f"temp_{int(time.time())}.jpg")
    cv2.imwrite(temp_path, img_array)
    
    try:
        def compare_face(face_file):
            try:
                db_path = os.path.join(FACES_DIR, face_file)
                result = DeepFace.verify(
                    img1_path=temp_path,
                    img2_path=db_path,
                    model_name="SFace",
                    detector_backend="opencv",
                    enforce_detection=False,
                    distance_metric="cosine",
                    silent=True
                )
                return result, face_file
            except Exception:
                return None, face_file
        
        # Utilisation du ThreadPool pour paralléliser les comparaisons
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(compare_face, get_cached_faces()))
        
        for result, face_file in results:
            if result and result["verified"] and result["distance"] < RECOGNITION_THRESHOLD:
                # Récupérer les infos depuis le nom de fichier
                name_service = face_file.split('_')
                if len(name_service) >= 2:
                    name = name_service[0]
                    service = ' '.join(name_service[1:]).replace('.jpg', '')
                    return name, service, result["distance"]
        
        return None, None, None
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def calculate_late_time(check_time, check_type):
    """Optimisée avec traitement direct du temps"""
    official_time = OFFICIAL_TIMES[check_type]
    h, m, s = map(int, check_time.split(':'))
    check_time_obj = dt_time(h, m, s)
    
    if check_type == "Arrivée":
        if check_time_obj > official_time:
            return (h - official_time.hour) * 60 + (m - official_time.minute)
    else:  # Départ
        if check_time_obj < official_time:
            return (official_time.hour - h) * 60 + (official_time.minute - m)
    return 0

def mark_attendance(name, service, check_type):
    """Optimisée avec écriture unique et mise à jour du cache"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    
    late_minutes = calculate_late_time(time_str, check_type)
    status = "À l'heure" if late_minutes == 0 else f"Retard de {late_minutes} min"
    
    # Charger depuis le cache si disponible
    df = get_cached_data(ATTENDANCE_FILE, 'attendance').copy()
    
    new_row = {
        "Nom": name, "Service": service, "Date": date_str, 
        "Heure": time_str, "Type": check_type, "Statut": status
    }
    
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(ATTENDANCE_FILE, index=False)
    
    # Mettre à jour le cache
    data_cache['attendance'] = df
    data_cache['last_update'] = time.time()
    
    if late_minutes > 0:
        official_time_str = OFFICIAL_TIMES[check_type].strftime("%H:%M:%S")
        late_df = get_cached_data(LATE_ATTENDANCE_FILE, 'late_attendance').copy()
        
        late_row = {
            "Nom": name, "Service": service, "Date": date_str,
            "Heure Pointage": time_str, "Heure Officielle": official_time_str,
            "Type": check_type, "Retard (minutes)": late_minutes
        }
        
        late_df = pd.concat([late_df, pd.DataFrame([late_row])], ignore_index=True)
        late_df.to_csv(LATE_ATTENDANCE_FILE, index=False)
        data_cache['late_attendance'] = late_df
    
    return status

# -------------------- Interface Streamlit Optimisée ---------------------

st.set_page_config(
    page_title="Pointage Facial", 
    layout="centered",
    page_icon="📸"
)

# CSS optimisé
st.markdown("""
<style>
    .stButton>button { width: 100%; padding: 10px; border-radius: 5px; }
    .success-box { padding: 15px; background-color: #e6f7e6; border-radius: 5px; border-left: 5px solid #4CAF50; margin: 10px 0; }
    .error-box { padding: 15px; background-color: #ffebee; border-radius: 5px; border-left: 5px solid #f44336; margin: 10px 0; }
    .warning-box { padding: 15px; background-color: #fff8e1; border-radius: 5px; border-left: 5px solid #ffc107; margin: 10px 0; }
    .info-box { padding: 15px; background-color: #e3f2fd; border-radius: 5px; border-left: 5px solid #2196F3; margin: 10px 0; }
    [data-testid="stHorizontalBlock"] { align-items: center; }
    .stRadio > div { flex-direction:row; }
</style>
""", unsafe_allow_html=True)

# Menu latéral optimisé
menu = st.sidebar.radio(
    "Menu", 
    ["Accueil", "Enregistrement", "Pointage", "Historique", "Retards"],
    horizontal=True
)

# Page d'accueil
if menu == "Accueil":
    st.markdown("## Bienvenue dans l'application de pointage par reconnaissance faciale")
    cols = st.columns(2)
    with cols[0]:
        st.markdown("""
        **Fonctionnalités :**
        - 👤 Enregistrement des employés
        - 📸 Pointage automatique
        - 📊 Historique avec filtres
        - ⏱️ Gestion des retards
        
        **Heures officielles :**
        - Arrivée: 8h30
        - Départ: 17h00
        """)
    with cols[1]:
        st.image("https://img.freepik.com/vecteurs-libre/concept-reconnaissance-faciale_23-2148477110.jpg", 
                caption="Système de pointage par reconnaissance faciale")

# Enregistrement
elif menu == "Enregistrement":
    st.subheader("👤 Enregistrement d'un nouvel employé")
    
    with st.form("employee_form"):
        name = st.text_input("Nom complet*")
        service = st.selectbox("Service*", ["Direction", "RH", "Informatique", "Comptabilité", "Production", "Commercial"])
        
        st.info("Pour une meilleure reconnaissance :\n- Gardez une expression neutre\n- Regardez droit devant\n- Assurez un bon éclairage")
        
        img_file = st.camera_input("Prenez une photo de l'employé", key="register_cam")
        
        if st.form_submit_button("Enregistrer l'employé"):
            if not name or not service:
                st.error("Veuillez remplir tous les champs obligatoires (*)")
            elif img_file is None:
                st.error("Veuillez prendre une photo de l'employé")
            else:
                try:
                    image = Image.open(img_file)
                    save_face_image(name, service, image)
                    st.success(f"✅ Employé {name} ({service}) enregistré avec succès!")
                    st.image(image, caption="Photo enregistrée", width=300)
                except Exception as e:
                    st.error(f"Erreur lors de l'enregistrement : {str(e)}")

# Pointage
elif menu == "Pointage":
    st.subheader("📍 Système de pointage")
    check_type = st.radio("Type de pointage", ["Arrivée", "Départ"], horizontal=True)
    
    st.info(f"Prêt pour pointer une {check_type.lower()}. Cliquez sur le bouton ci-dessous.")
    
    if st.button(f"📸 Pointer mon {check_type.lower()}", type="primary"):
        st.session_state['capture_triggered'] = True
    
    if st.session_state.get('capture_triggered'):
        with st.spinner("Préparez-vous à être photographié..."):
            time.sleep(1)
            img_file = st.camera_input("Positionnez votre visage", key="check_cam")
            
            if img_file:
                try:
                    image = Image.open(img_file)
                    with st.spinner("Recherche en cours..."):
                        name, service, distance = recognize_face_parallel(image)
                        
                        if name:
                            status = mark_attendance(name, service, check_type)
                            if "Retard" in status:
                                st.warning(f"⚠️ {check_type} enregistrée pour {name} ({service}) - {status}")
                            else:
                                st.success(f"✅ {check_type} enregistrée pour {name} ({service}) - {status}")
                            
                            # Afficher les derniers pointages
                            df = get_cached_data(ATTENDANCE_FILE, 'attendance')
                            last_records = df[df["Nom"] == name].sort_values(by=["Date", "Heure"], ascending=False).head(3)
                            if not last_records.empty:
                                st.dataframe(last_records, hide_index=True)
                        else:
                            st.error("❌ Visage non reconnu. Veuillez vous rapprocher de l'administrateur.")
                except Exception as e:
                    st.error(f"Erreur technique : {str(e)}")
                finally:
                    st.session_state['capture_triggered'] = False

# Historique
elif menu == "Historique":
    st.subheader("📊 Historique des pointages")
    df = get_cached_data(ATTENDANCE_FILE, 'attendance')
    
    if df.empty:
        st.info("Aucun pointage enregistré")
    else:
        cols = st.columns(3)
        date_filter = cols[0].date_input("Filtrer par date")
        service_filter = cols[1].selectbox("Filtrer par service", ["Tous"] + list(df["Service"].unique()))
        name_filter = cols[2].selectbox("Filtrer par nom", ["Tous"] + list(df["Nom"].unique()))
        
        filtered_df = df.copy()
        if date_filter:
            filtered_df = filtered_df[filtered_df["Date"] == str(date_filter)]
        if service_filter != "Tous":
            filtered_df = filtered_df[filtered_df["Service"] == service_filter]
        if name_filter != "Tous":
            filtered_df = filtered_df[filtered_df["Nom"] == name_filter]
        
        # Affichage optimisé
        st.dataframe(filtered_df.sort_values(by=["Date", "Heure"], ascending=False), 
                    use_container_width=True, hide_index=True)

# Retards
elif menu == "Retards":
    st.subheader("⏱️ Historique des retards")
    late_df = get_cached_data(LATE_ATTENDANCE_FILE, 'late_attendance')
    
    if late_df.empty:
        st.info("Aucun retard enregistré")
    else:
        cols = st.columns(2)
        date_filter = cols[0].date_input("Filtrer par date", key="late_date")
        type_filter = cols[1].selectbox("Filtrer par type", ["Tous"] + list(late_df["Type"].unique()))
        
        filtered_df = late_df.copy()
        if date_filter:
            filtered_df = filtered_df[filtered_df["Date"] == str(date_filter)]
        if type_filter != "Tous":
            filtered_df = filtered_df[filtered_df["Type"] == type_filter]
        
        st.dataframe(filtered_df.sort_values(by=["Date", "Heure Pointage"], ascending=False), 
                    use_container_width=True, hide_index=True)