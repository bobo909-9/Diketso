import os
import json
import threading
import hashlib
import time
# import boto3  <-- REMOVED
# from botocore.exceptions import NoCredentialsError <-- REMOVED
from flask import Flask, request, jsonify, send_from_directory, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import google.generativeai as genai
from web3 import Web3

# ================= CONFIGURATION =================
app = Flask(__name__)
CORS(app)

# --- LOCAL STORAGE CONFIG (New) ---
# This creates a folder named 'static/uploads' in your project directory
# Flask is good at serving files from 'static' folders
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Creates the folder if it doesn't exist

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///civicpulse.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- AI CONFIG ---
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY") 
genai.configure(api_key=GENAI_API_KEY)

# ================= HELPERS =================

def save_locally(file, filename):
    """
    Saves a file to the local filesystem instead of Digital Ocean.
    Returns the local URL.
    """
    try:
        # Create the full path: e.g., /Users/You/Project/static/uploads/report_123.jpg
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save the file using Flask's built-in save method
        file.save(file_path)
        
        # Generate Local URL
        # This creates a URL like: http://localhost:5000/uploads/report_123.jpg
        # _external=True ensures it includes the 'http://localhost:5000' part
        url = url_for('uploaded_file', filename=filename, _external=True)
        return url
    except Exception as e:
        print(f"Save Error: {e}")
        return None

def calculate_file_hash(file):
    """Calculates SHA256 hash of file for Blockchain integrity"""
    sha256_hash = hashlib.sha256()
    # Read file in chunks to avoid memory issues
    for byte_block in iter(lambda: file.read(4096), b""):
        sha256_hash.update(byte_block)
    file.seek(0) # CRITICAL: Reset file pointer after reading so it can be saved later!
    return sha256_hash.hexdigest()

# ================= DATABASE MODELS =================
class TicketCache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, unique=True)
    category = db.Column(db.String(50))
    severity = db.Column(db.Integer)
    image_url = db.Column(db.String(200)) 
    status = db.Column(db.String(20))

    def to_dict(self):
        return {
            "ticket_id": self.ticket_id,
            "category": self.category,
            "severity": self.severity,
            "image_url": self.image_url,
            "status": self.status
        }

# ================= ROUTES =================

# --- NEW ROUTE TO SERVE IMAGES ---
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """
    This route lets the frontend 'see' the image.
    If the frontend asks for http://localhost:5000/uploads/pic.jpg,
    Flask serves it from the static/uploads folder.
    """
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """
    1. Receives Image
    2. Calculates Hash
    3. Saves Locally
    4. Analyzes with Gemini
    5. Returns Hash + Local URL
    """
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    
    file = request.files['image']
    
    # 1. Generate unique filename
    timestamp = int(time.time())
    filename = f"report_{timestamp}_{file.filename}"
    
    # 2. Calculate Hash (Proof of Data)
    # Note: We calculate hash BEFORE saving
    img_hash = calculate_file_hash(file)
    
    # 3. Save to Local Disk (Replaces Digital Ocean)
    public_url = save_locally(file, filename)
    
    if not public_url:
        return jsonify({"error": "Local save failed"}), 500

    # 4. AI Analysis (Mocked for stability)
    # In production: model.generate_content([prompt, file])
    ai_result = {
        "category": "Pothole",
        "severity": 8,
        "description": "Severe road damage detected."
    }
    
    # 5. Return Data to Frontend
    return jsonify({
        "category": ai_result['category'],
        "severity": ai_result['severity'],
        "imageHash": img_hash, 
        "imageUrl": public_url # This will now be http://localhost:5000/uploads/...
    })

@app.route('/api/tickets', methods=['GET'])
def get_tickets():
    tickets = TicketCache.query.all()
    return jsonify([t.to_dict() for t in tickets])

@app.route('/')
def health():
    return "CivicPulse Backend Online (Local Storage Mode)", 200

# ================= MAIN =================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
