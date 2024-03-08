import streamlit as st
import mysql.connector
import requests
from tensorflow.keras.models import load_model
import numpy as np
import cv2
import time

def connect_to_database():
    conn = mysql.connector.connect(
        host = "localhost",
        database = "blazeguards",
        user = "root",
        password = "Abhinash143"
    )
    cursor = conn.cursor()
    return conn, cursor
conn, cursor = connect_to_database()

def choose_on_map():
    st.title("Click on the map to Choose a Location")  
       # Initialize latitude and longitude with default values
    lat = 0.0
    lon = 0.0

    iframe_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
            integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
            crossorigin=""/>
        <!-- Make sure you put this AFTER Leaflet's CSS -->
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
            integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
            crossorigin=""></script>
        <style>
            #map {
                height: 400px;
                width: 258px;
                border-radius: 21px;
            }
        </style>
    </head>
    <body>
        
        <div id="map"></div>

        <script>
            var map = L.map('map').setView([28.6139, 84.2096], 7);

            L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(map);

            var popup = L.popup();

            function onMapClick(e) {
                popup
                    .setLatLng(e.latlng)
                    .setContent("You clicked the map at " + e.latlng.toString())
                    .openOn(map);

                // Update the hidden input fields with new values
                var lat = e.latlng.lat;
                var lon = e.latlng.lng;               
                
            }

            map.on('click', onMapClick);
        </script>
    </body>
    </html>
    """

    
    st.components.v1.html(iframe_html, width=800, height=600)

    # Display text input fields for latitude and longitude
    lat = st.text_input("Latitude", value=str(lat), key="latitude")
    lon = st.text_input("Longitude", value=str(lon), key="longitude")

    return lat, lon
             

# Function to handle "Manually" method

def manually_select_location():
    st.write("You chose 'Manually'")
    location_name = st.text_input("Enter a location:")

    latitude = None
    longitude = None
    
    if st.button("Geocode"):
        if location_name:
            # Geocode the entered location
            base_url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": location_name,
                "format": "json",
            }

            response = requests.get(base_url, params=params)
            data = response.json()

            if data:
                first_result = data[0]  # Take the first result (most relevant)
                latitude = float(first_result["lat"])
                longitude = float(first_result["lon"])
                
            else:
                st.write("Unable to geocode the address.")
        else:
            st.write("Please enter a location.")

    return latitude, longitude
 

# Function to handle "Current Location" method

def get_current_location():    
    try:
        response = requests.get('https://ipinfo.io')
        data = response.json()
        if 'loc' in data:
            latitude, longitude = data['loc'].split(',')
            address = data['city']            
            return float(latitude), float(longitude), address
    except Exception as e:
        print(f"An error occurred: {e}")


# Function to validate user credentials
def validate_login(username, password):
    query = "SELECT * FROM blazeguards.admins WHERE username = %s AND password = %s"
    cursor.execute(query, (username, password))
    result = cursor.fetchone()
    return result is not None


def display_submissions():
    query = "SELECT submission_id, address, fire_intensity, population_density, sensitive_areas, status FROM blazeguards.submissions"
    cursor.execute(query)
    submissions = cursor.fetchall()

    # Display all submissions
    # Create a list of dictionaries for the data
    data = []
    for submission in submissions:
        data.append({
            "Address": submission[1],
            "Fire Intensity": submission[2],
            "Population Density": submission[3],
            "Sensitive Areas": submission[4],
            "Status": submission[5]
        })

    # Display the data in a table
    st.header('Fire Reports 🔔')
    st.table(data)

# Function to update status
def set_status():
    st.header('Set the status of alerts ⏱')
    query = "SELECT submission_id, address, fire_intensity, population_density, sensitive_areas, status FROM blazeguards.submissions"
    cursor.execute(query)
    submissions = cursor.fetchall()
    # Provide option to select and update status of specific submission
    selected_submission = st.selectbox("Select Submissions by Address", [submission[1] for submission in submissions])

    for submission in submissions:
        if selected_submission == submission[1]:
            # st.write(f"\nSelected Submission - Submission ID: {submission[0]}, Address: {submission[1]}, Fire Intensity: {submission[2]}, Population Density: {submission[3]}, Sensitive Areas: {submission[4]}, Status: {submission[5]}")
            status = st.selectbox(f"Set Status of - {submission[1]}", ["In-Operation", "Controlled", "Active"], key=f"status_{submission[1]}")
            if st.button('Update'):
                # Update the status in the database
                update_query = "UPDATE blazeguards.submissions SET status = %s WHERE submission_id = %s"
                cursor.execute(update_query, (status, submission[0]))
                conn.commit()

#Set the region to receive alerts
def set_region():
    st.header("Select the region to get the alert")
    user_lat = float(st.number_input("Latitude"))
    user_lon = float(st.number_input("Longitude"))
    if st.button('Set'):
        if user_lat and user_lon:
            st.write("Submitted Data:")
            st.write(f"Latitude: {user_lat}")
            st.write(f"Longitude: {user_lon}")
            # Save data to MySQL
            query = "INSERT INTO regions (latitude, longitude) VALUES (%s, %s)"
            cursor.execute(query, (user_lat, user_lon))
            conn.commit()


#Fire Detection model
def fire_detection():
    # Load the trained model
    cnn = load_model('models/fire-smoke-normal.h5')

    # Define the categories
    Categories = ['Fire', 'Normal', 'Smoke']

    # Initialize VideoCapture object for live feed
    cap = cv2.VideoCapture(1)
    cap.set(cv2.CAP_PROP_FPS, 4)

    # Streamlit loop
    button_counter = 0

    # Flag to control warnings
    send_warnings = st.checkbox("Start Warnings", value=True)

    # Create a container to hold the video feed and controls
    video_container = st.container()

    # Streamlit loop
    with video_container:
        st.header("Live Video Feed")
        video_placeholder = st.empty()
        stop_placeholder = st.empty()
        while True:
            # Read a frame from the video feed
            ret, frame = cap.read()

            # Convert the frame to RGB and resize
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            frame_resized = cv2.resize(frame_rgb, (224, 224))
            frame_resized = frame_resized / 255.0
            frame_resized = np.expand_dims(frame_resized, axis=0)

            # Predict using the model
            result = cnn.predict(frame_resized)
            result = np.argmax(result, axis=1)[0]


            # Get the highest probability
            accuracy = np.max(result)
            label = Categories[result]

            # Draw the category and accuracy on the frame
            label_text = f'{label}'
            cv2.putText(frame, label_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            # Display the frame
            video_placeholder.image(frame, caption='Processed Frame', width=640)

            # Generate a unique key for the button using the counter
            button_key = f'stop_button_{button_counter}'
            button_counter += 1

            # Break the loop if 'q' is pressed
            if stop_placeholder.button('Stop', key=button_key):
                break
            # Initialize a timestamp variable
            last_warning_time = time.time()
            # If fire or smoke detected and accuracy is greater than 90%, send an SMS alert
            if send_warnings and accuracy > 0.9 and label in ['Fire', 'Smoke']:
                current_time = time.time()
                # Check if 15 minutes have passed since the last warning
                if current_time - last_warning_time >= 900:  # 900 seconds = 15 minutes
                    st.warning(f"Alert! of {label} is sent to the authorities.")
                    # Update the timestamp
                    last_warning_time = current_time

    # Release VideoCapture object
    cap.release()
