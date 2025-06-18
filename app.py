import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta
import os
import csv

# Configuration de la page
st.set_page_config(
    page_title="Application de Pointage", 
    layout="wide",
    initial_sidebar_state="auto"
)

# Chemins des fichiers
EMPLOYES_FILE = "employes.csv"
POINTAGE_FILE = "pointage.csv"
RETARDS_FILE = "retards.csv"

# Heures par défaut
HEURE_ENTREE_DEFAUT = time(8, 0)  # 8h00
HEURE_SORTIE_DEFAUT = time(17, 0)  # 17h00
SEUIL_RETARD = 15  # minutes

# Services disponibles
SERVICES_DISPONIBLES = [
    "Administration",
    "Production",
    "Comptabilité",
    "Ressources Humaines",
    "Informatique",
    "Commercial"
]

# Détection d'appareil mobile simplifiée
def is_mobile():
    """Détection basique d'appareil mobile basée sur la largeur d'écran"""
    return st.session_state.get('screen_width', 1000) < 768

# Créer les fichiers s'ils n'existent pas
def init_files():
    # Fichier des employés
    if not os.path.exists(EMPLOYES_FILE):
        with open(EMPLOYES_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Nom", "Prenom", "Service", "Heure_Entree", "Heure_Sortie"])
    
    # Fichier de pointage
    if not os.path.exists(POINTAGE_FILE):
        with open(POINTAGE_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Nom", "Prenom", "Service", "Type", "Heure", "Date"])
    
    # Fichier des retards
    if not os.path.exists(RETARDS_FILE):
        with open(RETARDS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Nom", "Prenom", "Service", "Heure_Arrivee", "Heure_Officielle", "Retard_min", "Date"])

# Charger les données
def load_data(filename):
    try:
        return pd.read_csv(filename)
    except:
        return pd.DataFrame()

# Sauvegarder les données
def save_data(df, filename):
    df.to_csv(filename, index=False, encoding='utf-8')

# Convertir string en time
def str_to_time(time_str):
    try:
        return datetime.strptime(time_str, "%H:%M").time()
    except:
        return HEURE_ENTREE_DEFAUT

# Fonctions de gestion du personnel
def ajouter_employe(nom, prenom, service, heure_entree=None, heure_sortie=None):
    df = load_data(EMPLOYES_FILE)
    new_id = df["ID"].max() + 1 if not df.empty else 1
    
    if heure_entree is None:
        heure_entree = HEURE_ENTREE_DEFAUT
    if heure_sortie is None:
        heure_sortie = HEURE_SORTIE_DEFAUT
    
    new_employe = pd.DataFrame([[new_id, nom, prenom, service, heure_entree.strftime("%H:%M"), heure_sortie.strftime("%H:%M")]], 
                            columns=["ID", "Nom", "Prenom", "Service", "Heure_Entree", "Heure_Sortie"])
    df = pd.concat([df, new_employe], ignore_index=True)
    save_data(df, EMPLOYES_FILE)
    st.success(f"Employé {prenom} {nom} ajouté avec succès!")

def modifier_employe(id_employe, nom=None, prenom=None, service=None, heure_entree=None, heure_sortie=None):
    df = load_data(EMPLOYES_FILE)
    idx = df[df["ID"] == id_employe].index[0]
    
    if nom: df.at[idx, "Nom"] = nom
    if prenom: df.at[idx, "Prenom"] = prenom
    if service: df.at[idx, "Service"] = service
    if heure_entree: 
        heure_entree = heure_entree.time() if isinstance(heure_entree, datetime) else heure_entree
        df.at[idx, "Heure_Entree"] = heure_entree.strftime("%H:%M")
    if heure_sortie: 
        heure_sortie = heure_sortie.time() if isinstance(heure_sortie, datetime) else heure_sortie
        df.at[idx, "Heure_Sortie"] = heure_sortie.strftime("%H:%M")
    
    save_data(df, EMPLOYES_FILE)
    st.success("Employé modifié avec succès!")

def supprimer_employe(id_employe):
    df = load_data(EMPLOYES_FILE)
    df = df[df["ID"] != id_employe]
    save_data(df, EMPLOYES_FILE)
    st.success("Employé supprimé avec succès!")

# Fonctions de pointage
def pointer(id_employe, type_pointage):
    employes = load_data(EMPLOYES_FILE)
    employe = employes[employes["ID"] == id_employe].iloc[0]
    
    now = datetime.now()
    heure_actuelle = now.time()
    date_actuelle = now.date()
    
    # Enregistrement du pointage
    df_pointage = load_data(POINTAGE_FILE)
    new_pointage = pd.DataFrame([[id_employe, employe["Nom"], employe["Prenom"], employe["Service"], type_pointage, heure_actuelle.strftime("%H:%M"), date_actuelle.strftime("%Y-%m-%d")]],
                            columns=["ID", "Nom", "Prenom", "Service", "Type", "Heure", "Date"])
    df_pointage = pd.concat([df_pointage, new_pointage], ignore_index=True)
    save_data(df_pointage, POINTAGE_FILE)
    
    # Vérification des retards pour l'arrivée
    if type_pointage == "Entrée":
        heure_officielle = str_to_time(employe["Heure_Entree"])
        retard = (datetime.combine(date_actuelle, heure_actuelle) - 
                datetime.combine(date_actuelle, heure_officielle)).total_seconds() / 60
        
        if retard > SEUIL_RETARD:
            df_retards = load_data(RETARDS_FILE)
            new_retard = pd.DataFrame([[id_employe, employe["Nom"], employe["Prenom"], employe["Service"], 
                                    heure_actuelle.strftime("%H:%M"), heure_officielle.strftime("%H:%M"), round(retard), date_actuelle.strftime("%Y-%m-%d")]],
                                  columns=["ID", "Nom", "Prenom", "Service", "Heure_Arrivee", "Heure_Officielle", "Retard_min", "Date"])
            df_retards = pd.concat([df_retards, new_retard], ignore_index=True)
            save_data(df_retards, RETARDS_FILE)
            st.warning(f"Retard enregistré: {round(retard)} minutes")

# Calculer les heures travaillées
def calculer_heures_travaillees(id_employe, date):
    pointages = load_data(POINTAGE_FILE)
    pointages_date = pointages[(pointages["ID"] == id_employe) & (pointages["Date"] == date.strftime("%Y-%m-%d"))]
    
    entrees = pointages_date[pointages_date["Type"] == "Entrée"]["Heure"].sort_values()
    sorties = pointages_date[pointages_date["Type"] == "Sortie"]["Heure"].sort_values()
    
    if len(entrees) == 0 or len(sorties) == 0:
        return timedelta(0)
    
    premiere_entree = str_to_time(entrees.iloc[0])
    derniere_sortie = str_to_time(sorties.iloc[-1])
    
    return datetime.combine(date, derniere_sortie) - datetime.combine(date, premiere_entree)

# Interface Streamlit adaptative
def main():
    init_files()
    
    # Ajout de meta pour le viewport mobile
    st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    """, unsafe_allow_html=True)
    
    # Détection basique de la largeur d'écran
    if 'screen_width' not in st.session_state:
        st.session_state.screen_width = 1000  # Valeur par défaut
    
    st.title("📝 Application de Pointage Avancée")
    
    # Menu adaptatif
    if is_mobile():
        menu = st.selectbox("Menu", ["Pointage", "Gestion du Personnel", "Historique", "Retards", "Statistiques"])
    else:
        menu = st.sidebar.selectbox("Menu", ["Pointage", "Gestion du Personnel", "Historique", "Retards", "Statistiques"])
    
    if menu == "Pointage":
        st.header("Enregistrement des pointages")
        
        employes = load_data(EMPLOYES_FILE)
        if employes.empty:
            st.warning("Aucun employé enregistré. Veuillez ajouter des employés d'abord.")
            return
        
        for col in ["ID", "Nom", "Prenom", "Service"]:
            if col not in employes.columns:
                st.error(f"Colonne manquante dans le fichier des employés: {col}")
                return
        
        # Sélection d'employé adaptée au mobile
        if is_mobile():
            selected_name = st.selectbox("Sélectionnez un employé", 
                                      employes["Prenom"] + " " + employes["Nom"])
            selected_id = employes[(employes["Prenom"] + " " + employes["Nom"]) == selected_name]["ID"].iloc[0]
        else:
            selected_id = st.selectbox("Sélectionnez un employé", 
                                    employes["ID"].astype(str) + " - " + employes["Prenom"] + " " + employes["Nom"] + " (" + employes["Service"] + ")")
            selected_id = int(selected_id.split(" - ")[0])
        
        employe = employes[employes["ID"] == selected_id].iloc[0]
        st.info(f"Service: {employe['Service']} - Heure d'entrée officielle: {employe['Heure_Entree']} - Heure de sortie officielle: {employe['Heure_Sortie']}")
        
        # Boutons adaptés au mobile
        if is_mobile():
            if st.button("🟢 Enregistrer l'arrivée", use_container_width=True):
                pointer(selected_id, "Entrée")
            if st.button("🔴 Enregistrer la sortie", use_container_width=True):
                pointer(selected_id, "Sortie")
        else:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🟢 Enregistrer l'arrivée", use_container_width=True):
                    pointer(selected_id, "Entrée")
            with col2:
                if st.button("🔴 Enregistrer la sortie", use_container_width=True):
                    pointer(selected_id, "Sortie")
        
        st.subheader("Derniers pointages")
        pointages = load_data(POINTAGE_FILE)
        if not pointages.empty:
            st.dataframe(pointages.tail(5).sort_index(ascending=False), use_container_width=True)
    
    elif menu == "Gestion du Personnel":
        st.header("Gestion du Personnel")
        
        # Onglets adaptés au mobile
        if is_mobile():
            tab = st.radio("Options", ["Ajouter Employé", "Modifier Employé", "Supprimer Employé"])
        else:
            tab1, tab2, tab3 = st.tabs(["Ajouter Employé", "Modifier Employé", "Supprimer Employé"])
        
        if not is_mobile() or tab == "Ajouter Employé":
            if not is_mobile():
                with tab1:
                    with st.form("ajout_form"):
                        nom = st.text_input("Nom")
                        prenom = st.text_input("Prénom")
                        service = st.selectbox("Service", SERVICES_DISPONIBLES)
                        
                        if is_mobile():
                            heure_entree = st.time_input("Heure d'entrée", value=HEURE_ENTREE_DEFAUT)
                            heure_sortie = st.time_input("Heure de sortie", value=HEURE_SORTIE_DEFAUT)
                        else:
                            col1, col2 = st.columns(2)
                            with col1:
                                heure_entree = st.time_input("Heure d'entrée", value=HEURE_ENTREE_DEFAUT)
                            with col2:
                                heure_sortie = st.time_input("Heure de sortie", value=HEURE_SORTIE_DEFAUT)
                        
                        if st.form_submit_button("Ajouter", use_container_width=True):
                            if nom and prenom:
                                ajouter_employe(nom, prenom, service, heure_entree, heure_sortie)
                            else:
                                st.error("Veuillez remplir tous les champs")
            else:
                with st.form("ajout_form"):
                    nom = st.text_input("Nom")
                    prenom = st.text_input("Prénom")
                    service = st.selectbox("Service", SERVICES_DISPONIBLES)
                    heure_entree = st.time_input("Heure d'entrée", value=HEURE_ENTREE_DEFAUT)
                    heure_sortie = st.time_input("Heure de sortie", value=HEURE_SORTIE_DEFAUT)
                    
                    if st.form_submit_button("Ajouter", use_container_width=True):
                        if nom and prenom:
                            ajouter_employe(nom, prenom, service, heure_entree, heure_sortie)
                        else:
                            st.error("Veuillez remplir tous les champs")
        
        if not is_mobile() or tab == "Modifier Employé":
            employes = load_data(EMPLOYES_FILE)
            if employes.empty:
                st.warning("Aucun employé à modifier")
            else:
                if not is_mobile():
                    with tab2:
                        selected = st.selectbox("Employé à modifier", 
                                             employes["ID"].astype(str) + " - " + employes["Prenom"] + " " + employes["Nom"])
                        selected_id = int(selected.split(" - ")[0])
                        employe = employes[employes["ID"] == selected_id].iloc[0]
                        
                        with st.form("modif_form"):
                            new_nom = st.text_input("Nom", value=employe["Nom"])
                            new_prenom = st.text_input("Prénom", value=employe["Prenom"])
                            
                            try:
                                index_service = SERVICES_DISPONIBLES.index(employe["Service"])
                            except ValueError:
                                index_service = 0
                            
                            new_service = st.selectbox("Service", SERVICES_DISPONIBLES, index=index_service)
                            
                            if is_mobile():
                                new_heure_entree = st.time_input("Heure d'entrée", value=str_to_time(employe["Heure_Entree"]))
                                new_heure_sortie = st.time_input("Heure de sortie", value=str_to_time(employe["Heure_Sortie"]))
                            else:
                                col1, col2 = st.columns(2)
                                with col1:
                                    new_heure_entree = st.time_input("Heure d'entrée", value=str_to_time(employe["Heure_Entree"]))
                                with col2:
                                    new_heure_sortie = st.time_input("Heure de sortie", value=str_to_time(employe["Heure_Sortie"]))
                            
                            if st.form_submit_button("Modifier", use_container_width=True):
                                modifier_employe(selected_id, new_nom, new_prenom, new_service, 
                                               new_heure_entree, new_heure_sortie)
                else:
                    selected = st.selectbox("Employé à modifier", 
                                         employes["Prenom"] + " " + employes["Nom"])
                    selected_id = employes[(employes["Prenom"] + " " + employes["Nom"]) == selected]["ID"].iloc[0]
                    employe = employes[employes["ID"] == selected_id].iloc[0]
                    
                    with st.form("modif_form"):
                        new_nom = st.text_input("Nom", value=employe["Nom"])
                        new_prenom = st.text_input("Prénom", value=employe["Prenom"])
                        
                        try:
                            index_service = SERVICES_DISPONIBLES.index(employe["Service"])
                        except ValueError:
                            index_service = 0
                        
                        new_service = st.selectbox("Service", SERVICES_DISPONIBLES, index=index_service)
                        new_heure_entree = st.time_input("Heure d'entrée", value=str_to_time(employe["Heure_Entree"]))
                        new_heure_sortie = st.time_input("Heure de sortie", value=str_to_time(employe["Heure_Sortie"]))
                        
                        if st.form_submit_button("Modifier", use_container_width=True):
                            modifier_employe(selected_id, new_nom, new_prenom, new_service, 
                                           new_heure_entree, new_heure_sortie)
        
        if not is_mobile() or tab == "Supprimer Employé":
            employes = load_data(EMPLOYES_FILE)
            if employes.empty:
                st.warning("Aucun employé à supprimer")
            else:
                if not is_mobile():
                    with tab3:
                        to_delete = st.selectbox("Employé à supprimer", 
                                              employes["ID"].astype(str) + " - " + employes["Prenom"] + " " + employes["Nom"])
                        if st.button("Supprimer", use_container_width=True):
                            supprimer_employe(int(to_delete.split(" - ")[0]))
                else:
                    to_delete = st.selectbox("Employé à supprimer", 
                                          employes["Prenom"] + " " + employes["Nom"])
                    if st.button("Supprimer", use_container_width=True):
                        selected_id = employes[(employes["Prenom"] + " " + employes["Nom"]) == to_delete]["ID"].iloc[0]
                        supprimer_employe(selected_id)
        
        st.subheader("Liste des Employés")
        employes = load_data(EMPLOYES_FILE)
        st.dataframe(employes, use_container_width=True)
    
    elif menu == "Historique":
        st.header("Historique des Pointages")
        
        employes = load_data(EMPLOYES_FILE)
        
        if is_mobile():
            selected_service = st.selectbox("Filtrer par service", ["Tous"] + SERVICES_DISPONIBLES)
            date_filter = st.date_input("Filtrer par date")
        else:
            col1, col2 = st.columns(2)
            with col1:
                selected_service = st.selectbox("Filtrer par service", ["Tous"] + SERVICES_DISPONIBLES)
            with col2:
                date_filter = st.date_input("Filtrer par date")
        
        pointages = load_data(POINTAGE_FILE)
        if not pointages.empty:
            if selected_service != "Tous":
                pointages = pointages[pointages["Service"] == selected_service]
            if date_filter:
                pointages = pointages[pointages["Date"] == date_filter.strftime("%Y-%m-%d")]
            
            st.dataframe(pointages.sort_values(by=["Date", "Heure"], ascending=False), use_container_width=True)
        else:
            st.warning("Aucun pointage enregistré")
    
    elif menu == "Retards":
        st.header("Historique des Retards")
        
        employes = load_data(EMPLOYES_FILE)
        
        if is_mobile():
            selected_service = st.selectbox("Filtrer les retards par service", ["Tous"] + SERVICES_DISPONIBLES)
            date_filter = st.date_input("Filtrer les retards par date")
        else:
            col1, col2 = st.columns(2)
            with col1:
                selected_service = st.selectbox("Filtrer les retards par service", ["Tous"] + SERVICES_DISPONIBLES)
            with col2:
                date_filter = st.date_input("Filtrer les retards par date")
        
        retards = load_data(RETARDS_FILE)
        if not retards.empty:
            if selected_service != "Tous":
                retards = retards[retards["Service"] == selected_service]
            if date_filter:
                retards = retards[retards["Date"] == date_filter.strftime("%Y-%m-%d")]
            
            st.dataframe(retards.sort_values(by=["Date", "Heure_Arrivee"], ascending=False), use_container_width=True)
            
            # Statistiques
            st.subheader("Statistiques des Retards")
            if is_mobile():
                st.metric("Nombre total de retards", len(retards))
                avg_retard = retards["Retard_min"].mean()
                st.metric("Retard moyen (min)", round(avg_retard, 1))
                max_retard = retards["Retard_min"].max()
                st.metric("Retard maximum (min)", max_retard)
            else:
                cols = st.columns(3)
                with cols[0]:
                    st.metric("Nombre total de retards", len(retards))
                with cols[1]:
                    avg_retard = retards["Retard_min"].mean()
                    st.metric("Retard moyen (min)", round(avg_retard, 1))
                with cols[2]:
                    max_retard = retards["Retard_min"].max()
                    st.metric("Retard maximum (min)", max_retard)
        else:
            st.info("Aucun retard enregistré")
    
    elif menu == "Statistiques":
        st.header("Statistiques des Employés")
        
        employes = load_data(EMPLOYES_FILE)
        pointages = load_data(POINTAGE_FILE)
        retards = load_data(RETARDS_FILE)
        
        if not employes.empty:
            st.subheader("Répartition par service")
            service_counts = employes["Service"].value_counts()
            st.bar_chart(service_counts)
            
            if not pointages.empty:
                st.subheader("Heures travaillées")
                if is_mobile():
                    selected_emp = st.selectbox("Sélectionner un employé", 
                                             employes["Prenom"] + " " + employes["Nom"])
                    selected_id = employes[(employes["Prenom"] + " " + employes["Nom"]) == selected_emp]["ID"].iloc[0]
                else:
                    selected_emp = st.selectbox("Sélectionner un employé", 
                                             employes["ID"].astype(str) + " - " + employes["Prenom"] + " " + employes["Nom"])
                    selected_id = int(selected_emp.split(" - ")[0])
                
                selected_date = st.date_input("Sélectionner une date", datetime.now())
                
                heures = calculer_heures_travaillees(selected_id, selected_date)
                st.metric("Heures travaillées ce jour", f"{heures.seconds//3600}h{(heures.seconds//60)%60}m")

if __name__ == "__main__":
    main()