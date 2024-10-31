import streamlit as st
import requests
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from streamlit_drawable_canvas import st_canvas
import base64
from io import BytesIO
from PIL import Image

API_URL = "http://localhost:5000/api"

def format_time(seconds):
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes} min {seconds} sec"

def add_participant_ui():
    if 'participant_data' not in st.session_state:
        st.session_state['participant_data'] = None

    if 'rerun' not in st.session_state:
        st.session_state['rerun'] = False

    if st.session_state['rerun']:
        st.session_state['rerun'] = False
        st.rerun()

    if st.session_state['participant_data'] is None:
        st.title("Add Participant")
        gender = st.selectbox("Gender", ["Male", "Female"])
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        
        if st.button("Add Participant"):
            st.session_state['participant_data'] = {
                "gender": gender,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone,
                "time": None
            }
            st.session_state['rerun'] = True
            st.rerun()
    else:
        st.title("Datenschutzrichtlinie")
        st.write("Please read and accept the data security policy.")
        accept_policy = st.checkbox("I read and accept the data security policy")
        
        st.write("Please sign below:")
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",  # Fixed fill color with some opacity
            stroke_width=2,
            stroke_color="#000000",
            background_color="#FFFFFF",
            height=150,
            width=400,
            drawing_mode="freedraw",
            key="canvas",
        )

        if st.button("Accept") and accept_policy:
            if canvas_result.image_data is not None:
                # Convert the image to base64
                img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()

                st.session_state['participant_data']['timestamp'] = datetime.now().isoformat()
                st.session_state['participant_data']['signature'] = img_str

                response = requests.post(f"{API_URL}/participant", json=st.session_state['participant_data'])
                if response.status_code == 201:
                    st.success("Participant added successfully")
                    st.session_state['participant_data'] = None
                else:
                    st.error("Failed to add participant")

def main_screen():
    st.title("Participants")
    search = st.text_input("Search by name")
    page = st.number_input("Page", min_value=0)
    
    response = requests.get(f"{API_URL}/participants", params={"page": page, "per_page": 20, "search": search})
    participants = response.json()
    
    for participant in participants:
        time_value = participant['time'] if participant['time'] is not None else 0
        with st.expander(f"{participant['last_name']}, {participant['first_name']} - {format_time(time_value)}"):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("Edit", key=f"edit_{participant['_id']}"):
                    st.write("Edit functionality not implemented yet.")
            
            with col2:
                if st.button("Delete", key=f"delete_{participant['_id']}"):
                    response = requests.delete(f"{API_URL}/participant/{participant['_id']}")
                    if response.status_code == 200:
                        st.success("Participant deleted successfully")
                    else:
                        st.error("Failed to delete participant")
            
            stopwatch_key = f"stopwatch_{participant['_id']}"
            if stopwatch_key not in st.session_state:
                st.session_state[stopwatch_key] = None

            timer_placeholder = st.empty()
            
            with col3:
                if st.button("Start Stopwatch", key=f"start_{participant['_id']}"):
                    st.session_state[stopwatch_key] = time.time()
            
            with col4:
                if st.button("Stop Stopwatch", key=f"stop_{participant['_id']}"):
                    if st.session_state[stopwatch_key] is not None:
                        elapsed_time = time.time() - st.session_state[stopwatch_key]
                        st.session_state[stopwatch_key] = None
                        # Send the elapsed time to the API
                        response = requests.post(f"{API_URL}/participant/{participant['_id']}/time", json={"time": elapsed_time})
                        if response.status_code == 200:
                            st.success("Time updated successfully")
                            st.session_state['ranking_update'] = True  # Set flag to update ranking
                        else:
                            st.error("Failed to update time")
            
            if st.session_state[stopwatch_key] is not None:
                start_time = st.session_state[stopwatch_key]
                while st.session_state[stopwatch_key] is not None:
                    elapsed_time = time.time() - start_time
                    timer_placeholder.write(f"Elapsed Time: {format_time(elapsed_time)}")
                    time.sleep(0.1)

def ranking_ui():
    # Automatically refresh every 3 seconds
    st_autorefresh(interval=3 * 1000, key="ranking_refresh")

    try:
        response = requests.get(f"{API_URL}/participants")
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
        participants = response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching participants: {e}")
        participants = []

    participants = [p for p in participants if p["time"] is not None]

    women = sorted([p for p in participants if p["gender"] == "Female"], key=lambda x: x["time"], reverse=True)[:5]
    men = sorted([p for p in participants if p["gender"] == "Male"], key=lambda x: x["time"], reverse=True)[:5]
    all_participants = sorted(participants, key=lambda x: x["time"], reverse=True)[:5]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.header("Top Frauen")
        for rank, participant in enumerate(women, start=1):
            time_value = participant['time'] if participant['time'] is not None else 0
            st.write(f"{rank}. {participant['first_name']} {participant['last_name'][0]}* - {format_time(time_value)}")

    with col2:
        st.header("Top Männer")
        for rank, participant in enumerate(men, start=1):
            time_value = participant['time'] if participant['time'] is not None else 0
            st.write(f"{rank}. {participant['first_name']} {participant['last_name'][0]}* - {format_time(time_value)}")

    with col3:
        st.header("Top Alle")
        for rank, participant in enumerate(all_participants, start=1):
            time_value = participant['time'] if participant['time'] is not None else 0
            st.write(f"{rank}. {participant['first_name']} {participant['last_name'][0]}* - {format_time(time_value)}")

if __name__ == "__main__":
    st.sidebar.title("Navigation")
    app_mode = st.sidebar.selectbox("Choose the app mode", ["Ranking", "Add Participant", "Main Screen"])
    
    if app_mode == "Add Participant":
        add_participant_ui()
    elif app_mode == "Main Screen":
        main_screen()
    elif app_mode == "Ranking":
        ranking_ui()