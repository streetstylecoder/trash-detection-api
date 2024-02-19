import os
import json
import requests
from flask import Flask, jsonify,render_template_string,request
import cv2
import firebase_admin
from firebase_admin import credentials, firestore, storage
from apscheduler.schedulers.background import BackgroundScheduler
import requests
from datetime import datetime, timedelta


app = Flask(__name__)

global_latitude = None
global_longitude = None

html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Location Sender</title>
    <script>
        function sendLocation() {
            if ("geolocation" in navigator) {
                navigator.geolocation.getCurrentPosition(function(position) {
                    const latitude = position.coords.latitude;
                    const longitude = position.coords.longitude;

                    // Send this information to the Flask backend
                    fetch('/start', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ latitude: latitude, longitude: longitude }),
                    })
                    .then(response => response.json())
                    .then(data => {
                        console.log('Success:', data);
                        document.getElementById("status").innerText = "Location sent successfully.";
                    })
                    .catch((error) => {
                        console.error('Error:', error);
                        document.getElementById("status").innerText = "Error sending location.";
                    });
                });
            } else {
                console.log("Geolocation is not available in your browser.");
                document.getElementById("status").innerText = "Geolocation is not available in your browser.";
            }
        }
    </script>
</head>
<body>
    <h1>Send Location to Flask</h1>
    <button onclick="sendLocation()">Send Location</button>
    <p id="status"></p>
</body>
</html>
"""



# Initialize Firebase
cred = credentials.Certificate('camera-app-e2db9-firebase-adminsdk-lpw9g-7f9e089d05.json')
firebase_admin.initialize_app(cred, {
    'storageBucket': 'camera-app-e2db9.appspot.com'
})

db = firestore.client()


# Function to capture image
def capture_image():
    print("capture image")
    cap = cv2.VideoCapture(0)  # Index 0 for default camera
    ret, frame = cap.read()
    image_path = 'captured_image.jpg'
    if ret:
        cv2.imwrite(image_path, frame)
    cap.release()
    return ret, image_path

def upload_image(file_path):
    url = "https://freeimage.host/api/1/upload"

    payload = {
        'key': '6d207e02198a847aa98d0a2a901485a5',
        'action': 'upload',
        'format': 'json'
    }
    files = [
        ('source', (file_path.split('/')[-1], open(file_path, 'rb'), 'image/jpeg'))
    ]
    headers = {
        'Cookie': 'PHPSESSID=vlmiuj40ptgrs1huonaj59fiah'  # This might not be needed; try removing if not required
    }

    response = requests.request("POST", url, headers=headers, data=payload, files=files)
    data = response.json()

    # Check if the upload was successful
    if response.status_code == 200 and 'status_code' in data and data['status_code'] == 200:
        # Return the URL of the uploaded image
        return data['image']['url']
    else:
        # Print the error if something went wrong
        error_message = data.get('error', {}).get('message', 'An error occurred')
        print(f"Error uploading image: {error_message}")
        return None

# Function to get classes from Roboflow

def get_classes_from_roboflow(image_url):
    api_key = "39FZgkRj9QxkBcPy0z0n"
    encoded_url = requests.utils.quote(image_url)
    roboflow_url = f"https://detect.roboflow.com/garbage-detection-hua7l/1?api_key={api_key}&image={encoded_url}"
    response = requests.post(roboflow_url)
    if response.status_code == 200:
        predictions = response.json()["predictions"]
        classes = [prediction["class"] for prediction in predictions]
        print(classes)
        return classes
    else:
        return None

# Function to upload image to Firebase Storage and Firestore
def upload_to_firebase(image_path, image_url, classes,latitude,longitude):
    bucket = storage.bucket()
    blob = bucket.blob(f'images/{os.path.basename(image_path)}')
    blob.upload_from_filename(image_path)

    # Generate a signed URL for the blob that is valid for 24 hours
    firebase_image_url = blob.generate_signed_url(
        expiration=datetime.utcnow() + timedelta(hours=90),
        method='GET'
    )


    # Save image data to Firestore
    waste_data = {
        'imageUrl': firebase_image_url,
        'tags': classes,
       'latitude': latitude,
        'longitude': longitude
    }
    db.collection('wasteData').add(waste_data)
    print("data uploaded to firebase")

# Scheduled job to capture, upload, and process images
def scheduled_job():
    print("Capturing image...")
    success, image_path = capture_image()
    if success:
        print("Uploading image to hosting service...")
        image_url = upload_image(image_path)
        
        print("Getting classes from Roboflow...")
        classes = get_classes_from_roboflow(image_url)
        if classes:
            print("Detected classes:", classes)
            print("Uploading image to Firebase...")
            # Pass the global latitude and longitude
            upload_to_firebase(image_path, image_url, classes, global_latitude, global_longitude)
            print("Upload to Firebase completed.")
        else:
            print("No classes detected.")
    else:
        print("Image capture failed.")


scheduler = BackgroundScheduler()

# Define scheduled_job function here

# Start the scheduler outside the route
scheduler.add_job(scheduled_job, 'interval', seconds=5, max_instances=1)
scheduler.start()


@app.route('/')
def index():
    return render_template_string(html_content)



# Endpoint to start the capture-upload process
@app.route('/start', methods=['POST'])
def start():
    global global_latitude, global_longitude
    data = request.json
    global_latitude = data.get('latitude')
    global_longitude = data.get('longitude')

    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_job, 'interval', seconds=5)
    scheduler.start()
    return jsonify({'status': 'Capture started with location'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
