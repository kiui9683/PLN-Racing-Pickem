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
        color: #FBBF24; /* Solid premium gold to preserve native emoji colors */
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
            with st.form("login_form"):
                l_username = st.text_input("Username", key="l_user")
                l_password = st.text_input("Password", type="password", key="l_pass")
                if st.form_submit_button("Login", use_container_width=True):
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
            with st.form("signup_form"):
                s_username = st.text_input("Choose Username", key="s_user")
                s_password = st.text_input("Choose Password", type="password", key="s_pass")
                if st.form_submit_button("Create Account", use_container_width=True):
                    if s_username and s_password:
                        with st.spinner("Creating account..."):
                            success, msg = db.create_user(s_username, s_password, "user")
                            if success:
                                st.session_state.user = s_username
                                st.session_state.role = "user"
                                st.session_state.page = "My Picks"
                                st.success("Account created! Logging in...")
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        st.warning("Please fill out all fields.")

def admin_page():
    if st.session_state.role not in ["admin", "manager"]:
        st.warning("Unauthorized access.")
        return
        
    st.title("🛠️ Management Panel")
    st.caption("Manage the entire Pick'em site from here.")
    
    tabs_list = ["Races", "Entries (Horses)", "Operations", "Points Config"]
    if st.session_state.role == "admin":
        tabs_list.append("Users")
    
    tabs = st.tabs(tabs_list)
    
    # 1. RACES
    with tabs[0]:
        st.subheader("Add a New Race")
        with st.form("add_race_form"):
            r_name = st.text_input("Race Name")
            col0, col1 = st.columns(2)
            r_track = col0.text_input("Racetrack")
            r_group = col1.text_input("Race Group", placeholder="e.g. Group A, Final")
            col2, col3 = st.columns(2)
            r_dist = col2.text_input("Distance (e.g. 1200m)")
            r_surf = col3.selectbox("Surface", ["Turf", "Dirt"])
            r_order = st.number_input("Race Order Number", min_value=1, value=1)
            
            if st.form_submit_button("Add Race"):
                grp = r_group if r_group else "Default"
                if db.add_race(r_name, r_track, r_dist, r_surf, r_order, grp):
                    st.success("Race added successfully.")
                else:
                    st.error("Failed to add race. Check DB connection.")
        
        st.markdown("---")
        st.subheader("Existing Races")
        races = db.get_all_races()
        if races:
            for r in races:
                col1, col2 = st.columns([4,1])
                grp_label = f" [{r.get('group')}]" if r.get('group') and r.get('group') != "Default" else ""
                col1.markdown(f"**Race {r.get('order')}: {r.get('name')}**{grp_label} - {r.get('racetrack')} | Locked: {r.get('locked')}")
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
            race_options = {r['id']: f"[{r.get('group', 'Default')}] Race {r.get('order')}: {r.get('name')}" for r in races}
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
        from collections import defaultdict
        
        grp_races = defaultdict(list)
        for r in races: grp_races[r.get("group", "Default")].append(r)
        
        for g_name, r_list in grp_races.items():
            st.markdown(f"#### {g_name}")
            for r in r_list:
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
                        pts_cfg = db.get_points_config()
                        
                        form_key = f"results_form_{r['id']}"
                        with st.form(form_key):
                            res_inputs = {}
                            sorted_placements = sorted(pts_cfg.keys(), key=lambda x: int(x) if x.isdigit() else x)
                            for place in sorted_placements:
                                res_inputs[place] = st.selectbox(f"{place} Place", options=list(h_options.keys()), format_func=lambda x: h_options[x], key=f"{place}_{r['id']}")
                            
                            if st.form_submit_button("Save Results"):
                                res_dict = {place: hid for place, hid in res_inputs.items() if hid}
                                db.set_race_results(r['id'], res_dict)
                                st.success("Results updated!")

    # 4. POINTS CONFIG
    with tabs[3]:
        st.subheader("Points Settings")
        pts = db.get_points_config()
        
        st.write("Current Settings:")
        with st.form("points_form"):
            new_pts = {}
            for place, point_val in sorted(pts.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0]):
                new_pts[place] = st.number_input(f"Points for {place} Place", value=int(point_val))
            if st.form_submit_button("Update Existing Points"):
                db.update_points_config(new_pts)
                st.success("Points setup updated.")
                st.rerun()
                
        st.markdown("---")
        st.subheader("Add or Remove Placements")
        col1, col2 = st.columns(2)
        with col1:
            with st.form("add_point_form"):
                new_p_name = st.text_input("New Placement Name (e.g., '4', 'Last')")
                new_p_val = st.number_input("Points", value=1)
                submit_add = st.form_submit_button("Add Placement")
                if submit_add and new_p_name:
                    pts[new_p_name] = new_p_val
                    db.update_points_config(pts)
                    st.success(f"Added {new_p_name}")
                    st.rerun()
        with col2:
            with st.form("del_point_form"):
                delete_place = st.selectbox("Delete Placement", options=[""] + list(pts.keys()))
                submit_del = st.form_submit_button("Delete")
                if submit_del and delete_place in pts:
                    del pts[delete_place]
                    db.update_points_config(pts)
                    st.success(f"Deleted {delete_place}")
                    st.rerun()

    # 5. USERS (Admin Only)
    if st.session_state.role == "admin" and len(tabs) > 4:
        with tabs[4]:
            st.subheader("User Management")
            users = db.get_all_users()
            for u in sorted(users, key=lambda x: x['role']):
                with st.expander(f"👤 {u['username']} (Role: {u['role']})"):
                    col_role, col_del = st.columns(2)
                    with col_role:
                        new_role = st.selectbox("Role", ["user", "manager", "admin"], index=["user", "manager", "admin"].index(u['role']), key=f"role_{u['username']}")
                        if st.button("Update Role", key=f"btn_role_{u['username']}"):
                            db.update_user_role(u['username'], new_role)
                            st.success("Role updated.")
                            st.rerun()
                    with col_del:
                        if st.button("Delete User", key=f"del_user_{u['username']}"):
                            if u['username'] == st.session_state.user:
                                st.error("Cannot delete yourself!")
                            else:
                                db.delete_user(u['username'])
                                st.success("User deleted.")
                                st.rerun()


