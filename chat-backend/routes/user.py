from flask import Blueprint, request, jsonify, current_app
from models.user import get_user_by_id, get_all_users_except, update_user_profile
from models.message import get_unread_count
from models.group import get_user_groups
import os
import base64
import uuid
from werkzeug.utils import secure_filename

user_bp = Blueprint('user', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_base64_image(base64_data, user_id):
    try:
        # Extract base64 data
        if ',' in base64_data:
            header, data = base64_data.split(',', 1)
            # Get file extension from header
            if 'jpeg' in header or 'jpg' in header:
                ext = 'jpg'
            elif 'png' in header:
                ext = 'png'
            elif 'gif' in header:
                ext = 'gif'
            else:
                ext = 'jpg'  # default
        else:
            data = base64_data
            ext = 'jpg'  # default
        
        # Generate unique filename
        filename = f"profile_{user_id}_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join('static/uploads', filename)
        
        # Decode and save
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(data))
        
        return f"/static/uploads/{filename}"
    except Exception as e:
        print(f"Error saving image: {e}")
        return None

@user_bp.route('/profile/<token>', methods=['GET'])
def get_profile(token):
    try:
        user = get_user_by_id(int(token))
        if user:
            user.pop('password', None)
            return jsonify({'success': True, 'data': user})
        return jsonify({'success': False, 'message': 'User not found'}), 404
    except Exception as e:
        print(f"Profile error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get profile'}), 500

@user_bp.route('/profile/<user_id>/update', methods=['PUT'])
def update_profile(user_id):
    try:
        data = request.json
        
        # Handle profile picture
        profile_picture_url = data.get('profile_picture')
        if profile_picture_url and profile_picture_url.startswith('data:'):
            # It's a base64 image, save it
            saved_url = save_base64_image(profile_picture_url, user_id)
            if saved_url:
                profile_picture_url = saved_url
            else:
                return jsonify({'success': False, 'message': 'Failed to save profile picture'}), 500
        
        success = update_user_profile(
            user_id=int(user_id),
            name=data.get('name'),
            email=data.get('email'),
            phone=data.get('phone'),
            profile_picture=profile_picture_url
        )
        
        if success:
            return jsonify({'success': True, 'message': 'Profile updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to update profile'}), 500
            
    except Exception as e:
        print(f"Update profile error: {e}")
        return jsonify({'success': False, 'message': 'Failed to update profile'}), 500

@user_bp.route('/chats/<user_id>', methods=['GET'])
def get_user_chats(user_id):
    try:
        # Get current user's info first
        current_user = get_user_by_id(int(user_id))
        
        # Get direct chats
        users = get_all_users_except(int(user_id))
        unread_counts = get_unread_count(int(user_id))
        
        # Get group chats
        groups = get_user_groups(int(user_id))
        
        chats = []
        
        # Add direct chats
        for user_data in users:
            online_status = user_data.get('is_online', False) or user_data.get('status') == 'online'
            status_text = 'Online' if online_status else 'Offline'
            
            if not online_status and user_data.get('last_active'):
                from datetime import datetime
                now = datetime.now()
                if isinstance(user_data['last_active'], str):
                    try:
                        last_active = datetime.strptime(user_data['last_active'], '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        last_active = datetime.strptime(user_data['last_active'][:19], '%Y-%m-%d %H:%M:%S')
                else:
                    last_active = user_data['last_active']
                
                diff = now - last_active
                if diff.days > 0:
                    status_text = f"Last seen {diff.days} days ago"
                elif diff.seconds > 3600:
                    hours = diff.seconds // 3600
                    status_text = f"Last seen {hours} hours ago"
                elif diff.seconds > 60:
                    minutes = diff.seconds // 60
                    status_text = f"Last seen {minutes} minutes ago"
                else:
                    status_text = "Last seen just now"
            
            chats.append({
                'id': f"{user_id}_{user_data['id']}",
                'type': 'direct',
                'user': user_data['name'],
                'username': user_data['username'],
                'user_id': user_data['id'],
                'profile_picture': user_data.get('profile_picture'),
                'online': online_status,
                'status': status_text,
                'unread_count': unread_counts.get(user_data['id'], 0)
            })
        
        # Add group chats
        for group in groups:
            chats.append({
                'id': f"group_{group['id']}",
                'type': 'group',
                'user': group['name'],
                'description': group.get('description', ''),
                'group_id': group['id'],
                'profile_picture': group.get('group_picture'),
                'member_count': group.get('member_count', 0),
                'role': group.get('role', 'member'),
                'unread_count': group.get('unread_count', 0)
            })
        
        # Add current user info for header display
        response_data = {
            'chats': chats,
            'current_user': {
                'id': current_user['id'],
                'name': current_user['name'],
                'username': current_user['username'],
                'profile_picture': current_user.get('profile_picture')
            }
        }
        
        return jsonify({'success': True, 'data': response_data})
    except Exception as e:
        print(f"Chats error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get chats'}), 500