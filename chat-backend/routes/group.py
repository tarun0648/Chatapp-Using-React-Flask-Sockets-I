from flask import Blueprint, request, jsonify
from models.group import (
    create_group, get_user_groups, get_group_members, 
    add_group_member, remove_group_member, get_group_by_id
)
from models.message import get_messages, mark_group_messages_as_read

group_bp = Blueprint('group', __name__)

@group_bp.route('/create', methods=['POST'])
def create_new_group():
    try:
        data = request.json
        group_id = create_group(
            name=data['name'],
            description=data.get('description', ''),
            created_by=data['created_by'],
            group_picture=data.get('group_picture')
        )
        
        if group_id:
            return jsonify({'success': True, 'group_id': group_id})
        else:
            return jsonify({'success': False, 'message': 'Failed to create group'}), 500
            
    except Exception as e:
        print(f"Create group error: {e}")
        return jsonify({'success': False, 'message': 'Failed to create group'}), 500

@group_bp.route('/user/<user_id>', methods=['GET'])
def get_user_group_list(user_id):
    try:
        groups = get_user_groups(int(user_id))
        return jsonify({'success': True, 'data': groups})
    except Exception as e:
        print(f"Get user groups error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get groups'}), 500

@group_bp.route('/<group_id>/members', methods=['GET'])
def get_group_member_list(group_id):
    try:
        members = get_group_members(int(group_id))
        return jsonify({'success': True, 'data': members})
    except Exception as e:
        print(f"Get group members error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get members'}), 500

@group_bp.route('/<group_id>/messages', methods=['GET'])
def get_group_messages(group_id):
    try:
        messages = get_messages(group_id=int(group_id))
        return jsonify({'success': True, 'data': messages})
    except Exception as e:
        print(f"Get group messages error: {e}")
        return jsonify({'success': False, 'message': 'Failed to get messages'}), 500

@group_bp.route('/<group_id>/add-member', methods=['POST'])
def add_member_to_group(group_id):
    try:
        data = request.json
        success = add_group_member(
            group_id=int(group_id),
            user_id=data['user_id'],
            added_by=data['added_by']
        )
        
        if success:
            return jsonify({'success': True, 'message': 'Member added successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to add member'}), 400
            
    except Exception as e:
        print(f"Add member error: {e}")
        return jsonify({'success': False, 'message': 'Failed to add member'}), 500

@group_bp.route('/<group_id>/remove-member', methods=['POST'])
def remove_member_from_group(group_id):
    try:
        data = request.json
        success = remove_group_member(
            group_id=int(group_id),
            user_id=data['user_id'],
            removed_by=data['removed_by']
        )
        
        if success:
            return jsonify({'success': True, 'message': 'Member removed successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to remove member'}), 400
            
    except Exception as e:
        print(f"Remove member error: {e}")
        return jsonify({'success': False, 'message': 'Failed to remove member'}), 500

@group_bp.route('/<group_id>/mark-read', methods=['POST'])
def mark_group_messages_read(group_id):
    try:
        data = request.json
        affected_count = mark_group_messages_as_read(int(group_id), data['user_id'])
        return jsonify({
            'success': True, 
            'message': f'Marked {affected_count} messages as read',
            'count': affected_count
        })
    except Exception as e:
        print(f"Mark group read error: {e}")
        return jsonify({'success': False, 'message': 'Failed to mark messages as read'}), 500