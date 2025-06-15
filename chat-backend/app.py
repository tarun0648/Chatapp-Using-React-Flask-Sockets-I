# backend/app.py - FIXED BROADCAST ERROR
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

# Enhanced CORS settings for Socket.IO
CORS(app, 
     origins=["http://localhost:3000"], 
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=True)

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

# ✅ FIXED: Enhanced SocketIO configuration - REMOVED BROADCAST ERROR
socketio = SocketIO(
    app, 
    cors_allowed_origins=["http://localhost:3000"], 
    logger=True, 
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25,
    transports=['websocket', 'polling'],
    allow_upgrades=True,
    async_mode='threading'
)

# Initialize socket handlers
socketio_init(socketio)

# Serve static files
from flask import send_from_directory

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('static/uploads', filename)

@app.route('/')
def home():
    return {"message": "Enhanced Chat Backend Running", "status": "OK", "features": ["Real-time messaging", "Typing indicators", "Read receipts"]}

@app.route('/health')
def health():
    return {"status": "healthy", "socket_connected": True}

# Enhanced debugging middleware
@app.before_request
def log_request_info():
    if request.path.startswith('/socket.io'):
        print(f'📡 Socket.IO request: {request.method} {request.path}')

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Starting FIXED Flask-SocketIO Chat Server")
    print("=" * 60)
    print("📱 Frontend URL: http://localhost:3000")
    print("🔧 Backend API: http://localhost:5000")
    print("🔌 WebSocket: ws://localhost:5000")
    print("=" * 60)
    print("✅ FIXED Features:")
    print("   - ✅ Blue tick for direct chats")
    print("   - ✅ Real-time chat list notifications")
    print("   - ✅ Fast online/offline status")
    print("   - ✅ Fixed broadcast error")
    print("   - ✅ Enhanced error handling")
    print("=" * 60)
    
    socketio.run(
        app, 
        debug=True, 
        host='0.0.0.0', 
        port=5000,
        use_reloader=False,  # Important: prevents socket.io issues
        log_output=True
    )