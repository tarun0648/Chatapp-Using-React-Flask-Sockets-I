# backend/sockets/chat_socket.py - COMPLETE FIX
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
        print(f'🔌 Client connected: {request.sid}')
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
                
                # Join user to their personal room for notifications
                join_room(f"user_{user_id}")
                
                # Emit to all users that this user is online
                socketio.emit('user_online', {'user_id': user_id}, broadcast=True)
                
                print(f'✅ User {user_id} connected with socket {request.sid}')
                
        except Exception as e:
            print(f'❌ Connect error: {e}')

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle socket disconnection"""
        print(f'🔌 Client disconnected: {request.sid}')
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
                        socketio.emit('user_offline', {'user_id': user_id}, broadcast=True)
                
                # Clean up user rooms
                if user_id in user_rooms:
                    del user_rooms[user_id]
                
                print(f'❌ User {user_id} disconnected')
                
        except Exception as e:
            print(f'❌ Disconnect error: {e}')

    @socketio.on('join')
    def handle_join(data):
        """Handle user joining a chat room"""
        try:
            chat_id = data['chat_id']
            user_id = active_users.get(request.sid)
            
            if not user_id:
                emit('error', {'message': 'User not authenticated'})
                return
            
            print(f'🏠 User {user_id} joining room: {chat_id}')
            
            # Normalize direct chat IDs
            if not chat_id.startswith('group_'):
                try:
                    user_ids = [int(x) for x in chat_id.split('_') if x.isdigit()]
                    if len(user_ids) == 2:
                        user_ids.sort()
                        normalized_chat_id = f"{user_ids[0]}_{user_ids[1]}"
                        
                        # Verify user is part of the conversation
                        if user_id not in user_ids:
                            emit('error', {'message': 'Not authorized to join this chat'})
                            return
                        
                        chat_id = normalized_chat_id
                        print(f'📝 Normalized chat ID: {chat_id}')
                    else:
                        emit('error', {'message': 'Invalid direct chat ID'})
                        return
                except (ValueError, IndexError):
                    emit('error', {'message': 'Invalid chat ID format'})
                    return
            else:
                # Group chat verification
                group_id = int(chat_id.split('_')[1])
                if not is_user_group_member(group_id, user_id):
                    emit('error', {'message': 'Not authorized to join this group'})
                    return
            
            # Join the room
            join_room(chat_id)
            
            # Track user rooms
            if user_id not in user_rooms:
                user_rooms[user_id] = []
            if chat_id not in user_rooms[user_id]:
                user_rooms[user_id].append(chat_id)
            
            print(f'✅ User {user_id} joined room: {chat_id}')
            
            # Emit join confirmation
            emit('room_joined', {'chat_id': chat_id, 'status': 'success'})
            
        except Exception as e:
            print(f'❌ Join error: {e}')
            emit('error', {'message': f'Failed to join room: {str(e)}'})

    @socketio.on('leave')
    def handle_leave(data):
        """Handle user leaving a chat room"""
        try:
            chat_id = data['chat_id']
            user_id = active_users.get(request.sid)
            
            leave_room(chat_id)
            cleanup_typing_for_room(chat_id, user_id)
            
            if user_id and user_id in user_rooms and chat_id in user_rooms[user_id]:
                user_rooms[user_id].remove(chat_id)
            
            print(f'👋 User {user_id} left room: {chat_id}')
            
        except Exception as e:
            print(f'❌ Leave error: {e}')

    @socketio.on('send_message')
    def handle_send_message(data):
        """Handle sending a message - FIXED FOR REAL-TIME"""
        try:
            user_id = active_users.get(request.sid)
            if not user_id:
                emit('error', {'message': 'User not authenticated'})
                return
            
            if not data.get('content') or not data.get('content').strip():
                emit('error', {'message': 'Message content cannot be empty'})
                return
            
            chat_id = data['chat_id']
            print(f'💬 Sending message to chat: {chat_id}')
            
            # Normalize direct chat ID
            if not chat_id.startswith('group_'):
                try:
                    user_ids = [int(x) for x in chat_id.split('_') if x.isdigit()]
                    if len(user_ids) == 2:
                        user_ids.sort()
                        normalized_chat_id = f"{user_ids[0]}_{user_ids[1]}"
                        chat_id = normalized_chat_id
                        print(f'📝 Normalized message chat ID: {chat_id}')
                except (ValueError, IndexError):
                    pass
            
            # Save message to database
            if data.get('group_id'):
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
            
            if not message_id:
                print(f'❌ Failed to save message to database')
                emit('error', {'message': 'Failed to save message'})
                return
            
            # Get the saved message data
            message_data = get_message_by_id(message_id)
            if not message_data:
                print(f'❌ Failed to retrieve saved message')
                emit('error', {'message': 'Failed to retrieve message'})
                return
            
            print(f'✅ Message saved with ID: {message_id}')
            
            # Clean up typing
            cleanup_typing_for_room(chat_id, user_id)
            
            # Prepare message payload
            message_payload = {
                'id': message_data['id'],
                'sender_id': message_data['sender_id'],
                'receiver_id': message_data.get('receiver_id'),
                'group_id': message_data.get('group_id'),
                'content': message_data['content'],
                'status': 'delivered',
                'sender_username': message_data.get('sender_username'),
                'sender_name': message_data.get('sender_name'),
                'sender_picture': message_data.get('sender_picture'),
                'timestamp': str(message_data.get('timestamp'))
            }
            
            print(f'📤 Broadcasting message to room: {chat_id}')
            print(f'📤 Message payload: {message_payload}')
            
            # CRITICAL: Broadcast to room
            socketio.emit('receive_message', message_payload, room=chat_id)
            
            # For direct chats, ALSO send to both user personal rooms
            if not data.get('group_id') and data.get('receiver_id'):
                receiver_id = data['receiver_id']
                sender_id = data['sender_id']
                
                print(f'📤 DIRECT CHAT: Sending to user_{receiver_id} and user_{sender_id}')
                
                # Send to receiver's personal room
                socketio.emit('receive_message', message_payload, room=f"user_{receiver_id}")
                
                # Send to sender's personal room
                socketio.emit('receive_message', message_payload, room=f"user_{sender_id}")
                
                # Send to ALL active sockets of both users
                for uid in [receiver_id, sender_id]:
                    if uid in user_sockets:
                        for socket_id in user_sockets[uid]:
                            socketio.emit('receive_message', message_payload, room=socket_id)
                            print(f'📤 Sent to socket {socket_id} for user {uid}')
            
            # Send delivery confirmation to sender
            emit('message_delivered', {
                'message_id': message_id,
                'chat_id': chat_id
            })
            
            print(f'✅ Message broadcast completed for chat: {chat_id}')
                    
        except Exception as e:
            print(f'❌ Error sending message: {e}')
            import traceback
            traceback.print_exc()
            emit('error', {'message': f'Failed to send message: {str(e)}'})

    @socketio.on('mark_read')
    def handle_mark_read(data):
        """Handle marking messages as read - FIXED FOR BLUE TICK"""
        try:
            user_id = active_users.get(request.sid)
            if not user_id:
                return
            
            print(f'📖 Mark read request: {data}')
            
            if data.get('group_id'):
                # Group message read
                if not is_user_group_member(data['group_id'], user_id):
                    return
                
                affected_count = mark_group_messages_as_read(data['group_id'], data['reader_id'])
                
                try:
                    members = get_group_members(data['group_id'])
                    for member in members:
                        if member['id'] != data['reader_id']:
                            socketio.emit('messages_read', {
                                'reader_id': data['reader_id'],
                                'group_id': data['group_id'],
                                'count': affected_count
                            }, room=f"user_{member['id']}")
                except Exception as e:
                    print(f'❌ Error notifying group read status: {e}')
            else:
                # DIRECT MESSAGE READ - BLUE TICK FIX
                sender_id = data['sender_id']
                receiver_id = data['receiver_id']
                reader_id = data['reader_id']
                
                print(f'🔵 BLUE TICK: Processing read for sender={sender_id}, reader={reader_id}')
                
                # Mark messages as read in database
                affected_count = mark_messages_as_read(sender_id, receiver_id, reader_id)
                print(f'🔵 BLUE TICK: {affected_count} messages marked as read in DB')
                
                if affected_count > 0:
                    # Create blue tick notification
                    blue_tick_data = {
                        'type': 'blue_tick',
                        'sender_id': sender_id,
                        'reader_id': reader_id,
                        'receiver_id': receiver_id,
                        'count': affected_count,
                        'chat_id': data.get('chat_id')
                    }
                    
                    print(f'🔵 BLUE TICK: Sending notification to sender {sender_id}')
                    print(f'🔵 BLUE TICK: Notification data: {blue_tick_data}')
                    
                    # Send to sender's personal room
                    socketio.emit('messages_read', blue_tick_data, room=f"user_{sender_id}")
                    
                    # Send to ALL active sockets of the sender
                    if sender_id in user_sockets:
                        for socket_id in user_sockets[sender_id]:
                            socketio.emit('messages_read', blue_tick_data, room=socket_id)
                            print(f'🔵 BLUE TICK: Sent to socket {socket_id}')
                    
                    # Also send to the chat room
                    if data.get('chat_id'):
                        socketio.emit('messages_read', blue_tick_data, room=data['chat_id'])
                    
                    print(f'🔵 ✅ BLUE TICK: Notifications sent successfully')
                else:
                    print(f'🔵 ❌ BLUE TICK: No messages were marked as read')
            
            print(f'📖 Mark read completed: {affected_count} messages')
                
        except Exception as e:
            print(f'❌ Error marking messages as read: {e}')
            import traceback
            traceback.print_exc()

    @socketio.on('typing')
    def handle_typing(data):
        """Handle typing indicators"""
        try:
            chat_id = data['chat_id']
            user_id = data['user_id']
            is_typing = data['is_typing']
            
            print(f'⌨️ Typing event: user {user_id}, chat {chat_id}, typing: {is_typing}')
            
            if user_id != active_users.get(request.sid):
                return
            
            # Normalize direct chat ID
            if not chat_id.startswith('group_'):
                try:
                    user_ids = [int(x) for x in chat_id.split('_') if x.isdigit()]
                    if len(user_ids) == 2:
                        user_ids.sort()
                        normalized_chat_id = f"{user_ids[0]}_{user_ids[1]}"
                        chat_id = normalized_chat_id
                        
                        if user_id not in user_ids:
                            return
                except (ValueError, IndexError):
                    return
            else:
                group_id = int(chat_id.split('_')[1])
                if not is_user_group_member(group_id, user_id):
                    return
            
            if is_typing:
                start_typing(chat_id, user_id)
            else:
                stop_typing(chat_id, user_id)
            
        except Exception as e:
            print(f'❌ Error handling typing: {e}')

    def start_typing(chat_id, user_id):
        """Start typing indicator"""
        try:
            if chat_id not in typing_users:
                typing_users[chat_id] = {}
            if chat_id not in typing_timers:
                typing_timers[chat_id] = {}
            
            if user_id in typing_timers.get(chat_id, {}):
                typing_timers[chat_id][user_id].cancel()
            
            typing_users[chat_id][user_id] = time.time()
            
            timer = Timer(3.0, lambda: stop_typing(chat_id, user_id))
            typing_timers[chat_id][user_id] = timer
            timer.start()
            
            typing_event = {
                'user_id': user_id,
                'is_typing': True,
                'chat_id': chat_id
            }
            
            # Emit to room
            socketio.emit('user_typing', typing_event, room=chat_id, include_self=False)
            
            # For direct chats, also emit to user rooms
            if not chat_id.startswith('group_'):
                try:
                    user_ids = [int(x) for x in chat_id.split('_') if x.isdigit()]
                    for uid in user_ids:
                        if uid != user_id:
                            socketio.emit('user_typing', typing_event, room=f"user_{uid}")
                except (ValueError, IndexError):
                    pass
            
        except Exception as e:
            print(f'❌ Error starting typing: {e}')

    def stop_typing(chat_id, user_id):
        """Stop typing indicator"""
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
            
            typing_event = {
                'user_id': user_id,
                'is_typing': False,
                'chat_id': chat_id
            }
            
            socketio.emit('user_typing', typing_event, room=chat_id, include_self=False)
            
            if not chat_id.startsWith('group_'):
                try:
                    user_ids = [int(x) for x in chat_id.split('_') if x.isdigit()]
                    for uid in user_ids:
                        if uid != user_id:
                            socketio.emit('user_typing', typing_event, room=f"user_{uid}")
                except (ValueError, IndexError):
                    pass
            
        except Exception as e:
            print(f'❌ Error stopping typing: {e}')

    def cleanup_typing_for_room(chat_id, user_id):
        """Clean up typing for room"""
        try:
            if user_id and chat_id in typing_users and user_id in typing_users[chat_id]:
                del typing_users[chat_id][user_id]
                if not typing_users[chat_id]:
                    del typing_users[chat_id]
            
            if user_id and chat_id in typing_timers and user_id in typing_timers[chat_id]:
                typing_timers[chat_id][user_id].cancel()
                del typing_timers[chat_id][user_id]
                if not typing_timers[chat_id]:
                    del typing_timers[chat_id]
            
        except Exception as e:
            print(f'❌ Error cleaning typing: {e}')

    def cleanup_user_typing(user_id):
        """Clean up all typing for user"""
        try:
            rooms_to_clean = []
            for chat_id in list(typing_users.keys()):
                if user_id in typing_users[chat_id]:
                    rooms_to_clean.append(chat_id)
            
            for chat_id in rooms_to_clean:
                stop_typing(chat_id, user_id)
                        
        except Exception as e:
            print(f'❌ Error cleaning user typing: {e}')

    return socketio