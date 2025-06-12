from flask_socketio import emit, join_room, leave_room, disconnect
from flask import request
from models.message import save_message, mark_messages_as_read, get_message_by_id, mark_group_messages_as_read
from models.user import update_user_online_status, get_user_by_id
from models.group import get_group_members, is_user_group_member
import time
from threading import Timer

# Store user sessions and state
active_users = {}  # {socket_id: user_id}
user_sockets = {}  # {user_id: [socket_ids]}
user_rooms = {}    # {user_id: [room_ids]}
typing_users = {}  # {room_id: {user_id: timestamp}}
typing_timers = {} # {room_id: {user_id: Timer}}

def socketio_init(socketio):
    """Initialize all socket event handlers"""
    
    @socketio.on('connect')
    def handle_connect(auth):
        """Handle new socket connection"""
        print(f'Client connected: {request.sid}')
        try:
            token = auth.get('token') if auth else None
            if token:
                user_id = int(token)
                
                # Store user session
                active_users[request.sid] = user_id
                if user_id not in user_sockets:
                    user_sockets[user_id] = []
                if request.sid not in user_sockets[user_id]:
                    user_sockets[user_id].append(request.sid)
                
                # Update online status
                update_user_online_status(user_id, True)
                
                # Join user to their personal room for direct messages
                join_room(f"user_{user_id}")
                
                # Emit to all users that this user is online
                emit('user_online', {'user_id': user_id}, broadcast=True)
                
                print(f'User {user_id} connected with socket {request.sid}')
                
        except Exception as e:
            print(f'Connect error: {e}')

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle socket disconnection"""
        print(f'Client disconnected: {request.sid}')
        try:
            if request.sid in active_users:
                user_id = active_users[request.sid]
                
                # Clean up typing timers for this user
                cleanup_user_typing(user_id)
                
                # Remove from active sessions
                del active_users[request.sid]
                if user_id in user_sockets and request.sid in user_sockets[user_id]:
                    user_sockets[user_id].remove(request.sid)
                    if not user_sockets[user_id]:  # No more active sessions
                        del user_sockets[user_id]
                        # Update offline status
                        update_user_online_status(user_id, False)
                        # Emit to all users that this user is offline
                        emit('user_offline', {'user_id': user_id}, broadcast=True)
                
                # Clean up user rooms
                if user_id in user_rooms:
                    del user_rooms[user_id]
                
                print(f'User {user_id} disconnected')
                
        except Exception as e:
            print(f'Disconnect error: {e}')

    @socketio.on('join')
    def handle_join(data):
        """Handle user joining a chat room"""
        try:
            chat_id = data['chat_id']
            user_id = active_users.get(request.sid)
            
            if not user_id:
                emit('error', {'message': 'User not authenticated'})
                return
            
            # Verify user can join this room
            if chat_id.startswith('group_'):
                group_id = int(chat_id.split('_')[1])
                if not is_user_group_member(group_id, user_id):
                    emit('error', {'message': 'Not authorized to join this group'})
                    return
            
            join_room(chat_id)
            
            # Track user rooms
            if user_id not in user_rooms:
                user_rooms[user_id] = []
            if chat_id not in user_rooms[user_id]:
                user_rooms[user_id].append(chat_id)
            
            print(f'User {user_id} joined room: {chat_id}')
            
            # Emit join confirmation
            emit('room_joined', {'chat_id': chat_id, 'status': 'success'})
            
        except Exception as e:
            print(f'Join error: {e}')
            emit('error', {'message': 'Failed to join room'})

    @socketio.on('leave')
    def handle_leave(data):
        """Handle user leaving a chat room"""
        try:
            chat_id = data['chat_id']
            user_id = active_users.get(request.sid)
            
            leave_room(chat_id)
            
            # Clean up typing status when leaving
            cleanup_typing_for_room(chat_id, user_id)
            
            # Remove from user rooms tracking
            if user_id and user_id in user_rooms and chat_id in user_rooms[user_id]:
                user_rooms[user_id].remove(chat_id)
            
            print(f'User {user_id} left room: {chat_id}')
            
        except Exception as e:
            print(f'Leave error: {e}')

    @socketio.on('send_message')
    def handle_send_message(data):
        """Handle sending a message"""
        try:
            user_id = active_users.get(request.sid)
            if not user_id:
                emit('error', {'message': 'User not authenticated'})
                return
            
            # Validate message data
            if not data.get('content') or not data.get('content').strip():
                emit('error', {'message': 'Message content cannot be empty'})
                return
            
            # Save message to database first
            if data.get('group_id'):
                # Verify user is member of the group
                if not is_user_group_member(data['group_id'], user_id):
                    emit('error', {'message': 'Not authorized to send to this group'})
                    return
                
                message_id = save_message(
                    sender_id=data['sender_id'],
                    content=data['content'],
                    group_id=data['group_id']
                )
            else:
                message_id = save_message(
                    sender_id=data['sender_id'],
                    receiver_id=data['receiver_id'], 
                    content=data['content']
                )
            
            if message_id:
                message_data = get_message_by_id(message_id)
                if message_data:
                    chat_id = data['chat_id']
                    
                    # Clean up typing status for sender
                    cleanup_typing_for_room(chat_id, user_id)
                    
                    # Prepare message data for emission
                    message_payload = {
                        'id': message_data['id'],
                        'sender_id': message_data['sender_id'],
                        'receiver_id': message_data.get('receiver_id'),
                        'group_id': message_data.get('group_id'),
                        'content': message_data['content'],
                        'status': 'sent',
                        'sender_username': message_data.get('sender_username'),
                        'sender_name': message_data.get('sender_name'),
                        'sender_picture': message_data.get('sender_picture'),
                        'timestamp': str(message_data.get('timestamp'))
                    }
                    
                    # Emit to the chat room
                    emit('receive_message', message_payload, room=chat_id)
                    
                    # For direct messages, also emit to both users' personal rooms
                    if not data.get('group_id') and data.get('receiver_id'):
                        receiver_id = data['receiver_id']
                        sender_id = data['sender_id']
                        
                        # Emit to receiver's personal room (for notifications)
                        emit('new_message_notification', {
                            'chat_id': chat_id,
                            'sender_name': message_data.get('sender_name'),
                            'content': message_data['content'],
                            'sender_picture': message_data.get('sender_picture'),
                            'timestamp': str(message_data.get('timestamp'))
                        }, room=f"user_{receiver_id}")
                        
                        # Emit to sender's personal room for chat list updates
                        emit('new_message_notification', {
                            'chat_id': chat_id,
                            'sender_name': 'You',
                            'content': message_data['content'],
                            'timestamp': str(message_data.get('timestamp'))
                        }, room=f"user_{sender_id}")
                    
                    # For group messages, emit to all group members
                    elif data.get('group_id'):
                        members = get_group_members(data['group_id'])
                        for member in members:
                            if member['id'] != data['sender_id']:  # Don't send to sender
                                emit('new_message_notification', {
                                    'chat_id': chat_id,
                                    'sender_name': message_data.get('sender_name'),
                                    'content': message_data['content'],
                                    'sender_picture': message_data.get('sender_picture'),
                                    'is_group': True,
                                    'timestamp': str(message_data.get('timestamp'))
                                }, room=f"user_{member['id']}")
                    
                    # Mark as delivered for sender
                    emit('message_delivered', {
                        'message_id': message_id,
                        'chat_id': chat_id
                    }, room=request.sid)
                    
            else:
                emit('error', {'message': 'Failed to save message'})
                    
        except Exception as e:
            print(f'Error sending message: {e}')
            emit('error', {'message': 'Failed to send message'})

    @socketio.on('mark_read')
    def handle_mark_read(data):
        """Handle marking messages as read"""
        try:
            user_id = active_users.get(request.sid)
            if not user_id:
                return
            
            if data.get('group_id'):
                # Verify user is member of the group
                if not is_user_group_member(data['group_id'], user_id):
                    return
                
                affected_count = mark_group_messages_as_read(data['group_id'], data['reader_id'])
                
                # Notify all group members that messages were read
                members = get_group_members(data['group_id'])
                for member in members:
                    if member['id'] != data['reader_id']:
                        emit('messages_read', {
                            'reader_id': data['reader_id'],
                            'group_id': data['group_id'],
                            'count': affected_count
                        }, room=f"user_{member['id']}")
            else:
                sender_id = data['sender_id']
                receiver_id = data['receiver_id']
                reader_id = data['reader_id']
                
                affected_count = mark_messages_as_read(sender_id, receiver_id, reader_id)
                
                if affected_count > 0:
                    # Notify sender that messages were read
                    emit('messages_read', {
                        'reader_id': reader_id,
                        'count': affected_count
                    }, room=f"user_{sender_id}")
            
            print(f'Marked {affected_count} messages as read')
                
        except Exception as e:
            print(f'Error marking messages as read: {e}')

    @socketio.on('typing')
    def handle_typing(data):
        """Handle typing indicators"""
        try:
            chat_id = data['chat_id']
            user_id = data['user_id']
            is_typing = data['is_typing']
            
            # Verify user is authenticated
            if user_id != active_users.get(request.sid):
                return
            
            # Verify user can send to this room
            if chat_id.startswith('group_'):
                group_id = int(chat_id.split('_')[1])
                if not is_user_group_member(group_id, user_id):
                    return
            
            if is_typing:
                start_typing(chat_id, user_id)
            else:
                stop_typing(chat_id, user_id)
            
        except Exception as e:
            print(f'Error handling typing: {e}')

    @socketio.on('get_online_users')
    def handle_get_online_users():
        """Get list of currently online users"""
        try:
            online_user_ids = list(user_sockets.keys())
            emit('online_users_list', {'user_ids': online_user_ids})
        except Exception as e:
            print(f'Error getting online users: {e}')

    @socketio.on('ping')
    def handle_ping():
        """Handle ping for connection keepalive"""
        emit('pong')

    @socketio.on('force_disconnect')
    def handle_force_disconnect():
        """Force disconnect user (admin function)"""
        try:
            user_id = active_users.get(request.sid)
            if user_id:
                # Clean up all user sessions
                if user_id in user_sockets:
                    for socket_id in user_sockets[user_id].copy():
                        if socket_id in active_users:
                            del active_users[socket_id]
                        disconnect(socket_id)
                    del user_sockets[user_id]
                
                cleanup_user_typing(user_id)
                update_user_online_status(user_id, False)
                
        except Exception as e:
            print(f'Error force disconnecting: {e}')

    # Helper functions for typing management
    def start_typing(chat_id, user_id):
        """Start typing indicator for user in chat"""
        try:
            if chat_id not in typing_users:
                typing_users[chat_id] = {}
            if chat_id not in typing_timers:
                typing_timers[chat_id] = {}
            
            # Cancel existing timer if any
            if user_id in typing_timers[chat_id]:
                typing_timers[chat_id][user_id].cancel()
            
            # Mark user as typing
            typing_users[chat_id][user_id] = time.time()
            
            # Set auto-stop timer (3 seconds)
            timer = Timer(3.0, lambda: stop_typing(chat_id, user_id))
            typing_timers[chat_id][user_id] = timer
            timer.start()
            
            # Emit typing status to room (except sender)
            emit('user_typing', {
                'user_id': user_id,
                'is_typing': True,
                'chat_id': chat_id
            }, room=chat_id, include_self=False)
            
            # For direct messages, also emit to the other user's personal room
            if not chat_id.startswith('group_'):
                user_ids = chat_id.split('_')
                try:
                    other_user_id = int([uid for uid in user_ids if int(uid) != user_id][0])
                    emit('user_typing', {
                        'user_id': user_id,
                        'is_typing': True,
                        'chat_id': chat_id
                    }, room=f"user_{other_user_id}")
                except (ValueError, IndexError):
                    pass
            
        except Exception as e:
            print(f'Error starting typing: {e}')

    def stop_typing(chat_id, user_id):
        """Stop typing indicator for user in chat"""
        try:
            # Remove from typing users
            if chat_id in typing_users and user_id in typing_users[chat_id]:
                del typing_users[chat_id][user_id]
                if not typing_users[chat_id]:  # Remove empty dict
                    del typing_users[chat_id]
            
            # Cancel and remove timer
            if chat_id in typing_timers and user_id in typing_timers[chat_id]:
                typing_timers[chat_id][user_id].cancel()
                del typing_timers[chat_id][user_id]
                if not typing_timers[chat_id]:  # Remove empty dict
                    del typing_timers[chat_id]
            
            # Emit stop typing status to room (except sender)
            emit('user_typing', {
                'user_id': user_id,
                'is_typing': False,
                'chat_id': chat_id
            }, room=chat_id, include_self=False)
            
            # For direct messages, also emit to the other user's personal room
            if not chat_id.startswith('group_'):
                user_ids = chat_id.split('_')
                try:
                    other_user_id = int([uid for uid in user_ids if int(uid) != user_id][0])
                    emit('user_typing', {
                        'user_id': user_id,
                        'is_typing': False,
                        'chat_id': chat_id
                    }, room=f"user_{other_user_id}")
                except (ValueError, IndexError):
                    pass
            
        except Exception as e:
            print(f'Error stopping typing: {e}')

    def cleanup_typing_for_room(chat_id, user_id):
        """Clean up typing status for user in specific room"""
        try:
            if chat_id in typing_users and user_id in typing_users[chat_id]:
                del typing_users[chat_id][user_id]
                if not typing_users[chat_id]:
                    del typing_users[chat_id]
            
            if chat_id in typing_timers and user_id in typing_timers[chat_id]:
                typing_timers[chat_id][user_id].cancel()
                del typing_timers[chat_id][user_id]
                if not typing_timers[chat_id]:
                    del typing_timers[chat_id]
            
            # Emit stop typing
            emit('user_typing', {
                'user_id': user_id,
                'is_typing': False,
                'chat_id': chat_id
            }, room=chat_id, include_self=False)
            
        except Exception as e:
            print(f'Error cleaning up typing for room: {e}')

    def cleanup_user_typing(user_id):
        """Clean up all typing timers for a user"""
        try:
            # Clean up typing status
            rooms_to_clean = []
            for chat_id in typing_users:
                if user_id in typing_users[chat_id]:
                    rooms_to_clean.append(chat_id)
            
            for chat_id in rooms_to_clean:
                stop_typing(chat_id, user_id)
            
            # Clean up timers
            timer_rooms_to_clean = []
            for chat_id in typing_timers:
                if user_id in typing_timers[chat_id]:
                    timer_rooms_to_clean.append(chat_id)
            
            for chat_id in timer_rooms_to_clean:
                if user_id in typing_timers[chat_id]:
                    typing_timers[chat_id][user_id].cancel()
                    del typing_timers[chat_id][user_id]
                    if not typing_timers[chat_id]:
                        del typing_timers[chat_id]
                        
        except Exception as e:
            print(f'Error cleaning up user typing: {e}')

    def get_room_typing_users(chat_id):
        """Get list of users currently typing in a room"""
        try:
            if chat_id in typing_users:
                current_time = time.time()
                active_typers = []
                
                # Remove expired typing status (older than 5 seconds)
                expired_users = []
                for user_id, timestamp in typing_users[chat_id].items():
                    if current_time - timestamp > 5:
                        expired_users.append(user_id)
                    else:
                        active_typers.append(user_id)
                
                # Clean up expired users
                for user_id in expired_users:
                    stop_typing(chat_id, user_id)
                
                return active_typers
            return []
        except Exception as e:
            print(f'Error getting room typing users: {e}')
            return []

    def broadcast_user_count():
        """Broadcast current online user count"""
        try:
            online_count = len(user_sockets)
            emit('user_count_update', {'count': online_count}, broadcast=True)
        except Exception as e:
            print(f'Error broadcasting user count: {e}')

    # Periodic cleanup function (called every 30 seconds)
    def periodic_cleanup():
        """Clean up stale typing indicators and connections"""
        try:
            current_time = time.time()
            
            # Clean up old typing indicators
            for chat_id in list(typing_users.keys()):
                for user_id in list(typing_users[chat_id].keys()):
                    if current_time - typing_users[chat_id][user_id] > 10:  # 10 seconds timeout
                        stop_typing(chat_id, user_id)
            
            # Clean up disconnected sockets
            for socket_id in list(active_users.keys()):
                # This would require additional checks in a real implementation
                pass
                
        except Exception as e:
            print(f'Error in periodic cleanup: {e}')

    return socketio