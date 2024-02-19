from flask import Flask, request, jsonify
from tensorflow.keras.models import load_model
from PIL import Image
import numpy as np

app = Flask(__name__)

# Load your trained model
model = load_model('trash.h5')

@app.route('/predict', methods=['POST'])
def predict():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    image = Image.open(file.stream).resize((180, 180))
    image_array = np.asarray(image) / 255.0  # Normalize the image
    prediction = model.predict(np.expand_dims(image_array, axis=0))
    class_id = np.argmax(prediction, axis=1)[0]
    
    # Define your classes
    classes = ['Cardboard', 'Glass', 'Metal', 'Paper', 'Plastic', 'Trash']

    return jsonify({'class': classes[class_id], 'confidence': float(np.max(prediction))})

if __name__ == '__main__':
    app.run(debug=True)
