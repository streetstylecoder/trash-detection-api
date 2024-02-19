import streamlit as st
from streamlit_js_eval import streamlit_js_eval, get_geolocation
import base64
import requests
import cv2

# Function to capture image from webcam
def capture_image():
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if ret:
        # Convert image to base64 string
        _, buffer = cv2.imencode('.jpg', frame)
        img_str = base64.b64encode(buffer).decode()
        cap.release()
        return img_str
    else:
        cap.release()
        return None

# Function to send image to Flask backend API
def send_image_to_api(image_data, latitude, longitude):
    url = 'http://localhost:5000/upload'  # Replace with your Flask server URL
    data = {
        'imageData': image_data,
        'latitude': latitude,
        'longitude': longitude
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        return response.json()
    else:
        return {'message': 'Error sending image to API'}

# Streamlit app
def main():
    st.title('Camera App')
    st.markdown('This app captures images from your webcam and sends them to a Flask backend API.')

    # Capture image button
    if st.button('Capture Image'):
        st.write('Capturing image...')
        image_data = capture_image()
        if st.checkbox("Check my location"):
            location = get_geolocation()
            latitude = location.get("latitude")
            longitude = location.get("longitude")
        else:
            latitude, longitude = None, None
        if image_data:
            st.image(image_data, use_column_width=True, channels='BGR')
            st.write('Image captured successfully.')
            # Send image to backend API
            st.write('Sending image to backend API...')
            response = send_image_to_api(image_data, latitude, longitude)
            st.write(response)
        else:
            st.write('Failed to capture image from webcam.')

if __name__ == '__main__':
    main()
