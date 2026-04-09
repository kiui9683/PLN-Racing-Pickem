import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import bcrypt

@st.cache_resource
def get_db():
    if not firebase_admin._apps:
        # 1. Try local firebase_credentials.toml first (for local scripts/dev)
        import os
        toml_path = "firebase_credentials.toml"
        if os.path.exists(toml_path):
            try:
                import tomllib
                with open(toml_path, "rb") as f:
                    config = tomllib.load(f)
                    if "firebase" in config:
                        cred = credentials.Certificate(config["firebase"])
                        firebase_admin.initialize_app(cred)
                        return firestore.client()
            except Exception as e:
                pass # Fallback to secrets or json

        # 2. Try Streamlit secrets
        try:
            if "firebase" in st.secrets:
                cred = credentials.Certificate(dict(st.secrets["firebase"]))
                firebase_admin.initialize_app(cred)
                return firestore.client()
        except Exception:
            pass

        # 3. Try local json during development
        try:
            cred = credentials.Certificate("firebase_credentials.json")
            firebase_admin.initialize_app(cred)
            return firestore.client()
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

def add_race(name, racetrack, distance, surface, order, group="Default"):
    db = get_db()
    if not db: return False
    db.collection("races").add({
        "name": name,
        "racetrack": racetrack,
        "distance": distance,
        "surface": surface,
        "order": order,
        "group": group,
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

def edit_race(race_id, name, racetrack, distance, surface, order, group):
    db = get_db()
    if not db: return False
    db.collection("races").document(race_id).update({
        "name": name,
        "racetrack": racetrack,
        "distance": distance,
        "surface": surface,
        "order": order,
        "group": group
    })
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

def clear_race_results(race_id):
    db = get_db()
    if not db: return False
    db.collection("races").document(race_id).update({
        "results": {}
    })
    return True

# --- TRAINERS ---
def get_all_trainers():
    db = get_db()
    if not db: return []
    try:
        docs = db.collection("trainers").stream()
        return [{**doc.to_dict(), "id": doc.id} for doc in docs]
    except Exception as e:
        st.error(f"Error fetching trainers: {e}")
        return []

def add_trainer(name, img_url, horses_dict):
    """
    horses_dict format:
    {
       "Sprint": [{"name": "U1", "img": "...", "stats": "..."}, {"name": "U2", "img": "...", "stats": "..."}],
       ...
    }
    """
    db = get_db()
    if not db: return False
    db.collection("trainers").add({
        "name": name,
        "img_url": img_url,
        "horses": horses_dict
    })
    return True

def delete_trainer(trainer_id):
    db = get_db()
    if not db: return False
    db.collection("trainers").document(trainer_id).delete()
    return True

def edit_trainer(trainer_id, name, img_url, horses_dict):
    db = get_db()
    if not db: return False
    db.collection("trainers").document(trainer_id).update({
        "name": name,
        "img_url": img_url,
        "horses": horses_dict
    })
    return True

# --- RACE ENTRIES ---
def get_entries_for_race(race_id):
    db = get_db()
    if not db: return []
    
    # 1. Fetch entry docs matching race_id
    entry_docs = db.collection("race_entries").where("race_id", "==", race_id).stream()
    entries = []
    
    # 2. Fetch all trainers for lookup (or could fetch individually, but roster is small)
    all_trainers = {t['id']: t for t in get_all_trainers()}
    
    for doc in entry_docs:
        data = doc.to_dict()
        trainer_id = data.get("trainer_id")
        horse_index = data.get("horse_index", 0) # 0 or 1
        division = data.get("division", "Unknown")
        
        trainer = all_trainers.get(trainer_id)
        if trainer:
            # Extract the specific horse
            horses_in_div = trainer.get("horses", {}).get(division, [])
            selected_horse = horses_in_div[horse_index] if len(horses_in_div) > horse_index else {}
            
            entries.append({
                "entry_id": doc.id,
                "trainer_id": trainer_id,
                "trainer_name": trainer.get("name"),
                "trainer_img_url": trainer.get("img_url"),
                "horse_index": horse_index,
                "umamusume": selected_horse.get("name"),
                "horse_img_url": selected_horse.get("img"),
                "stats_img_url": selected_horse.get("stats"),
                "division": division
            })
            
    return entries

def add_entry_to_race(race_id, trainer_id, horse_index, division):
    db = get_db()
    if not db: return False
    
    # Check if entry already exists (trainer can only have one entry per race)
    existing = list(db.collection("race_entries")
                    .where("race_id", "==", race_id)
                    .where("trainer_id", "==", trainer_id)
                    .stream())
    if existing: return True
    
    db.collection("race_entries").add({
        "race_id": race_id,
        "trainer_id": trainer_id,
        "horse_index": horse_index,
        "division": division
    })
    return True

def remove_entry_from_race(race_id, trainer_id):
    db = get_db()
    if not db: return False
    docs = db.collection("race_entries").where("race_id", "==", race_id).where("trainer_id", "==", trainer_id).stream()
    for doc in docs:
        doc.reference.delete()
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
