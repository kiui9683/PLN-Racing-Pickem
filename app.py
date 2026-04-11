import streamlit as st
import firebase_db as db
from PIL import Image
import requests
from io import BytesIO
import pandas as pd
import re

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

def get_division_from_distance(dist_str):
    dist_match = re.search(r'\d+', str(dist_str))
    dist_val = int(dist_match.group()) if dist_match else 0
    if dist_val < 1600: return 'Sprint'
    if dist_val < 2000: return 'Mile'
    if dist_val < 2500: return 'Medium'
    return 'Long'

# --- SESSION STATE ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'role' not in st.session_state:
    st.session_state.role = None
if 'page' not in st.session_state:
    st.session_state.page = "Login" if not st.session_state.user else "Pick'em"

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
                                st.session_state.page = "Pick'em"
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
                                st.session_state.page = "Pick'em"
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
    
    tabs_list = ["Races", "Horse Library", "Trainers (Roster)", "Entries (Races)", "Operations", "Points Config"]
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
            unique_groups_1 = sorted(list(set([r.get("group", "Default") for r in races])))
            filter_options_1 = ["All Groups"] + unique_groups_1
            selected_group_filter_1 = st.selectbox("Filter by Group:", options=filter_options_1, key="filter_races")

            for r in races:
                if selected_group_filter_1 != "All Groups" and r.get("group", "Default") != selected_group_filter_1:
                    continue
                with st.expander(f"Race {r.get('order')}: {r.get('name')} [{r.get('group', 'Default')}]"):
                    with st.form(f"edit_race_{r['id']}"):
                        e_name = st.text_input("Race Name", value=r.get('name', ''))
                        col0, col1 = st.columns(2)
                        e_track = col0.text_input("Racetrack", value=r.get('racetrack', ''))
                        e_group = col1.text_input("Race Group", value=r.get('group', 'Default'))
                        col2, col3 = st.columns(2)
                        e_dist = col2.text_input("Distance", value=r.get('distance', ''))
                        sel_idx = 0 if r.get('surface', 'Turf') == 'Turf' else 1
                        e_surf = col3.selectbox("Surface", ["Turf", "Dirt"], index=sel_idx)
                        e_order = st.number_input("Race Order Number", value=int(r.get('order', 1)))
                        
                        col_save, col_del = st.columns(2)
                        if col_save.form_submit_button("Save Changes"):
                            db.edit_race(r['id'], e_name, e_track, e_dist, e_surf, e_order, e_group)
                            st.success("Updated!")
                            st.rerun()
                        if col_del.form_submit_button("Delete Race"):
                            db.delete_race(r['id'])
                            st.rerun()

    # 2. HORSE LIBRARY
    with tabs[1]:
        st.subheader("Global Horse Library")
        st.write("Add horses to the central pool. These can be assigned to multiple trainers.")
        with st.form("add_to_library_form"):
            lh_name = st.text_input("Horse Name")
            lh_img = st.text_input("Horse Image URL")
            if st.form_submit_button("Add to Library"):
                if lh_name and lh_img:
                    if db.add_global_pool_horse(lh_name, lh_img):
                        st.success(f"{lh_name} added to library!")
                        st.rerun()
                else:
                    st.warning("Please provide both name and image URL.")
        
        st.markdown("---")
        lib_horses = db.get_global_pool_horses()
        if lib_horses:
            for lh in lib_horses:
                col1, col2 = st.columns([4, 1])
                col1.write(f"**{lh['name']}**")
                if col2.button("Delete", key=f"del_lib_{lh['id']}"):
                    db.delete_global_pool_horse(lh['id'])
                    st.rerun()
        else:
            st.info("No horses in library.")

    # 3. TRAINERS (ROSTER)
    with tabs[2]:
        st.subheader("Trainer Roster")
        st.write("Add and edit trainers. Select horses from the Library for each division.")
        
        lib_horses = db.get_global_pool_horses()
        if not lib_horses:
            st.warning("Please add horses to the Horse Library first.")
        else:
            lh_options = {lh['id']: lh['name'] for lh in lib_horses}
            lh_data = {lh['id']: lh for lh in lib_horses}
            
            with st.form("add_trainer_form"):
                t_name = st.text_input("Trainer Name")
                t_img = st.text_input("Trainer Image URL")
                
                st.markdown("#### Horse Roster (2 per division)")
                divisions = ["Sprint", "Mile", "Medium", "Long"]
                t_horses = {}
                
                for div in divisions:
                    st.markdown(f"**{div} Division**")
                    colA, colB = st.columns(2)
                    h_list = []
                    for i in range(2):
                        with (colA if i == 0 else colB):
                            st.write(f"Slot {i+1}")
                            lh_id = st.selectbox("Select Horse", options=list(lh_options.keys()), format_func=lambda x: lh_options[x], key=f"add_{div}_{i}_lh")
                            hs = st.text_input(f"Unique Stats URL", key=f"add_{div}_{i}_stats")
                            
                            chosen_lh = lh_data[lh_id]
                            h_list.append({
                                "name": chosen_lh['name'], 
                                "img": chosen_lh['image_url'], 
                                "stats": hs, 
                                "horse_id": lh_id
                            })
                    t_horses[div] = h_list
                
                if st.form_submit_button("Add Trainer"):
                    if t_name:
                        if db.add_trainer(t_name, t_img, t_horses):
                            st.success("Trainer added!")
                            st.rerun()
                        else:
                            st.error("Failed to add.")
                    else:
                        st.warning("Trainer name is required.")
        
        st.markdown("---")
        st.subheader("Existing Trainers")
        all_trainers = db.get_all_trainers()
        for t in all_trainers:
            with st.expander(f"Tr: {t.get('name')}"):
                with st.form(f"edit_trainer_{t['id']}"):
                    e_name = st.text_input("Trainer Name", value=t.get('name'))
                    e_img = st.text_input("Trainer Image", value=t.get('img_url'))
                    
                    e_horses = {}
                    for div in ["Sprint", "Mile", "Medium", "Long"]:
                        st.markdown(f"**{div} Division**")
                        colA, colB = st.columns(2)
                        h_list = t.get("horses", {}).get(div, [])
                        # Ensure we have data even if lib changed
                        while len(h_list) < 2: h_list.append({"name":"", "img":"", "stats":"", "horse_id":""})
                        
                        new_h_list = []
                        for i in range(2):
                            with (colA if i == 0 else colB):
                                st.write(f"Slot {i+1}")
                                curr_h_id = h_list[i].get("horse_id", "")
                                
                                # Find index in current library or append if missing
                                lib_ids = list(lh_options.keys())
                                if curr_h_id in lib_ids:
                                    sel_idx = lib_ids.index(curr_h_id)
                                else:
                                    sel_idx = 0
                                
                                lh_id_edit = st.selectbox("Select Horse", options=lib_ids, format_func=lambda x: lh_options[x], index=sel_idx, key=f"edit_{t['id']}_{div}_{i}_lh")
                                hs = st.text_input(f"Unique Stats URL", value=h_list[i].get("stats", ""), key=f"edit_{t['id']}_{div}_{i}_stats")
                                
                                chosen_lh = lh_data[lh_id_edit]
                                new_h_list.append({
                                    "name": chosen_lh['name'], 
                                    "img": chosen_lh['image_url'], 
                                    "stats": hs, 
                                    "horse_id": lh_id_edit
                                })
                        e_horses[div] = new_h_list
                        
                    col_save, col_del = st.columns(2)
                    if col_save.form_submit_button("Save Changes"):
                        db.edit_trainer(t['id'], e_name, e_img, e_horses)
                        st.success("Updated!")
                        st.rerun()
                    if col_del.form_submit_button("Delete Trainer"):
                        db.delete_trainer(t['id'])
                        st.rerun()

    # 4. ENTRIES (RACES)
    with tabs[3]:
        st.subheader("Assign Trainer Entries to Races")
        races = db.get_all_races()
        if not races:
            st.info("Please create a race first.")
        else:
            race_options = {r['id']: f"[{r.get('group', 'Default')}] Race {r.get('order')}: {r.get('name')}" for r in races}
            selected_race_id = st.selectbox("Select Race", options=list(race_options.keys()), format_func=lambda x: race_options[x])
            
            sel_race = next((rt for rt in races if rt['id'] == selected_race_id), None)
            req_div = get_division_from_distance(sel_race.get('distance', '0')) if sel_race else "Unknown"
            if sel_race:
                st.info(f"**Race Distance**: {sel_race.get('distance', '0')} ➡️ **Required Division**: {req_div}")
            
            curr_entries = db.get_entries_for_race(selected_race_id)
            current_trainer_ids = [e['trainer_id'] for e in curr_entries]
            
            with st.form("add_race_entry_form"):
                all_trainers = db.get_all_trainers()
                available_trainers = [t for t in all_trainers if t['id'] not in current_trainer_ids]
                
                if not available_trainers:
                    st.warning("No more trainers available to add.")
                    st.form_submit_button("Assign Trainer", disabled=True)
                else:
                    t_options = {t['id']: t.get('name') for t in available_trainers}
                    t_choose = st.selectbox("Select Trainer", options=list(t_options.keys()), format_func=lambda x: t_options[x])
                    
                    # Horse selection for that trainer and division
                    st.markdown(f"**Select Horse from {req_div} Roster**")
                    trainer_obj = next(to for to in available_trainers if to['id'] == t_choose)
                    h_roster = trainer_obj.get("horses", {}).get(req_div, [])
                    while len(h_roster) < 2: h_roster.append({"name": f"Unknown {len(h_roster)+1}"})
                    
                    # Add placeholder option
                    h_options_radio = [0, 1, -1]
                    def format_h_choice(i):
                        if i == -1: return "None / Placeholder"
                        return h_roster[i].get("name", f"Horse {i+1}")
                    
                    h_choice = st.radio("Choose Horse", options=h_options_radio, format_func=format_h_choice)
                    
                    if st.form_submit_button("Assign Trainer & Horse"):
                        if db.add_entry_to_race(selected_race_id, t_choose, h_choice, req_div):
                            st.success("Trainer entered!")
                            st.rerun()

            st.markdown("---")
            with st.expander("⚡ Bulk Entry by Race Group"):
                st.write("Add multiple trainers to all races in a group at once. Horses will be set to 'TBD / Placeholder'.")
                all_tr = db.get_all_trainers()
                if all_tr:
                    unique_grps = sorted(list(set([r.get("group", "Default") for r in races])))
                    
                    bulk_t_ids = st.multiselect("Select Trainers", options=[t['id'] for t in all_tr], format_func=lambda x: next(t['name'] for t in all_tr if t['id'] == x))
                    bulk_group = st.selectbox("Select Race Group", options=unique_grps)
                    
                    if st.button("Bulk Enter Trainers"):
                        if not bulk_t_ids:
                            st.warning("Please select at least one trainer.")
                        else:
                            races_in_grp = [r for r in races if r.get("group", "Default") == bulk_group]
                            if not races_in_grp:
                                st.warning(f"No races found in group '{bulk_group}'.")
                            else:
                                for r in races_in_grp:
                                    r_div = get_division_from_distance(r.get('distance', '0'))
                                    for t_id in bulk_t_ids:
                                        db.add_entry_to_race(r['id'], t_id, -1, r_div)
                                st.success(f"Processed {len(bulk_t_ids)} trainers for all races in {bulk_group}.")
                                st.rerun()
                else:
                    st.info("No trainers available.")
            
            st.markdown("---")
            st.subheader("Current Entries in Race")
            if not curr_entries:
                st.write("No entries yet.")
            for ent in curr_entries:
                col1, col2 = st.columns([4,1])
                col1.write(f"**{ent.get('umamusume')}** (Trainer: {ent.get('trainer_name')})")
                if col2.button("Remove Entry", key=f"rm_ent_{ent['trainer_id']}_{selected_race_id}"):
                    db.remove_entry_from_race(selected_race_id, ent['trainer_id'])
                    st.rerun()

    # 5. OPERATIONS
    with tabs[4]:
        st.subheader("Race Locks & Results")
        races = db.get_all_races()
        if races:
            unique_groups_2 = sorted(list(set([r.get("group", "Default") for r in races])))
            filter_options_2 = ["All Groups"] + unique_groups_2
            selected_group_filter_2 = st.selectbox("Filter by Group:", options=filter_options_2, key="filter_ops")
            
            from collections import defaultdict
            grp_races = defaultdict(list)
            for r in races: 
                if selected_group_filter_2 != "All Groups" and r.get("group", "Default") != selected_group_filter_2:
                    continue
                grp_races[r.get("group", "Default")].append(r)
            
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
                        entries = db.get_entries_for_race(r['id'])
                        if entries:
                            h_options = {e['trainer_id']: f"{e.get('umamusume')} ({e.get('trainer_name')})" for e in entries}
                            h_options[""] = "--- Select ---"
                            pts_cfg = db.get_points_config()
                            
                            form_key = f"results_form_{r['id']}"
                            with st.form(form_key):
                                res_inputs = {}
                                sorted_placements = sorted(pts_cfg.keys(), key=lambda x: int(x) if x.isdigit() else x)
                                max_places = min(len(entries), len(sorted_placements))
                                for place in sorted_placements[:max_places]:
                                    # Sort entry options alphabetically by trainer/horse name for results
                                    h_keys = sorted(list(h_options.keys()), key=lambda x: h_options[x].lower())
                                    res_inputs[place] = st.selectbox(f"{place} Place", options=h_keys, format_func=lambda x: h_options[x], key=f"{place}_{r['id']}")
                                
                                col_s, col_c = st.columns(2)
                                if col_s.form_submit_button("Save Results"):
                                    res_dict = {place: tid for place, tid in res_inputs.items() if tid}
                                    
                                    # Validate duplicates
                                    values = list(res_dict.values())
                                    if len(values) != len(set(values)):
                                        st.error("Validation Error: A trainer cannot be assigned to multiple placements.")
                                    else:
                                        db.set_race_results(r['id'], res_dict)
                                        st.success("Results updated!")
                                        st.rerun()
                                        
                                if col_c.form_submit_button("Clear Results"):
                                    db.clear_race_results(r['id'])
                                    st.success("Results cleared!")
                                    st.rerun()

    # 6. POINTS CONFIG
    with tabs[5]:
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

    # 7. USERS (Admin Only)
    if st.session_state.role == "admin" and len(tabs) > 6:
        with tabs[6]:
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
    st.title("🎯 Pick'em")
    st.caption("Select one trainer/horse to win for each race. You may change your pick anytime until the Admin locks the race.")
    
    races = db.get_all_races()
    if not races:
        st.info("No races available yet.")
        return
        
    user_picks = db.get_user_picks(st.session_state.user)
    points_cfg = db.get_points_config()
    
    unique_groups = sorted(list(set([r.get("group", "Default") for r in races])))
    filter_options = ["All Groups"] + unique_groups
    selected_group_filter = st.selectbox("🎯 Filter Picks by Group:", options=filter_options)
    st.markdown("---")
    
    from collections import defaultdict
    grouped_races = defaultdict(list)
    for r in races:
        if selected_group_filter != "All Groups" and r.get("group", "Default") != selected_group_filter:
            continue
        grouped_races[r.get("group", "Default")].append(r)
        
    for group_name, group_races in grouped_races.items():
        st.markdown(f"<h2 style='text-align: center; color: #FBBF24; margin-top: 30px;'>🚩 {group_name}</h2>", unsafe_allow_html=True)
        
        for r in group_races:
            is_locked = r.get("locked", False)
            lock_msg = "🔒 **LOCKED**" if is_locked else "🟢 **OPEN**"
            
            with st.expander(f"Race {r.get('order')}: {r.get('name')} | {r.get('racetrack')} | {r.get('distance')} | {lock_msg}", expanded=True):
                entries = db.get_entries_for_race(r['id'])
                
                if not entries:
                    st.write("No entries yet.")
                    continue
                    
                current_pick_tid = user_picks.get(r['id'])
                race_results = r.get("results", {}) # { "1": trainer_id }
                results_inv = {v: k for k, v in race_results.items()}
                
                # Show current pick prominently
                if current_pick_tid:
                    centry = next((e for e in entries if e['trainer_id'] == current_pick_tid), None)
                    if centry:
                        st.success(f"**Your Pick:** {centry.get('umamusume')} (Trained by {centry.get('trainer_name')})")
                else:
                    st.warning("You have not made a pick for this race.")
                    
                st.markdown("#### The Field")
                for e in entries:
                    with st.container():
                        col_himg, col_timg, col_name, col_stats, col_btn = st.columns([1, 1, 3, 1, 2])
                        with col_himg:
                            try:
                                img = load_image_from_url(e.get('horse_img_url'), width=60)
                                st.image(img, width=60)
                            except:
                                st.write("🏇")
                        with col_timg:
                            try:
                                timg = load_image_from_url(e.get('trainer_img_url'), width=60)
                                st.image(timg, width=60)
                            except:
                                pass
                        with col_name:
                            st.markdown(f"**{e.get('umamusume')}**")
                            st.caption(f"Tr: {e.get('trainer_name')}")
                        with col_stats:
                            if e['trainer_id'] in results_inv:
                                place = results_inv[e['trainer_id']]
                                pts = points_cfg.get(place, 0)
                                st.markdown(f"<div style='text-align:center;'><b>🏆 {place}</b><br>{pts} pts</div>", unsafe_allow_html=True)
                            elif e.get('stats_img_url'):
                                with st.popover("Stats"):
                                    try:
                                        simg = load_image_from_url(e.get('stats_img_url'), width=300)
                                        st.image(simg, use_container_width=True)
                                    except:
                                        st.write("No stats available.")
                        with col_btn:
                            if not is_locked:
                                btn_label = "✅ Selected" if e['trainer_id'] == current_pick_tid else "Select"
                                is_disabled = e['trainer_id'] == current_pick_tid
                                if st.button(btn_label, disabled=is_disabled, key=f"sel_{r['id']}_{e['trainer_id']}"):
                                    if db.make_pick(st.session_state.user, r['id'], e['trainer_id']):
                                        st.toast("Pick saved successfully!", icon="✅")
                                        st.rerun()
                            elif e['trainer_id'] == current_pick_tid:
                                st.info("Locked In")
                    st.markdown("---")


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
        user_breakdowns = {u['username']: [] for u in all_users}
        
        # Calculate scores
        for r in races:
            if selected_group_filter != "Total (All Races)" and r.get("group", "Default") != selected_group_filter:
                continue
                
            results = r.get("results", {})
            if not results:
                continue
                
            r_id = r['id']
            race_name = f"[{r.get('group', 'Default')}] {r.get('name', 'Unknown Race')}"
            entries = db.get_entries_for_race(r_id)
            
            for pick in picks_list:
                if pick.get("race_id") == r_id:
                    p_uid = pick.get("username")
                    p_tid = pick.get("horse_id") # horse_id field in DB now stores trainer_id
                    
                    if p_uid not in scores:
                        scores[p_uid] = 0
                        user_breakdowns[p_uid] = []
                        
                    for place, winner_tid in results.items():
                        if p_tid == winner_tid:
                            pts = int(points_cfg.get(place, 0))
                            scores[p_uid] += pts
                            
                            winning_e = next((e for e in entries if e['trainer_id'] == winner_tid), None)
                            h_name = winning_e.get('umamusume', 'Unknown') if winning_e else 'Unknown'
                            t_name = winning_e.get('trainer_name', 'Unknown Trainer') if winning_e else 'Unknown Trainer'
                            
                            user_breakdowns[p_uid].append({
                                'race': race_name,
                                'horse': h_name,
                                'trainer': t_name,
                                'place': place,
                                'pts': pts
                            })
                        
        # Sort and display
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        st.markdown("---")
        for i, (uname, score) in enumerate(sorted_scores):
            col1, col2 = st.columns([4, 1])
            with col1:
                if i == 0 and score > 0:
                    st.markdown(f"### 🥇 1. **{uname}** - {score} pts")
                elif i == 1 and score > 0:
                    st.markdown(f"### 🥈 2. **{uname}** - {score} pts")
                elif i == 2 and score > 0:
                    st.markdown(f"### 🥉 3. **{uname}** - {score} pts")
                else:
                    rank = i + 1
                    st.markdown(f"**{rank}. {uname}** - {score} pts")
            with col2:
                with st.popover("Breakdown"):
                    if not user_breakdowns.get(uname):
                        st.write("No points scored yet.")
                    else:
                        for bdoc in user_breakdowns[uname]:
                            st.markdown(f"**{bdoc['race']}**<br/>{bdoc['horse']} (Tr: {bdoc['trainer']}) *({bdoc['place']})* ➡️ **+{bdoc['pts']}**", unsafe_allow_html=True)
                            st.markdown("---")
                
    with tab_trainers:
        trainer_scores = {}
        trainer_breakdowns = {}
        
        for r in races:
            if selected_group_filter != "Total (All Races)" and r.get("group", "Default") != selected_group_filter:
                continue
                
            results = r.get("results", {})
            if not results:
                continue
            r_id = r['id']
            race_name = f"[{r.get('group', 'Default')}] {r.get('name', 'Unknown Race')}"
            entries = db.get_entries_for_race(r_id)
            for place, winner_tid in results.items():
                winning_e = next((e for e in entries if e['trainer_id'] == winner_tid), None)
                if winning_e:
                    t_name = winning_e.get('trainer_name', 'Unknown Trainer')
                    h_name = winning_e.get('umamusume', 'Unknown')
                    
                    if t_name not in trainer_scores:
                        trainer_scores[t_name] = 0
                        trainer_breakdowns[t_name] = []
                        
                    pts = int(points_cfg.get(place, 0))
                    trainer_scores[t_name] += pts
                    trainer_breakdowns[t_name].append({
                        'race': race_name,
                        'horse': h_name,
                        'trainer': t_name,
                        'place': place,
                        'pts': pts
                    })
                    
        sorted_t_scores = sorted(trainer_scores.items(), key=lambda x: x[1], reverse=True)
        
        st.markdown("---")
        if not sorted_t_scores:
            st.info(f"No trainer points awarded yet for '{selected_group_filter}'.")
        else:
            for i, (tname, score) in enumerate(sorted_t_scores):
                col1, col2 = st.columns([4,1])
                with col1:
                    if i == 0 and score > 0:
                        st.markdown(f"### 🥇 1. **{tname}** - {score} pts")
                    elif i == 1 and score > 0:
                        st.markdown(f"### 🥈 2. **{tname}** - {score} pts")
                    elif i == 2 and score > 0:
                        st.markdown(f"### 🥉 3. **{tname}** - {score} pts")
                    else:
                        rank = i + 1
                        st.markdown(f"**{rank}. {tname}** - {score} pts")
                with col2:
                    with st.popover("Breakdown"):
                        if not trainer_breakdowns.get(tname):
                            st.write("No points scored yet.")
                        else:
                            for bdoc in trainer_breakdowns[tname]:
                                st.markdown(f"**{bdoc['race']}**<br/>{bdoc['horse']} (Tr: {bdoc['trainer']}) *({bdoc['place']})* ➡️ **+{bdoc['pts']}**", unsafe_allow_html=True)
                                st.markdown("---")
            
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
            
            if st.button("🎯 Pick'em", use_container_width=True):
                st.session_state.page = "Pick'em"
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
    elif p == "Pick'em":
        user_picks_page()
    elif p == "Leaderboard":
        leaderboard_page()

if __name__ == "__main__":
    main()