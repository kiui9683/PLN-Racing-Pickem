import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import bcrypt

@st.cache_resource
def get_db():
    if not firebase_admin._apps:
        if "firebase" in st.secrets:
            # Load from Streamlit secrets
            cred = credentials.Certificate(dict(st.secrets["firebase"]))
            firebase_admin.initialize_app(cred)
        else:
            try:
                # Load from local file during development if secrets are not set
                cred = credentials.Certificate("firebase_credentials.json")
                firebase_admin.initialize_app(cred)
            except Exception:
                return None
    return firestore.client()

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# --- AUTHENTICATION ---
def create_user(username, password, role="user"):
    db = get_db()
    if not db: return False, "No database connection. Please provide Firebase credentials."
    
    # Check if user already exists
    doc = db.collection("users").document(username).get()
    if doc.exists:
        return False, "Username already exists."
    
    db.collection("users").document(username).set({
        "username": username,
        "password": hash_password(password),
        "role": role,
        "created_at": firestore.SERVER_TIMESTAMP
    })
    return True, "Account created successfully!"

def authenticate_user(username, password):
    db = get_db()
    if not db: return False, None
    doc = db.collection("users").document(username).get()
    if not doc.exists:
        return False, None
    user_data = doc.to_dict()
    if check_password(password, user_data.get("password", "")):
        return True, user_data
    return False, None

def update_user_role(username, new_role):
    db = get_db()
    if not db: return False
    db.collection("users").document(username).update({
        "role": new_role
    })
    return True

def delete_user(username):
    db = get_db()
    if not db: return False
    db.collection("users").document(username).delete()
    return True

# --- RACES ---
def get_all_races():
    db = get_db()
    if not db: return []
    try:
        docs = db.collection("races").order_by("order").stream()
        return [{**doc.to_dict(), "id": doc.id} for doc in docs]
    except Exception as e:
        st.error(f"Error fetching races: {e}")
        return []

def add_race(name, racetrack, distance, surface, order):
    db = get_db()
    if not db: return False
    db.collection("races").add({
        "name": name,
        "racetrack": racetrack,
        "distance": distance,
        "surface": surface,
        "order": order,
        "locked": False,
        "results": {} # e.g. {"1": horse_id_A, "2": horse_id_B}
    })
    return True

def delete_race(race_id):
    db = get_db()
    if not db: return False
    # delete horses associated first conceptually, but we'll just delete the race
    db.collection("races").document(race_id).delete()
    return True

def toggle_race_lock(race_id, lock_status):
    db = get_db()
    if not db: return False
    db.collection("races").document(race_id).update({
        "locked": lock_status
    })
    return True

def set_race_results(race_id, results_dict):
    db = get_db()
    if not db: return False
    db.collection("races").document(race_id).update({
        "results": results_dict
    })
    return True

# --- HORSES / ENTRIES ---
def get_horses_for_race(race_id):
    db = get_db()
    if not db: return []
    docs = db.collection("horses").where("race_id", "==", race_id).stream()
    return [{**doc.to_dict(), "id": doc.id} for doc in docs]

def add_horse_to_race(race_id, umamusume, trainer, horse_img_url, trainer_img_url, stats_img_url):
    db = get_db()
    if not db: return False
    db.collection("horses").add({
        "race_id": race_id,
        "umamusume": umamusume,
        "trainer": trainer,
        "horse_img_url": horse_img_url,
        "trainer_img_url": trainer_img_url,
        "stats_img_url": stats_img_url
    })
    return True

def delete_horse(horse_id):
    db = get_db()
    if not db: return False
    db.collection("horses").document(horse_id).delete()
    return True

# --- PICKS ---
def get_user_picks(username):
    db = get_db()
    if not db: return {}
    docs = db.collection("picks").where("username", "==", username).stream()
    return {doc.to_dict()["race_id"]: doc.to_dict()["horse_id"] for doc in docs}

def make_pick(username, race_id, horse_id):
    db = get_db()
    if not db: return False
    pick_id = f"{username}_{race_id}"
    db.collection("picks").document(pick_id).set({
        "username": username,
        "race_id": race_id,
        "horse_id": horse_id,
        "timestamp": firestore.SERVER_TIMESTAMP
    })
    return True

def get_all_picks():
    db = get_db()
    if not db: return []
    docs = db.collection("picks").stream()
    return [doc.to_dict() for doc in docs]
    
# --- SETTINGS / LEADERBOARD ---
def get_points_config():
    db = get_db()
    if not db: return {"1": 10, "2": 5, "3": 3}
    doc = db.collection("settings").document("points").get()
    if doc.exists:
        return doc.to_dict()
    return {"1": 10, "2": 5, "3": 3}

def update_points_config(config_dict):
    db = get_db()
    if not db: return False
    db.collection("settings").document("points").set(config_dict)
    return True

def get_all_users():
    db = get_db()
    if not db: return []
    docs = db.collection("users").stream()
    return [{**doc.to_dict(), "id": doc.id} for doc in docs]
