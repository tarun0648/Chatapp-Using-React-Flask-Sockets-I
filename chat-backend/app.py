from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from config import close_db
from routes.auth import auth_bp
from routes.user import user_bp
from routes.chat import chat_bp
from routes.group import group_bp  # New import
from sockets.chat_socket import socketio_init

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.teardown_appcontext(close_db)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(user_bp, url_prefix="/user")
app.register_blueprint(chat_bp, url_prefix="/chat")
app.register_blueprint(group_bp, url_prefix="/group")  # New route

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:3000"])
socketio_init(socketio)

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
    print("Features: Group Chat, Profile Editing, No Timestamps")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)