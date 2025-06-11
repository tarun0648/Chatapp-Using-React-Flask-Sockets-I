from flask import Blueprint, request, jsonify
from models.user import get_user_by_id, get_all_users_except, update_user_profile
from models.message import get_unread_count
from models.group import get_user_groups
import os
from werkzeug.utils import secure_filename

user_bp = Blueprint('user', __name__)

# Configure upload settings
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        
        success = update_user_profile(
            user_id=int(user_id),
            name=data.get('name'),
            email=data.get('email'),
            phone=data.get('phone'),
            profile_picture=data.get('profile_picture')
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
        # Get direct chats
        users = get_all_users_except(int(user_id))
        unread_counts = get_unread_count(int(user_id))
        
        # Get group chats
        groups = get_user_groups(int(user_id))
        
        chats = []
        
        # Add direct chats
        for user in users:
            online_status = False
            status_text = 'Offline'
            
            if user.get('status') == 'online':
                online_status = True
                status_text = 'Online'
            elif user.get('status') == 'recently_active':
                status_text = 'Recently active'
            elif user.get('last_active'):
                from datetime import datetime
                now = datetime.now()
                if isinstance(user['last_active'], str):
                    try:
                        last_active = datetime.strptime(user['last_active'], '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        last_active = datetime.strptime(user['last_active'][:19], '%Y-%m-%d %H:%M:%S')
                else:
                    last_active = user['last_active']
                
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
                'id': f"{user_id}_{user['id']}",
                'type': 'direct',
                'user': user['name'],
                'username': user['username'],
                'user_id': user['id'],
                'profile_picture': user.get('profile_picture'),
                'online': online_status,
                'status': status_text,
                'unread_count': unread_counts.get(user['id'], 0)
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
        
        return jsonify({'success': True, 'data': chats})
    except Exception as e:
        print(f"Chats error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get chats'}), 500