import streamlit as st
from setups.config import validate_login, display_submissions,\
    connect_to_database, set_status, fire_detection,\
    set_region
from app import active_fire_data

 
headerSection = st.container()
mainSection = st.container()
loginSection = st.container()
logOutSection = st.container()

#Calling database connection function
conn, cursor = connect_to_database()


#Call main page display functions
def show_main_page():
    with st.sidebar:
        set_status()
        set_region()

    # Alert System
    # Function to calculate Haversine distance
    def haversine(lat1, lon1, lat2, lon2):
        import math
        R = 6371  # Radius of the Earth in kilometers
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) * math.sin(dlon / 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = R * c  # Distance in kilometers
        return distance

    # Define a threshold distance for considering a fire to be nearby (in kilometers)
    threshold_distance = 50  # Adjust as needed

    cursor.execute("SELECT latitude, longitude FROM blazeguards.regions WHERE id=%s",(1,))
    # Fetch the result
    user_location = cursor.fetchone()
    # Check if user_location is not None and has both latitude and longitude
    if user_location and len(user_location) == 2:
        user_lat, user_lon = user_location
        # st.write(f"User's latitude: {user_lat}, longitude: {user_lon}")
    else:
        st.write("Could not retrieve user location from the database.")

    # Continuous monitoring loop
    st.write("Monitoring for nearby fires...")
    nearby_fires = []
    for index, row in active_fire_data.iterrows():
        latitude = row['latitude']
        longitude = row['longitude']
        distance = haversine(user_lat, user_lon, latitude, longitude)
        if distance <= threshold_distance:
            nearby_fires.append(row)
    # Display alert if there are nearby fires
    if st.button(f"Alerts- {len(nearby_fires)}"):
        if nearby_fires:
            st.warning(f"There are {len(nearby_fires)} nearby fires.")
            st.write("Details of nearby fires:")
            for row in nearby_fires:
                st.write(f"Latitude: {row['latitude']}, Longitude: {row['longitude']}")
        else:
            st.success("No nearby fires detected.")


    with mainSection:
        display_submissions()
        st.header('CCTV Fire Capture Alert 📹')
        fire_detection()



#Log Out Session Set 
def LoggedOut_Clicked():
    st.session_state['loggedIn'] = False

#Log Out Page    
def show_logout_page():
    loginSection.empty()
    with logOutSection:
        st.button ("Log Out", key="logout", on_click=LoggedOut_Clicked)

#Call validate user-pass function    
def LoggedIn_Clicked(userName, password):
    if validate_login(userName, password):
        st.session_state['loggedIn'] = True
    else:
        st.session_state['loggedIn'] = False
        st.error("Invalid user name or password")

#Show login page.    
def show_login_page():
    with loginSection:
        if st.session_state['loggedIn'] == False:
            userName = st.text_input (label="Username", value="", placeholder="Enter your user name")
            password = st.text_input (label="Password", value="",placeholder="Enter password", type="password")
            st.button ("Login", on_click=LoggedIn_Clicked, args= (userName, password))

#Initiating sessions and setting up main page
with headerSection:
    st.title("🖥 Admin Panel")
    #first run will have nothing in session_state
    if 'loggedIn' not in st.session_state:
        st.session_state['loggedIn'] = False
        show_login_page() 
    else:
        if st.session_state['loggedIn']:
            show_logout_page()    
            show_main_page()  
        else:
            show_login_page()