import cv2
import numpy as np
import face_recognition

def detect_faces(image):
    """Détecte les visages dans une image et retourne le premier visage trouvé"""
    try:
        # Convertir en RGB (face_recognition utilise RGB)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Détecter les visages
        face_locations = face_recognition.face_locations(rgb_image)
        
        if len(face_locations) > 0:
            # Retourner le premier visage
            top, right, bottom, left = face_locations[0]
            return rgb_image[top:bottom, left:right]
        return None
    except Exception as e:
        print(f"Error in face detection: {e}")
        return None

def get_face_embedding(face_image):
    """Extrait les caractéristiques faciales (embedding) d'une image de visage"""
    try:
        # Calculer l'embedding facial
        embeddings = face_recognition.face_encodings(face_image)
        
        if len(embeddings) > 0:
            return embeddings[0]
        return None
    except Exception as e:
        print(f"Error in face embedding: {e}")
        return None

def compare_faces(embedding1, embedding2, threshold=0.6):
    """Compare deux embeddings faciaux et retourne si c'est la même personne"""
    if embedding1 is None or embedding2 is None:
        return False
    
    distance = np.linalg.norm(embedding1 - embedding2)
    return distance < threshold