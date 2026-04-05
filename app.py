import streamlit as st
import firebase_db as db
from PIL import Image
import requests
from io import BytesIO
import pandas as pd

st.set_page_config(page_title="PLN Racing Festival Pick'em", page_icon="🏇", layout="wide")

# PREMIUM CUSTOM CSS
st.markdown("""
<style>
    /* Base aesthetic adjustments */
    .stApp {
        background-color: #0e1117;
    }
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        background: -webkit-linear-gradient(45deg, #FFD700, #FFA500);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    hr {
        border-color: rgba(255, 255, 255, 0.1);
    }
    .stButton>button {
        background-color: #1f2937 !important;
        color: #fff !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }
    .stButton>button:hover {
        border-color: #FFA500 !important;
        box-shadow: 0 0 10px rgba(255, 165, 0, 0.5) !important;
    }
    .locked-race {
        color: #fca5a5;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def load_image_from_url(url, width=None):
    if not url or pd.isna(url):
        return Image.new('RGB', (100, 100), color=(30, 34, 43))
    try:
        response = requests.get(url, timeout=5)
        img = Image.open(BytesIO(response.content))
        if width:
            ratio = width / img.width
            height = int(img.height * ratio)
            img = img.resize((width, height))
        return img
    except Exception:
        return Image.new('RGB', (100, 100), color=(30, 34, 43))

# --- SESSION STATE ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'role' not in st.session_state:
    st.session_state.role = None
if 'page' not in st.session_state:
    st.session_state.page = "Login"

# --- PAGES ---
def login_page():
    st.markdown("<h1 style='text-align: center;'>🏇 PLN Racing Festival</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: white;'>Welcome to the Pick'em Challenge</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            l_username = st.text_input("Username", key="l_user")
            l_password = st.text_input("Password", type="password", key="l_pass")
            if st.button("Login", use_container_width=True):
                if l_username and l_password:
                    with st.spinner("Authenticating..."):
                        success, user_data = db.authenticate_user(l_username, l_password)
                        if success:
                            st.session_state.user = l_username
                            st.session_state.role = user_data.get("role", "user")
                            st.session_state.page = "My Picks"
                            st.rerun()
                        else:
                            st.error("Invalid username or password.")
                            
        with tab2:
            s_username = st.text_input("Choose Username", key="s_user")
            s_password = st.text_input("Choose Password", type="password", key="s_pass")
            s_admin_code = st.text_input("Admin Code (Optional)", type="password") # Secret logic to create admin
            if st.button("Create Account", use_container_width=True):
                if s_username and s_password:
                    with st.spinner("Creating account..."):
                        role = "admin" if s_admin_code == "PLN2026ADMIN" else "user"
                        success, msg = db.create_user(s_username, s_password, role)
                        if success:
                            st.success(msg + " You can now log in.")
                        else:
                            st.error(msg)
                else:
                    st.warning("Please fill out all fields.")

def admin_page():
    if st.session_state.role != "admin":
        st.warning("Unauthorized access.")
        return
        
    st.title("🛠️ Admin Panel")
    st.caption("Manage the entire Pick'em site from here.")
    
    tabs = st.tabs(["Races", "Entries (Horses)", "Operations", "Points Config"])
    
    # 1. RACES
    with tabs[0]:
        st.subheader("Add a New Race")
        with st.form("add_race_form"):
            r_name = st.text_input("Race Name")
            r_track = st.text_input("Racetrack")
            col1, col2 = st.columns(2)
            r_dist = col1.text_input("Distance (e.g. 1200m)")
            r_surf = col2.selectbox("Surface", ["Turf", "Dirt"])
            r_order = st.number_input("Race Order Number", min_value=1, value=1)
            
            if st.form_submit_button("Add Race"):
                if db.add_race(r_name, r_track, r_dist, r_surf, r_order):
                    st.success("Race added successfully.")
                else:
                    st.error("Failed to add race. Check DB connection.")
        
        st.markdown("---")
        st.subheader("Existing Races")
        races = db.get_all_races()
        if races:
            for r in races:
                col1, col2 = st.columns([4,1])
                col1.markdown(f"**Race {r.get('order')}: {r.get('name')}** - {r.get('racetrack')} | Locked: {r.get('locked')}")
                if col2.button("Delete", key=f"del_race_{r['id']}"):
                    db.delete_race(r['id'])
                    st.rerun()

    # 2. ENTRIES
    with tabs[1]:
        st.subheader("Add Horse to Race")
        races = db.get_all_races()
        if not races:
            st.info("Please create a race first.")
        else:
            race_options = {r['id']: f"Race {r.get('order')}: {r.get('name')}" for r in races}
            selected_race_id = st.selectbox("Select Race", options=list(race_options.keys()), format_func=lambda x: race_options[x])
            
            with st.form("add_horse_form"):
                h_trainer = st.text_input("Trainer Name")
                h_uma = st.text_input("Umamusume Name")
                h_img = st.text_input("Horse Image URL")
                h_timg = st.text_input("Trainer Image URL")
                h_simg = st.text_input("Stats Image URL")
                
                if st.form_submit_button("Add Entry"):
                    if db.add_horse_to_race(selected_race_id, h_uma, h_trainer, h_img, h_timg, h_simg):
                        st.success("Horse added successfully!")
                    else:
                        st.error("Failed to add. Check DB.")
            
            st.markdown("---")
            st.subheader("Entries in Selected Race")
            horses = db.get_horses_for_race(selected_race_id)
            for h in horses:
                col1, col2 = st.columns([4,1])
                col1.write(f"**{h.get('umamusume')}** (Trainer: {h.get('trainer')})")
                if col2.button("Delete Entry", key=f"del_h_{h['id']}"):
                    db.delete_horse(h['id'])
                    st.rerun()

    # 3. OPERATIONS
    with tabs[2]:
        st.subheader("Race Locks & Results")
        races = db.get_all_races()
        for r in races:
            with st.expander(f"Race {r.get('order')}: {r.get('name')}"):
                # Lock status
                is_locked = r.get('locked', False)
                lock_text = "Unlock Race" if is_locked else "Lock Race 🔒"
                if st.button(lock_text, key=f"lock_{r['id']}"):
                    db.toggle_race_lock(r['id'], not is_locked)
                    st.rerun()
                
                st.markdown("---")
                st.markdown("**Enter Results**")
                horses = db.get_horses_for_race(r['id'])
                if horses:
                    h_options = {h['id']: f"{h.get('umamusume')} ({h.get('trainer')})" for h in horses}
                    h_options[""] = "--- Select ---"
                    
                    form_key = f"results_form_{r['id']}"
                    with st.form(form_key):
                        first = st.selectbox("1st Place", options=list(h_options.keys()), format_func=lambda x: h_options[x], key=f"1st_{r['id']}")
                        second = st.selectbox("2nd Place", options=list(h_options.keys()), format_func=lambda x: h_options[x], key=f"2nd_{r['id']}")
                        third = st.selectbox("3rd Place", options=list(h_options.keys()), format_func=lambda x: h_options[x], key=f"3rd_{r['id']}")
                        
                        if st.form_submit_button("Save Results"):
                            res_dict = {}
                            if first: res_dict["1"] = first
                            if second: res_dict["2"] = second
                            if third: res_dict["3"] = third
                            db.set_race_results(r['id'], res_dict)
                            st.success("Results updated!")

    # 4. POINTS CONFIG
    with tabs[3]:
        st.subheader("Points Settings")
        pts = db.get_points_config()
        with st.form("points_form"):
            p1 = st.number_input("Points for 1st Place", value=int(pts.get("1", 10)))
            p2 = st.number_input("Points for 2nd Place", value=int(pts.get("2", 5)))
            p3 = st.number_input("Points for 3rd Place", value=int(pts.get("3", 3)))
            if st.form_submit_button("Update Points"):
                db.update_points_config({"1": p1, "2": p2, "3": p3})
                st.success("Points setup updated.")


def user_picks_page():
    st.title("🎯 My Picks")
    st.caption("Select one horse to win for each race. You may change your pick anytime until the Admin locks the race.")
    
    races = db.get_all_races()
    if not races:
        st.info("No races available yet.")
        return
        
    user_picks = db.get_user_picks(st.session_state.user)
    
    for r in races:
        is_locked = r.get("locked", False)
        lock_msg = "🔒 **LOCKED** - Picks can no longer be changed." if is_locked else "🟢 **OPEN**"
        
        with st.expander(f"Race {r.get('order')}: {r.get('name')} | {r.get('racetrack')} | {r.get('distance')} | {lock_msg}", expanded=True):
            horses = db.get_horses_for_race(r['id'])
            
            if not horses:
                st.write("No entries yet.")
                continue
                
            current_pick_id = user_picks.get(r['id'])
            
            # Show current pick prominently
            if current_pick_id:
                ch = next((h for h in horses if h['id'] == current_pick_id), None)
                if ch:
                    st.success(f"**Your Pick:** {ch.get('umamusume')} (Trained by {ch.get('trainer')})")
            else:
                st.warning("You have not made a pick for this race.")
                
            if not is_locked:
                st.markdown("---")
                # selection interface
                h_options = {h['id']: f"{h.get('umamusume')} (Trainer: {h.get('trainer')})" for h in horses}
                
                # pre-select if exists
                sel_index = list(h_options.keys()).index(current_pick_id) if current_pick_id in h_options else 0
                
                selected_h = st.radio("Select a Horse", options=list(h_options.keys()), format_func=lambda x: h_options[x], index=sel_index, key=f"radio_{r['id']}")
                if st.button("Save Pick", key=f"save_{r['id']}"):
                    if db.make_pick(st.session_state.user, r['id'], selected_h):
                        st.toast("Pick saved successfully!")
                        st.rerun()
            
            # Show Horse Detailed info
            st.markdown("#### The Field")
            cols = st.columns(min(len(horses), 4) if len(horses) > 0 else 1)
            for idx, h in enumerate(horses):
                c = cols[idx % 4]
                with c:
                    try:
                        img = load_image_from_url(h.get('horse_img_url'), width=100)
                        st.image(img, use_container_width=True)
                    except:
                        pass
                    st.markdown(f"**{h.get('umamusume')}**")
                    st.caption(f"Tr: {h.get('trainer')}")
                    
                    if st.button("Stats", key=f"st_{h['id']}"):
                        try:
                            st.image(load_image_from_url(h.get('stats_img_url'), width=300))
                        except:
                            st.caption("-")


def leaderboard_page():
    st.title("🏆 Leaderboard")
    st.caption("Ranking based on Official Race Results.")
    
    races = db.get_all_races()
    picks_list = db.get_all_picks()
    points_cfg = db.get_points_config()
    all_users = db.get_all_users()
    
    if not races:
        st.info("No races yet.")
        return
        
    scores = {u['username']: 0 for u in all_users}
    
    # Calculate scores
    for r in races:
        results = r.get("results", {})
        if not results:
            continue
            
        r_id = r['id']
        winner_id_1 = results.get("1")
        winner_id_2 = results.get("2")
        winner_id_3 = results.get("3")
        
        for pick in picks_list:
            if pick.get("race_id") == r_id:
                p_uid = pick.get("username")
                p_hid = pick.get("horse_id")
                
                if p_uid not in scores:
                    scores[p_uid] = 0
                    
                if p_hid == winner_id_1:
                    scores[p_uid] += int(points_cfg.get("1", 0))
                # Note: Currently users only pick ONE horse. So we only check if their pick won 1st.
                # If you want them to get points if their picked horse came 2nd/3rd, uncomment:
                elif p_hid == winner_id_2:
                    scores[p_uid] += int(points_cfg.get("2", 0))
                elif p_hid == winner_id_3:
                    scores[p_uid] += int(points_cfg.get("3", 0))
                    
    # Sort and display
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    st.markdown("---")
    for i, (uname, score) in enumerate(sorted_scores):
        if i == 0 and score > 0:
            st.markdown(f"### 🥇 1. **{uname}** - {score} pts")
        elif i == 1 and score > 0:
            st.markdown(f"### 🥈 2. **{uname}** - {score} pts")
        elif i == 2 and score > 0:
            st.markdown(f"### 🥉 3. **{uname}** - {score} pts")
        else:
            rank = i + 1
            st.markdown(f"**{rank}. {uname}** - {score} pts")
            
    st.markdown("---")
    st.markdown("### Point System")
    st.info(f"1st Place Pick = {points_cfg.get('1')} pts | 2nd Place Pick = {points_cfg.get('2')} pts | 3rd Place Pick = {points_cfg.get('3')} pts")


# --- MAIN APP LAYOUT ---
def main():
    if st.session_state.user:
        with st.sidebar:
            st.markdown("## Navigation")
            st.write(f"Hello, **{st.session_state.user}**!")
            st.markdown("---")
            
            if st.button("🎯 My Picks", use_container_width=True):
                st.session_state.page = "My Picks"
                st.rerun()
            if st.button("🏆 Leaderboard", use_container_width=True):
                st.session_state.page = "Leaderboard"
                st.rerun()
                
            if st.session_state.role == "admin":
                st.markdown("---")
                if st.button("🛠️ Admin Panel", use_container_width=True):
                    st.session_state.page = "Admin"
                    st.rerun()
                    
            st.markdown("---")
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.user = None
                st.session_state.role = None
                st.session_state.page = "Login"
                st.rerun()

    p = st.session_state.page
    if p == "Login":
        login_page()
    elif p == "Admin":
        admin_page()
    elif p == "My Picks":
        user_picks_page()
    elif p == "Leaderboard":
        leaderboard_page()

if __name__ == "__main__":
    main()