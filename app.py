import os
import json
import threading
import hashlib
import time
import boto3
from botocore.exceptions import NoCredentialsError
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import google.generativeai as genai
from web3 import Web3

# ================= CONFIGURATION =================
app = Flask(__name__)
CORS(app) 

# Database Config (SQLite for local, PostgreSQL for Prod)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///civicpulse.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- DIGITAL OCEAN SPACES CONFIG (New) ---
# Get these from your DO Dashboard -> API -> Spaces Keys
SPACES_REGION = 'nyc3' # e.g., nyc3, ams3
SPACES_ENDPOINT = f'https://{SPACES_REGION}.digitaloceanspaces.com'
SPACES_KEY = os.environ.get('SPACES_KEY') 
SPACES_SECRET = os.environ.get('SPACES_SECRET')
SPACES_BUCKET = 'civicpulse-storage' # Your unique bucket name

# --- AI & BLOCKCHAIN CONFIG ---
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY") 
genai.configure(api_key=GENAI_API_KEY)

# ================= HELPERS =================

def upload_to_spaces(file, filename):
    """
    Uploads a file to Digital Ocean Spaces (S3 Compatible)
    Returns the public URL.
    """
    session = boto3.session.Session()
    client = session.client('s3',
                            region_name=SPACES_REGION,
                            endpoint_url=SPACES_ENDPOINT,
                            aws_access_key_id=SPACES_KEY,
                            aws_secret_access_key=SPACES_SECRET)

    try:
        # Upload file with public-read permission
        client.upload_fileobj(
            file, 
            SPACES_BUCKET, 
            filename, 
            ExtraArgs={'ACL': 'public-read', 'ContentType': file.content_type}
        )
        # Generate Public URL
        url = f"{SPACES_ENDPOINT}/{SPACES_BUCKET}/{filename}"
        return url
    except Exception as e:
        print(f"Upload Error: {e}")
        return None

def calculate_file_hash(file):
    """Calculates SHA256 hash of file for Blockchain integrity"""
    sha256_hash = hashlib.sha256()
    for byte_block in iter(lambda: file.read(4096), b""):
        sha256_hash.update(byte_block)
    file.seek(0) # Reset file pointer after reading
    return sha256_hash.hexdigest()

# ================= DATABASE MODELS =================
class TicketCache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, unique=True)
    category = db.Column(db.String(50))
    severity = db.Column(db.Integer)
    image_url = db.Column(db.String(200)) # Added URL field
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

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """
    1. Receives Image
    2. Uploads to DO Spaces
    3. Analyzes with Gemini
    4. Returns Hash + URL to Frontend
    """
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    
    file = request.files['image']
    
    # 1. Generate unique filename
    timestamp = int(time.time())
    filename = f"report_{timestamp}_{file.filename}"
    
    # 2. Calculate Hash (Proof of Data)
    img_hash = calculate_file_hash(file)
    
    # 3. Upload to Cloud (Digital Ocean Spaces)
    public_url = upload_to_spaces(file, filename)
    
    if not public_url:
        return jsonify({"error": "Cloud upload failed"}), 500

    # 4. AI Analysis (Mocked for stability, replace with real Gemini call)
    # In production: model.generate_content([prompt, file])
    ai_result = {
        "category": "Pothole",
        "severity": 8,
        "description": "Severe road damage."
    }
    
    # 5. Return Data to Frontend
    return jsonify({
        "category": ai_result['category'],
        "severity": ai_result['severity'],
        "imageHash": img_hash, # This goes to Blockchain
        "imageUrl": public_url # This is for the UI to display later
    })

@app.route('/api/tickets', methods=['GET'])
def get_tickets():
    tickets = TicketCache.query.all()
    return jsonify([t.to_dict() for t in tickets])

@app.route('/')
def health():
    return "CivicPulse Backend Online (Digital Ocean)", 200

# ================= MAIN =================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # In production (Droplet), use Gunicorn, not app.run()
    app.run(debug=True, port=5000)