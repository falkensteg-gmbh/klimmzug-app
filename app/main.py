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

st.set_page_config(
    page_title="FalkenSteg Euromasters",
    #page_icon="🧊",
    layout='wide',
    initial_sidebar_state="collapsed" #, #expanded
    #menu_items={
    #    'Get Help': 'https://www.extremelycoolapp.com/help',
    #    'Report a bug': "https://www.extremelycoolapp.com/bug",
    #    'About': "# This is a header. This is an *extremely* cool app!"
    #}
)

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
        st.title("Datenschutzerklärung FalkenSteg")
        
        # Read the Datenschutzerklärung text from the file
        with open("app/datenschutzerklaerung.txt", "r") as file:
            datenschutz_text = file.read()
        
        # Display the Datenschutzerklärung text with Markdown formatting
        st.markdown(datenschutz_text)

        accept_policy = st.checkbox("**Hiermit bestaetige ich dass ich dieses Dokument vollstaendig gelesen und verstanden habe:**")

        st.write("Bitte unterzeichnen Sie hier:")
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",  # Fixed fill color with some opacity
            stroke_width=2,
            stroke_color="#000000",
            background_color="#FFFFFF",
            height=300,
            width=600,
            drawing_mode="freedraw",
            key="canvas",
        )

        if st.button("Akzeptieren") and accept_policy:
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

    women = sorted([p for p in participants if p["gender"] == "Female"], key=lambda x: x["time"], reverse=True)[:10]
    men = sorted([p for p in participants if p["gender"] == "Male"], key=lambda x: x["time"], reverse=True)[:10]
    all_participants = sorted(participants, key=lambda x: x["time"], reverse=True)[:10]

    col1, col2, col3, col4, col5 = st.columns([3, 3, 3, 3, 3])

    with col1:
        st.header("Frauen")
        for rank, participant in enumerate(women, start=1):
            time_value = participant['time'] if participant['time'] is not None else 0
            st.markdown(f"<p style='font-size:20px; margin-bottom: 10px;'>{rank}. {participant['first_name']} {participant['last_name'][0]}* - {format_time(time_value)}</p>", unsafe_allow_html=True)

    with col2:
        st.header("Männer")
        for rank, participant in enumerate(men, start=1):
            time_value = participant['time'] if participant['time'] is not None else 0
            st.markdown(f"<p style='font-size:20px; margin-bottom: 10px;'>{rank}. {participant['first_name']} {participant['last_name'][0]}* - {format_time(time_value)}</p>", unsafe_allow_html=True)

    with col3:
        st.header("Alle")
        for rank, participant in enumerate(all_participants, start=1):
            time_value = participant['time'] if participant['time'] is not None else 0
            st.markdown(f"<p style='font-size:20px; margin-bottom: 10px;'>{rank}. {participant['first_name']} {participant['last_name'][0]}* - {format_time(time_value)}</p>", unsafe_allow_html=True)

