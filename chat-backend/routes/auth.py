from flask import Blueprint, request, jsonify
from models.user import get_user_by_username, create_user, get_user_by_email
import bcrypt

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['name', 'username', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        # Check if user already exists
        existing_user = get_user_by_username(data['username'])
        if existing_user:
            return jsonify({'success': False, 'message': 'Username already exists'}), 400
            
        existing_email = get_user_by_email(data['email'])
        if existing_email:
            return jsonify({'success': False, 'message': 'Email already exists'}), 400
            
        # Hash password
        hashed_pw = bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt())
        
        # Create user
        success = create_user(
            data['name'], 
            data['username'], 
            data['email'], 
            hashed_pw.decode(), 
            data.get('phone', '')
        )
        
        if success:
            return jsonify({'success': True, 'message': 'User created successfully'}), 201
        else:
            return jsonify({'success': False, 'message': 'Failed to create user'}), 500
            
    except Exception as e:
        print(f"Signup error: {e}")
        return jsonify({'success': False, 'message': 'Registration failed'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        
        if not data.get('username') or not data.get('password'):
            return jsonify({'success': False, 'message': 'Username and password required'}), 400
            
        user = get_user_by_username(data['username'])
        
        if user and bcrypt.checkpw(data['password'].encode(), user['password'].encode()):
            return jsonify({'success': True, 'token': str(user['id'])})
        
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'success': False, 'message': 'Login failed'}), 500