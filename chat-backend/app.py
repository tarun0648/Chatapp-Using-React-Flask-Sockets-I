from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
from config import close_db
from routes.auth import auth_bp
from routes.user import user_bp
from routes.chat import chat_bp
from routes.group import group_bp
from sockets.chat_socket import socketio_init
import os

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'static/uploads')
app.teardown_appcontext(close_db)

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/uploads', exist_ok=True)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(user_bp, url_prefix="/user")
app.register_blueprint(chat_bp, url_prefix="/chat")
app.register_blueprint(group_bp, url_prefix="/group")

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:3000"], logger=True, engineio_logger=False)
socketio_init(socketio)

# Serve static files
from flask import send_from_directory

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('static/uploads', filename)

@app.route('/')
def home():
    return {"message": "Enhanced Chat Backend Running", "status": "OK"}

@app.route('/health')
def health():
    return {"status": "healthy"}

if __name__ == '__main__':
    print("Starting Enhanced Flask-SocketIO server...")
    print("Backend API: http://localhost:5000")
    print("WebSocket: ws://localhost:5000")
    print("Features: Group Chat, Profile Editing, Real-time messaging")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)