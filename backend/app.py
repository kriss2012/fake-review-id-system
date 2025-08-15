from flask import Flask, request, jsonify, send_from_directory
from model import fake_review_detector
import os
from PIL import Image
import pytesseract

app = Flask(__name__, static_folder=None)
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../frontend')

@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_review():
    review = request.form.get('review', '').strip()
    photo = request.files.get('photo')
    input_text = review

    # Extract text from image if no review text is provided
    if not input_text and photo:
        os.makedirs('uploads', exist_ok=True)
        filepath = os.path.join('uploads', photo.filename)
        photo.save(filepath)
        try:
            img = Image.open(filepath)
            extracted_text = pytesseract.image_to_string(img).strip()
            input_text = extracted_text
        except Exception:
            return jsonify({"result": "Error", "reason": "Photo could not be processed."}), 500

    # If still no input text, return error
    if not input_text:
        return jsonify({"result": "No review provided.", "reason": ""}), 400

    result, reason = fake_review_detector(input_text)
    return jsonify({"result": result, "reason": reason})

@app.route('/<path:path>')
def serve_static_files(path):
    return send_from_directory(FRONTEND_DIR, path)

if __name__ == '__main__':
    app.run(debug=True)
