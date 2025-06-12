from flask import Blueprint, request, jsonify
from models.message import get_messages, save_message, mark_messages_as_read

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/messages', methods=['POST'])
def fetch_messages():
    try:
        data = request.json
        messages = get_messages(data['sender_id'], data['receiver_id'])
        return jsonify({'success': True, 'data': messages})
    except Exception as e:
        print(f"Fetch messages error: {e}")
        return jsonify({'success': False, 'message': 'Failed to fetch messages'}), 500

@chat_bp.route('/<chat_id>', methods=['GET'])
def get_chat_messages(chat_id):
    try:
        user_ids = chat_id.split('_')
        if len(user_ids) == 2:
            messages = get_messages(int(user_ids[0]), int(user_ids[1]))
            return jsonify({'success': True, 'data': messages})
        return jsonify({'success': False, 'message': 'Invalid chat ID'}), 400
    except Exception as e:
        print(f"Chat messages error: {e}")
        return jsonify({'success': False, 'message': 'Failed to fetch messages'}), 500

@chat_bp.route('/message', methods=['POST'])
def send_message():
    try:
        data = request.json
        
        if data.get('group_id'):
            # Group message
            message_id = save_message(
                sender_id=data['sender_id'],
                content=data['content'],
                group_id=data['group_id']
            )
        else:
            # Direct message
            message_id = save_message(
                sender_id=data['sender_id'],
                receiver_id=data['receiver_id'],
                content=data['content']
            )
            
        if message_id:
            return jsonify({'success': True, 'message': 'Message sent', 'message_id': message_id})
        else:
            return jsonify({'success': False, 'message': 'Failed to send message'}), 500
    except Exception as e:
        print(f"Send message error: {e}")
        return jsonify({'success': False, 'message': 'Failed to send message'}), 500

@chat_bp.route('/mark-read', methods=['POST'])
def mark_messages_read():
    try:
        data = request.json
        affected_count = mark_messages_as_read(
            data['sender_id'], 
            data['receiver_id'], 
            data['reader_id']
        )
        return jsonify({
            'success': True, 
            'message': f'Marked {affected_count} messages as read',
            'count': affected_count
        })
    except Exception as e:
        print(f"Mark read error: {e}")
        return jsonify({'success': False, 'message': 'Failed to mark messages as read'}), 500