#    with col4:
#        st.image("app/Klimmzug_EM.png", use_column_width=True)

    # Read the image file and encode it to base64
    with open("app/Klimmzug_EM.png", "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode()

    # Apply custom CSS to stretch the image from top to bottom and align it to the right
    st.markdown(
        f"""
        <style>
        header[data-testid="stHeader"] {{
            display: none;
        }}
        .logo {{
            position: fixed;
            top: 0;
            left: 0;
            height: 300px; /* Adjust the height as needed */
            margin: 50px 0px 0px 75px;
        }}
        .full-height-image {{
            position: fixed;
            top: 0;
            right: 0;
            height: 100vh;
            width: auto;
            margin: 0;
            padding: 0;
        }}
        </style>
        <svg class="logo" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
            <path d="M18.9967 6.57924H19.8784L19.6676 0.253429H0.153357V1.11604H0.59424C1.44654 1.04285 2.30443 1.16072 3.1054 1.46107C3.30775 1.59867 3.47888 1.77731 3.60768 1.98537C3.73648 2.19343 3.82006 2.42626 3.853 2.66874C4.00298 3.94084 4.06066 5.22214 4.02554 6.50258V18.9434C4.06595 20.294 4.00827 21.6458 3.853 22.9881C3.81316 23.2456 3.72122 23.4924 3.58279 23.7132C3.44436 23.934 3.26236 24.1243 3.0479 24.2724C2.34137 24.5999 1.56205 24.7385 0.785944 24.675H0V25.5376H11.7891V24.675H10.9264C10.1205 24.76 9.3074 24.6067 8.58779 24.2341C8.36931 24.0717 8.18795 23.8646 8.05574 23.6266C7.92353 23.3886 7.84351 23.1252 7.82104 22.8539C7.69262 21.5802 7.6414 20.2999 7.66768 19.0201V12.7134H10.0447C10.8967 12.6489 11.7528 12.7665 12.5558 13.0584C13.035 13.3446 13.3852 13.8047 13.5334 14.3428C13.7759 15.1832 13.8858 16.0563 13.8593 16.9306H14.7986V7.97861H13.8593C13.9916 9.07869 13.7191 10.1893 13.0926 11.1032C12.2084 11.7313 11.1208 12.0049 10.0447 11.87H7.62933V1.11604H12.5942C13.717 1.06294 14.8414 1.17925 15.9296 1.46107C16.7426 1.78781 17.4191 2.38315 17.8465 3.14797C18.5049 4.18183 18.9059 5.35846 19.0158 6.57924M27.642 18.4833H21.3737L24.4982 10.8156L27.642 18.4833ZM27.642 25.6143H34.6579V25.0392C34.1571 25.0225 33.6716 24.8628 33.2586 24.5791C32.9309 24.3261 32.6789 23.9879 32.5301 23.6015L31.725 21.6846L25.7826 7.57605H25.265L20.1085 19.9019L19.4759 21.4162C19.158 22.3889 18.6925 23.307 18.0957 24.1382C17.6235 24.6154 17 24.9136 16.3322 24.9817V25.5759H21.6229V25.0392C21.123 25.0545 20.6317 24.9064 20.2235 24.6175C20.0415 24.476 19.8972 24.2917 19.8036 24.081C19.71 23.8703 19.6698 23.6397 19.6868 23.4098C19.8596 22.297 20.2023 21.2174 20.7027 20.2085L21.1628 19.0776H27.9103L29.2714 22.3747C29.5421 22.9221 29.7418 23.5018 29.8656 24.0999C29.879 24.2549 29.8438 24.4102 29.7648 24.5442C29.6857 24.6782 29.5669 24.7842 29.4247 24.8475C28.857 25.0027 28.2683 25.0674 27.6803 25.0392L27.642 25.6143ZM50.3 25.6143L50.415 20.3811H49.8016C49.5516 21.4784 49.1104 22.5231 48.4981 23.4673C48.1332 24.0253 47.6136 24.465 47.0029 24.7325C46.2121 24.9583 45.39 25.0554 44.5684 25.02H43.2265C42.5759 25.063 41.9234 24.9716 41.3096 24.7517C41.164 24.6779 41.0368 24.5725 40.9373 24.4431C40.8378 24.3137 40.7685 24.1637 40.7345 24.0041C40.6294 23.2035 40.591 22.3956 40.6195 21.5887V12.2917C40.595 11.3504 40.6398 10.4085 40.7537 9.47381C40.7851 9.30825 40.8507 9.15108 40.9465 9.01242C41.0422 8.87376 41.1659 8.7567 41.3096 8.66871C41.8596 8.49002 42.4387 8.41844 43.0157 8.45784H43.8016V7.78691H35.2905V8.38115H35.6739C36.2651 8.33257 36.8599 8.41099 37.4183 8.61117C37.5602 8.71248 37.6806 8.84086 37.7728 8.9889C37.8649 9.13694 37.9268 9.30174 37.955 9.47381C38.0578 10.3837 38.0962 11.2997 38.07 12.215V20.9178C38.0969 21.865 38.0585 22.8129 37.955 23.7549C37.9249 23.9361 37.8585 24.1093 37.7596 24.2642C37.6608 24.419 37.5316 24.5522 37.3799 24.6558C36.8912 24.8906 36.3483 24.9899 35.8081 24.9433H35.2905V25.5376L50.3 25.6143ZM62.3766 25.6143H71.597V25.0392C70.9247 25.0494 70.2622 24.8772 69.68 24.5408C68.5862 23.6964 67.5665 22.7601 66.6321 21.7421L59.9804 15.0329L63.22 12.0425C64.466 10.854 65.3286 10.1255 65.7887 9.72299C66.2546 9.35651 66.7711 9.05951 67.3222 8.84122C67.8455 8.62203 68.4039 8.49866 68.9708 8.477V7.78691H62.2807V8.38115C63.5587 8.38115 64.1977 8.76455 64.1977 9.53131C64.1977 10.0105 63.5651 10.8156 62.2807 11.9275L56.8558 16.8156V12.215C56.8233 11.273 56.8746 10.33 57.0092 9.39711C57.0335 9.23157 57.0943 9.07349 57.1871 8.93427C57.2799 8.79504 57.4025 8.67815 57.5459 8.59201C58.1023 8.41229 58.6879 8.34071 59.2712 8.38115H59.5779V7.78691H51.7185V8.38115C52.365 8.33341 53.0147 8.40488 53.6354 8.59201C53.778 8.67916 53.8999 8.79634 53.9926 8.93538C54.0853 9.07442 54.1465 9.23198 54.1721 9.39711C54.2966 10.3309 54.3415 11.2736 54.3063 12.215V20.9178C54.3332 21.865 54.2948 22.8129 54.1913 23.7549C54.1612 23.9361 54.0948 24.1093 53.9959 24.2642C53.8971 24.419 53.7679 24.5522 53.6162 24.6558C53.1275 24.8906 52.5846 24.9899 52.0444 24.9433H51.4885V25.5376H59.4629V25.0392H59.137C58.5736 25.0933 58.0068 24.9799 57.5076 24.7133C57.3581 24.598 57.2335 24.4537 57.1412 24.289C57.049 24.1242 56.991 23.9426 56.9709 23.7549C56.8694 22.8449 56.8309 21.9289 56.8558 21.0136V17.7549L58.1402 16.6431L63.1433 21.7037C64.4085 22.9689 65.0603 23.7932 65.0603 24.1574C65.0573 24.2823 65.0222 24.4043 64.9584 24.5118C64.8946 24.6192 64.8043 24.7084 64.696 24.7708C64.0872 25.0099 63.4289 25.0955 62.7791 25.02H62.4341L62.3766 25.6143ZM87.1432 25.6143L87.5266 20.0935H86.894C86.6684 21.1953 86.2323 22.2432 85.6096 23.1798C85.1774 23.8177 84.5815 24.3275 83.8844 24.6558C83.1462 24.9164 82.3667 25.0398 81.5841 25.02H80.2614C79.0729 25.02 78.3445 24.8283 78.0761 24.4641C77.6898 23.2649 77.5528 21.9994 77.6736 20.7453V16.5472H79.5905C80.1382 16.5174 80.6873 16.5691 81.2199 16.7006C81.3788 16.7503 81.5248 16.8345 81.6474 16.9472C81.77 17.0598 81.8662 17.1982 81.9292 17.3524C82.1365 17.9689 82.2212 18.6202 82.1783 19.2693H82.8109V13.1926H82.1783C82.2144 13.7848 82.1628 14.3791 82.025 14.9562C81.9664 15.1119 81.8742 15.2527 81.7549 15.3687C81.6356 15.4847 81.4922 15.5729 81.3349 15.6271C80.7539 15.8157 80.1427 15.8937 79.533 15.8572H77.6161V8.40034H80.0697C80.9756 8.37449 81.8817 8.44515 82.7726 8.61117C83.3509 8.76003 83.8593 9.10574 84.2103 9.58882C84.7302 10.3918 85.0823 11.2916 85.2454 12.2342H85.8588L85.4371 7.80607H72.7471V8.40034C73.321 8.35572 73.8975 8.44087 74.434 8.64952C74.5783 8.75368 74.6979 8.88846 74.784 9.04422C74.8702 9.19997 74.9208 9.37285 74.9324 9.55047C75.0327 10.4413 75.0711 11.338 75.0474 12.2342V20.937C75.0683 21.8582 75.0363 22.7798 74.9516 23.6973C74.8927 24.0456 74.7169 24.3634 74.4532 24.5983C73.9426 24.9106 73.3407 25.0391 72.7471 24.9625H72.3829V25.5568L87.1432 25.6143ZM106.427 8.89873C106.979 8.63242 107.579 8.48236 108.191 8.45784V7.78691H101.75V8.38115C102.362 8.36949 102.971 8.46019 103.552 8.64952C103.96 8.7684 104.308 9.03496 104.53 9.39711C104.735 9.92764 104.821 10.4973 104.779 11.0649V21.6846L94.2358 7.78691H89.0026V8.38115C89.6478 8.3368 90.2959 8.40162 90.9195 8.57285C91.0799 8.67083 91.2176 8.80184 91.3233 8.9572C91.4291 9.11255 91.5005 9.28867 91.5329 9.47381C91.6812 10.3796 91.739 11.2978 91.7054 12.215V21.6271C91.7329 22.3065 91.6944 22.987 91.5904 23.659C91.4433 24.0195 91.1613 24.3083 90.8045 24.4641C90.2091 24.7643 89.5542 24.9281 88.8876 24.9433V25.5376H95.5201V25.0392C94.7945 25.0849 94.0692 24.9464 93.4115 24.6366C93.0217 24.4544 92.714 24.1331 92.5489 23.7357C92.4192 23.0731 92.3677 22.3975 92.3955 21.7229V9.39711L104.951 26.036H105.507V11.3524C105.485 10.8026 105.55 10.2527 105.699 9.72299C105.863 9.36106 106.158 9.07384 106.523 8.91788M129.181 24.2532C129.896 23.5751 130.459 22.7527 130.833 21.8406C131.206 20.9285 131.382 19.9475 131.347 18.9626C131.369 17.6969 131.058 16.4478 130.446 15.3396C129.881 14.3287 129.062 13.4829 128.069 12.8859C126.526 12.0192 124.939 11.2322 123.315 10.5281C121.602 9.8632 120.004 8.93161 118.581 7.76775C118.152 7.40154 117.81 6.9454 117.578 6.43185C117.346 5.9183 117.23 5.35995 117.239 4.79652C117.25 3.80316 117.625 2.84844 118.293 2.11281C118.724 1.67465 119.246 1.33741 119.823 1.12528C120.4 0.913154 121.016 0.831421 121.629 0.885987C123.185 0.878783 124.684 1.4768 125.807 2.55373C127.081 3.78989 127.955 5.37874 128.319 7.11598H129.143V0.464263H128.319C128.234 1.28978 127.892 2.06781 127.341 2.6879C126.557 1.74301 125.558 1.00017 124.427 0.521797C123.456 0.171795 122.431 -0.00344223 121.399 0.00422053C120.526 -0.0270986 119.656 0.11614 118.84 0.425565C118.023 0.73499 117.277 1.20437 116.645 1.80613C116.022 2.38069 115.529 3.08135 115.198 3.86143C114.868 4.64151 114.707 5.48309 114.728 6.33006C114.724 7.49746 115.021 8.64606 115.59 9.66548C116.164 10.7128 116.995 11.5969 118.006 12.2342C119.484 13.1019 121.021 13.8641 122.606 14.5153C124.302 15.1996 125.871 16.1653 127.245 17.3715C127.666 17.7894 127.997 18.2889 128.218 18.8394C128.439 19.39 128.545 19.9798 128.529 20.5728C128.526 21.2098 128.395 21.8397 128.145 22.4255C127.894 23.0114 127.53 23.5415 127.073 23.9849C126.529 24.5175 125.88 24.9294 125.166 25.1937C124.453 25.4579 123.691 25.5686 122.932 25.5184C118.958 25.5184 116.446 22.8603 115.399 17.544H114.459V25.6909H115.399C115.523 24.8188 115.83 23.9828 116.3 23.2373C117.147 24.2566 118.212 25.0732 119.416 25.6272C120.62 26.1812 121.933 26.4584 123.258 26.4385C125.368 26.5261 127.43 25.7908 129.009 24.3874M148.715 11.9275H149.271V7.6719H132.018L131.922 11.9275H132.536C132.635 11.0478 132.902 10.1954 133.322 9.4163C133.555 8.96101 133.952 8.61145 134.434 8.43865C135.191 8.29003 135.963 8.23212 136.734 8.26614H139.379V20.8028C139.404 21.7505 139.359 22.6987 139.245 23.6398C139.218 23.8199 139.155 23.9926 139.06 24.1474C138.964 24.3023 138.838 24.4362 138.689 24.5408C138.19 24.7642 137.644 24.8629 137.098 24.8283H136.255V25.4226H145.092V24.8283H144.229C143.672 24.8786 143.112 24.7654 142.619 24.5025C142.466 24.3905 142.339 24.2469 142.246 24.0816C142.154 23.9162 142.098 23.7329 142.082 23.544C141.992 22.6332 141.96 21.7176 141.986 20.8028V8.26614H144.842C145.531 8.23989 146.219 8.29782 146.894 8.43865C147.368 8.62071 147.767 8.95867 148.025 9.39711C148.458 10.1804 148.738 11.0393 148.849 11.9275M165.584 25.3459L165.948 19.8252H165.315C165.098 20.9294 164.661 21.9789 164.031 22.9114C163.608 23.5573 163.009 24.0693 162.306 24.3874C161.567 24.648 160.788 24.7715 160.005 24.7517H158.683C157.494 24.7517 156.766 24.56 156.497 24.1957C156.111 22.9965 155.974 21.731 156.095 20.4769V16.2789H158.012C158.552 16.2558 159.093 16.3009 159.622 16.413C159.783 16.4692 159.93 16.5576 160.056 16.673C160.181 16.7884 160.281 16.9283 160.35 17.084C160.558 17.7006 160.642 18.3518 160.6 19.0009H161.175V12.9242H160.561C160.595 13.5175 160.537 14.1124 160.389 14.6878C160.333 14.8422 160.244 14.9824 160.128 15.0984C160.012 15.2144 159.872 15.3033 159.718 15.3587C159.1 15.5591 158.449 15.6373 157.801 15.5888H155.884V8.13194H158.338C159.243 8.10522 160.15 8.17591 161.04 8.3428C161.622 8.49625 162.135 8.84056 162.497 9.32045C163.018 10.1212 163.364 11.0225 163.513 11.9658H164.127L163.705 7.5377H151.015V8.13194C151.589 8.08732 152.165 8.1725 152.702 8.38115C152.846 8.48699 152.967 8.62181 153.056 8.77696C153.145 8.93211 153.201 9.10416 153.219 9.2821C153.32 10.1729 153.358 11.0696 153.334 11.9658V20.6686C153.364 21.5903 153.325 22.5129 153.219 23.429C153.167 23.7752 152.998 24.0931 152.74 24.3299C152.218 24.6303 151.614 24.7577 151.015 24.6942H150.651V25.2884L165.584 25.3459ZM181.59 19.1926C181.757 19.817 181.822 20.4644 181.781 21.1095C181.805 21.8025 181.667 22.4915 181.379 23.1223C181.028 23.7227 180.499 24.1985 179.865 24.4833C179.088 24.8581 178.235 25.0483 177.373 25.0392C176.536 25.0623 175.705 24.9028 174.937 24.5717C174.169 24.2406 173.483 23.746 172.925 23.1223C171.54 21.1743 170.9 18.7932 171.123 16.413C170.895 14.0507 171.581 11.6908 173.04 9.81884C173.598 9.21643 174.274 8.73534 175.026 8.40554C175.778 8.07575 176.59 7.90432 177.411 7.90192C178.169 7.88234 178.923 8.01283 179.63 8.28588C180.338 8.55894 180.984 8.96918 181.532 9.49297C182.71 10.6564 183.443 12.1963 183.603 13.8444H184.178V7.90192H183.545C183.463 8.56414 183.282 9.21031 183.008 9.81884C182.275 8.97778 181.366 8.30702 180.346 7.85342C179.327 7.39983 178.22 7.17433 177.104 7.19267C175.867 7.13685 174.633 7.36726 173.5 7.86597C172.366 8.36469 171.362 9.11826 170.568 10.068C168.976 11.9306 168.118 14.3087 168.152 16.7581C168.121 17.9297 168.328 19.0955 168.762 20.1843C169.196 21.2731 169.847 22.2621 170.676 23.0909C171.504 23.9197 172.493 24.5708 173.582 25.0047C174.671 25.4385 175.837 25.646 177.008 25.6143C178.428 25.5807 179.83 25.2951 181.149 24.7708C181.983 24.4187 182.871 24.2113 183.775 24.1574H184.35V22.2405C184.314 21.2736 184.359 20.3053 184.484 19.3459C184.516 19.1706 184.586 19.0044 184.688 18.8587C184.791 18.7131 184.924 18.5915 185.079 18.5025C185.625 18.2815 186.216 18.1897 186.804 18.2341V17.6207H179.136V18.2341H179.539C180.031 18.2049 180.524 18.2633 180.996 18.4066C181.128 18.4689 181.248 18.5569 181.346 18.6655C181.445 18.774 181.521 18.901 181.571 19.0392" fill="currentColor"></path>
        </svg>

        <img src="data:image/png;base64,{encoded_image}" class="full-height-image">
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    st.sidebar.title("Navigation")
    app_mode = st.sidebar.radio("Choose the app mode", ["Ranking", "Add Participant", "Main Screen"])
    
    if app_mode == "Add Participant":
        add_participant_ui()
    elif app_mode == "Main Screen":
        main_screen()
    elif app_mode == "Ranking":
        ranking_ui()