def user_picks_page():
    st.title("🎯 My Picks")
    st.caption("Select one horse to win for each race. You may change your pick anytime until the Admin locks the race.")
    
    races = db.get_all_races()
    if not races:
        st.info("No races available yet.")
        return
        
    user_picks = db.get_user_picks(st.session_state.user)
    
    from collections import defaultdict
    grouped_races = defaultdict(list)
    for r in races:
        grouped_races[r.get("group", "Default")].append(r)
        
    for group_name, group_races in grouped_races.items():
        st.markdown(f"<h2 style='text-align: center; color: #FBBF24; margin-top: 30px;'>🚩 {group_name}</h2>", unsafe_allow_html=True)
        
        for r in group_races:
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
    st.title("🏆 Leaderboards")
    st.caption("Rankings based on Official Race Results.")
    
    races = db.get_all_races()
    picks_list = db.get_all_picks()
    points_cfg = db.get_points_config()
    all_users = db.get_all_users()
    
    if not races:
        st.info("No races yet.")
        return
        
    unique_groups = sorted(list(set([r.get("group", "Default") for r in races])))
    filter_options = ["Total (All Races)"] + unique_groups
    
    # Filter selection
    selected_group_filter = st.selectbox("📊 Filter Leaderboard Data:", options=filter_options)
    
    tab_users, tab_trainers = st.tabs(["👤 User Pick'em", "🏇 Trainer Standings"])
        
    with tab_users:
        scores = {u['username']: 0 for u in all_users}
        
        # Calculate scores
        for r in races:
            if selected_group_filter != "Total (All Races)" and r.get("group", "Default") != selected_group_filter:
                continue
                
            results = r.get("results", {})
            if not results:
                continue
                
            r_id = r['id']
            
            for pick in picks_list:
                if pick.get("race_id") == r_id:
                    p_uid = pick.get("username")
                    p_hid = pick.get("horse_id")
                    
                    if p_uid not in scores:
                        scores[p_uid] = 0
                        
                    for place, winner_hid in results.items():
                        if p_hid == winner_hid:
                            scores[p_uid] += int(points_cfg.get(place, 0))
                        
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
                
    with tab_trainers:
        trainer_scores = {}
        for r in races:
            if selected_group_filter != "Total (All Races)" and r.get("group", "Default") != selected_group_filter:
                continue
                
            results = r.get("results", {})
            if not results:
                continue
            r_id = r['id']
            horses = db.get_horses_for_race(r_id)
            for place, winner_hid in results.items():
                winning_h = next((h for h in horses if h['id'] == winner_hid), None)
                if winning_h:
                    t_name = winning_h.get('trainer', 'Unknown Trainer')
                    if t_name not in trainer_scores:
                        trainer_scores[t_name] = 0
                    trainer_scores[t_name] += int(points_cfg.get(place, 0))
                    
        sorted_t_scores = sorted(trainer_scores.items(), key=lambda x: x[1], reverse=True)
        
        st.markdown("---")
        if not sorted_t_scores:
            st.info(f"No trainer points awarded yet for '{selected_group_filter}'.")
        else:
            for i, (tname, score) in enumerate(sorted_t_scores):
                if i == 0 and score > 0:
                    st.markdown(f"### 🥇 1. **{tname}** - {score} pts")
                elif i == 1 and score > 0:
                    st.markdown(f"### 🥈 2. **{tname}** - {score} pts")
                elif i == 2 and score > 0:
                    st.markdown(f"### 🥉 3. **{tname}** - {score} pts")
                else:
                    rank = i + 1
                    st.markdown(f"**{rank}. {tname}** - {score} pts")
            
    st.markdown("---")
    st.markdown("### Point System")
    point_str = " | ".join([f"{k} Place = {v} pts" for k, v in sorted(points_cfg.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0])])
    st.info(point_str)


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
                
            if st.session_state.role in ["admin", "manager"]:
                st.markdown("---")
                if st.button("🛠️ Management Panel", use_container_width=True):
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