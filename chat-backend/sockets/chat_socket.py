from flask_socketio import emit, join_room, leave_room
from flask import request  # Fixed import - request comes from flask, not flask_socketio
from models.message import save_message, mark_messages_as_read, get_message_by_id
from models.user import update_user_online_status, get_user_by_id

# Store user sessions
active_users = {}  # {socket_id: user_id}
user_sockets = {}  # {user_id: [socket_ids]}

def socketio_init(socketio):
    @socketio.on('connect')
    def handle_connect(auth):
        print(f'Client connected: {request.sid}')
        try:
            # Get user ID from auth token
            token = auth.get('token') if auth else None
            if token:
                user_id = int(token)  # Simple token = user_id for now
                
                # Store user session
                active_users[request.sid] = user_id
                if user_id not in user_sockets:
                    user_sockets[user_id] = []
                user_sockets[user_id].append(request.sid)
                
                # Update online status
                update_user_online_status(user_id, True, request.sid)
                
                # Emit to all users that this user is online
                emit('user_online', {'user_id': user_id}, broadcast=True)
                
                print(f'User {user_id} connected with socket {request.sid}')
                
        except Exception as e:
            print(f'Connect error: {e}')

    @socketio.on('disconnect')
    def handle_disconnect():
        print(f'Client disconnected: {request.sid}')
        try:
            if request.sid in active_users:
                user_id = active_users[request.sid]
                
                # Remove from active sessions
                del active_users[request.sid]
                if user_id in user_sockets:
                    user_sockets[user_id].remove(request.sid)
                    if not user_sockets[user_id]:  # No more active sessions
                        del user_sockets[user_id]
                        # Update offline status
                        update_user_online_status(user_id, False, request.sid)
                        # Emit to all users that this user is offline
                        emit('user_offline', {'user_id': user_id}, broadcast=True)
                
                print(f'User {user_id} disconnected')
                
        except Exception as e:
            print(f'Disconnect error: {e}')

    @socketio.on('join')
    def handle_join(data):
        try:
            chat_id = data['chat_id']
            join_room(chat_id)
            print(f'User joined room: {chat_id}')
            emit('status', {'msg': f'Joined room {chat_id}'}, room=chat_id)
        except Exception as e:
            print(f'Join error: {e}')

    @socketio.on('leave')
    def handle_leave(data):
        try:
            chat_id = data['chat_id']
            leave_room(chat_id)
            print(f'User left room: {chat_id}')
        except Exception as e:
            print(f'Leave error: {e}')

    @socketio.on('send_message')
    def handle_send_message(data):
        try:
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
                message_data = get_message_by_id(message_id)
                if message_data:
                    chat_id = data['chat_id']
                    
                    emit('receive_message', {
                        'id': message_data['id'],
                        'sender_id': message_data['sender_id'],
                        'receiver_id': message_data.get('receiver_id'),
                        'group_id': message_data.get('group_id'),
                        'content': message_data['content'],
                        'status': message_data.get('status', 'sent'),
                        'sender_username': message_data.get('sender_username'),
                        'sender_name': message_data.get('sender_name'),
                        'sender_picture': message_data.get('sender_picture')
                    }, room=chat_id)
                    
                    emit('message_delivered', {
                        'message_id': message_id,
                        'chat_id': chat_id
                    }, room=request.sid)
                    
        except Exception as e:
            print(f'Error sending message: {e}')
            emit('error', {'message': 'Failed to send message'})

    @socketio.on('mark_read')
    def handle_mark_read(data):
        try:
            sender_id = data['sender_id']
            receiver_id = data['receiver_id']
            reader_id = data['reader_id']
            
            affected_count = mark_messages_as_read(sender_id, receiver_id, reader_id)
            
            if affected_count > 0:
                # Notify sender that messages were read
                if sender_id in user_sockets:
                    for socket_id in user_sockets[sender_id]:
                        emit('messages_read', {
                            'reader_id': reader_id,
                            'count': affected_count
                        }, room=socket_id)
                
                print(f'Marked {affected_count} messages as read')
                
        except Exception as e:
            print(f'Error marking messages as read: {e}')

    @socketio.on('typing')
    def handle_typing(data):
        try:
            chat_id = data['chat_id']
            user_id = data['user_id']
            is_typing = data['is_typing']
            
            # Emit typing status to room (except sender)
            emit('user_typing', {
                'user_id': user_id,
                'is_typing': is_typing
            }, room=chat_id, include_self=False)
            
        except Exception as e:
            print(f'Error handling typing: {e}')

    return socketio