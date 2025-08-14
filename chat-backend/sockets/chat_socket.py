# backend/sockets/chat_socket.py - ENHANCED WITH LOGOUT HANDLER
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
                
                # Update online status IMMEDIATELY
                update_user_online_status(user_id, True)
                
                # Join user to their personal room for notifications
                join_room(f"user_{user_id}")
                
                # ✅ FIXED: Emit online status to ALL users immediately
                online_data = {'user_id': user_id, 'timestamp': time.time()}
                socketio.emit('user_online', online_data)
                
                print(f'✅ User {user_id} connected with socket {request.sid}')
                
                # Send immediate confirmation
                emit('connection_confirmed', {'user_id': user_id, 'status': 'online'})
                
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
                        # Update offline status IMMEDIATELY
                        update_user_online_status(user_id, False)
                        # ✅ FIXED: Emit offline status to ALL users immediately
                        offline_data = {'user_id': user_id, 'timestamp': time.time()}
                        socketio.emit('user_offline', offline_data)
                        print(f'🔴 User {user_id} went offline (disconnect)')
                
                # Clean up user rooms
                if user_id in user_rooms:
                    del user_rooms[user_id]
                
                print(f'✅ User {user_id} disconnected')
                
        except Exception as e:
            print(f'❌ Disconnect error: {e}')

    # ✅ NEW: Handle explicit logout
    @socketio.on('user_logout')
    def handle_user_logout(data):
        """Handle user logout event"""
        try:
            user_id = data.get('user_id')
            socket_user_id = active_users.get(request.sid)
            
            print(f'🚪 Logout event received for user {user_id}')
            
            # Verify the user is the one logging out
            if user_id and user_id == socket_user_id:
                # Clean up typing timers for this user
                cleanup_user_typing(user_id)
                
                # Update database status to offline IMMEDIATELY
                update_user_online_status(user_id, False)
                
                # Emit offline status to ALL users
                offline_data = {'user_id': user_id, 'timestamp': time.time(), 'reason': 'logout'}
                socketio.emit('user_offline', offline_data)
                
                # Clean up user sessions
                if user_id in user_sockets:
                    # Get all sockets for this user
                    user_socket_list = user_sockets[user_id].copy()
                    
                    # Remove all sockets for this user
                    for socket_id in user_socket_list:
                        if socket_id in active_users:
                            del active_users[socket_id]
                    
                    del user_sockets[user_id]
                
                # Clean up user rooms
                if user_id in user_rooms:
                    del user_rooms[user_id]
                
                print(f'🔴 User {user_id} logged out successfully - status set to offline')
                
                # Confirm logout to client
                emit('logout_confirmed', {'user_id': user_id, 'status': 'offline'})
                
            else:
                print(f'❌ Logout verification failed: {user_id} vs {socket_user_id}')
                
        except Exception as e:
            print(f'❌ Logout error: {e}')

    @socketio.on('join')
    def handle_join(data):
        """Handle user joining a chat room"""
        try:
            chat_id = data['chat_id']
            user_id = active_users.get(request.sid)
            
            if not user_id:
                emit('error', {'message': 'User not authenticated'})
                return
            
            print(f'🏠 User {user_id} attempting to join room: {chat_id}')
            
            # Verify user can join this room
            if chat_id.startswith('group_'):
                group_id = int(chat_id.split('_')[1])
                if not is_user_group_member(group_id, user_id):
                    emit('error', {'message': 'Not authorized to join this group'})
                    return
            else:
                # For direct chats, verify user is part of the conversation
                try:
                    user_ids = [int(x) for x in chat_id.split('_') if x.isdigit()]
                    if len(user_ids) != 2 or user_id not in user_ids:
                        emit('error', {'message': 'Not authorized to join this chat'})
                        return
                    
                    # Ensure both users can join the same room - normalize room name
                    user_ids.sort()
                    normalized_chat_id = f"{user_ids[0]}_{user_ids[1]}"
                    if chat_id != normalized_chat_id:
                        chat_id = normalized_chat_id
                        print(f'📝 Normalized chat_id to: {chat_id}')
                    
                except (ValueError, IndexError):
                    emit('error', {'message': 'Invalid chat ID format'})
                    return
            
            # Join the room
            join_room(chat_id)
            
            # Track user rooms
            if user_id not in user_rooms:
                user_rooms[user_id] = []
            if chat_id not in user_rooms[user_id]:
                user_rooms[user_id].append(chat_id)
            
            print(f'✅ User {user_id} successfully joined room: {chat_id}')
            
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
            
            # Clean up typing status when leaving
            cleanup_typing_for_room(chat_id, user_id)
            
            # Remove from user rooms tracking
            if user_id and user_id in user_rooms and chat_id in user_rooms[user_id]:
                user_rooms[user_id].remove(chat_id)
            
            print(f'🚪 User {user_id} left room: {chat_id}')
            
        except Exception as e:
            print(f'❌ Leave error: {e}')

    @socketio.on('send_message')
    def handle_send_message(data):
        """Handle sending messages"""
        try:
            user_id = active_users.get(request.sid)
            if not user_id:
                emit('error', {'message': 'User not authenticated'})
                return

            if not data.get('content') or not data.get('content').strip():
                emit('error', {'message': 'Message content cannot be empty'})
                return

            chat_id = data['chat_id']

            # Normalize direct chat ID
            if not chat_id.startswith('group_'):
                user_ids = [int(x) for x in chat_id.split('_') if x.isdigit()]
                if len(user_ids) == 2:
                    user_ids.sort()
                    chat_id = f"{user_ids[0]}_{user_ids[1]}"

            # Save the message
            if data.get('group_id'):
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
                emit('error', {'message': 'Failed to save message'})
                return

            message_data = get_message_by_id(message_id)
            if not message_data:
                emit('error', {'message': 'Failed to retrieve message'})
                return

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
                'timestamp': str(message_data.get('timestamp')),
                'chat_id': chat_id
            }

            print(f'📤 Broadcasting message to room: {chat_id}')
            
            # Send to chat room
            socketio.emit('receive_message', message_payload, room=chat_id)

            # Send real-time notification for ChatList updates
            notification_payload = {
                'chat_id': chat_id,
                'sender_id': message_data['sender_id'],
                'sender_name': message_data.get('sender_name'),
                'content': message_data['content'],
                'timestamp': str(message_data.get('timestamp')),
                'message_id': message_id
            }

            if message_data.get('group_id'):
                # Group chat notifications
                members = get_group_members(message_data['group_id'])
                for member in members:
                    if member['id'] != user_id:
                        socketio.emit('new_message_notification', notification_payload, room=f"user_{member['id']}")
                        print(f'📢 Sent group notification to user {member["id"]}')
            else:
                # Direct chat notifications for ChatList
                receiver_id = message_data.get('receiver_id')
                if receiver_id:
                    # Send to receiver
                    socketio.emit('new_message_notification', notification_payload, room=f"user_{receiver_id}")
                    print(f'📢 Sent direct chat notification to user {receiver_id}')
                    
                    # Also send to sender for their own chat list update
                    socketio.emit('new_message_notification', notification_payload, room=f"user_{user_id}")
                    print(f'📢 Sent chat list update to sender {user_id}')

            # Send delivery confirmation to sender
            emit('message_delivered', {'message_id': message_id, 'chat_id': chat_id})
            print(f'✅ Message {message_id} sent successfully')

        except Exception as e:
            print(f"❌ Send message error: {e}")
            emit('error', {'message': str(e)})

    @socketio.on('mark_read')
    def handle_mark_read(data):
        """Handle marking messages as read"""
        try:
            user_id = active_users.get(request.sid)
            if not user_id:
                return
            
            print(f"🔵 MARK READ EVENT: {data}")
            
            if data.get('group_id'):
                # Group message read
                if not is_user_group_member(data['group_id'], user_id):
                    return
                
                affected_count = mark_group_messages_as_read(data['group_id'], data['reader_id'])
                
                # Notify all group members
                try:
                    members = get_group_members(data['group_id'])
                    for member in members:
                        if member['id'] != data['reader_id']:
                            socketio.emit('messages_read', {
                                'reader_id': data['reader_id'],
                                'group_id': data['group_id'],
                                'count': affected_count,
                                'type': 'group_read'
                            }, room=f"user_{member['id']}")
                except Exception as e:
                    print(f"❌ Error notifying group read status: {e}")
            else:
                # Direct message read - BLUE TICK FIX
                sender_id = data['sender_id']
                receiver_id = data['receiver_id']
                reader_id = data['reader_id']
                
                print(f"🔵 DIRECT CHAT READ: sender={sender_id}, receiver={receiver_id}, reader={reader_id}")
                
                affected_count = mark_messages_as_read(sender_id, receiver_id, reader_id)
                
                if affected_count > 0:
                    # Create normalized chat_id for direct messages
                    user_ids = sorted([sender_id, receiver_id])
                    chat_id = f"{user_ids[0]}_{user_ids[1]}"
                    
                    # Enhanced blue tick notification
                    blue_tick_data = {
                        'sender_id': sender_id,
                        'receiver_id': receiver_id,
                        'reader_id': reader_id,
                        'chat_id': chat_id,
                        'count': affected_count,
                        'type': 'blue_tick',
                        'timestamp': time.time()
                    }
                    
                    print(f"🔵 SENDING BLUE TICK: {blue_tick_data}")
                    
                    # Multiple delivery methods for blue tick
                    # Method 1: Send to sender's personal room
                    socketio.emit('messages_read', blue_tick_data, room=f"user_{sender_id}")
                    print(f"🔵 Sent blue tick to user_{sender_id}")
                    
                    # Method 2: Send to chat room
                    socketio.emit('messages_read', blue_tick_data, room=chat_id)
                    print(f"🔵 Sent blue tick to room {chat_id}")
                    
                    # Method 3: Send to all sender's active sockets directly
                    if sender_id in user_sockets:
                        for socket_id in user_sockets[sender_id]:
                            socketio.emit('messages_read', blue_tick_data, room=socket_id)
                            print(f"🔵 Sent blue tick to socket {socket_id}")
                    
                    # Method 4: Broadcast with sender filter (backup)
                    socketio.emit('messages_read', blue_tick_data)
                    
                    print(f'🔵 ✅ BLUE TICK SENT SUCCESSFULLY - {affected_count} messages marked read')
                else:
                    print(f"🔵 ⚠️ No messages were marked as read")
            
        except Exception as e:
            print(f'❌ Error marking messages as read: {e}')

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
            
            # For direct chats, normalize the chat_id
            if not chat_id.startswith('group_'):
                try:
                    user_ids = [int(x) for x in chat_id.split('_') if x.isdigit()]
                    if len(user_ids) == 2:
                        user_ids.sort()
                        normalized_chat_id = f"{user_ids[0]}_{user_ids[1]}"
                        if chat_id != normalized_chat_id:
                            chat_id = normalized_chat_id
                        
                        # Verify user is part of the conversation
                        if user_id not in user_ids:
                            return
                except (ValueError, IndexError):
                    return
            else:
                # Verify user can send to this group
                group_id = int(chat_id.split('_')[1])
                if not is_user_group_member(group_id, user_id):
                    return
            
            if is_typing:
                start_typing(chat_id, user_id)
            else:
                stop_typing(chat_id, user_id)
            
        except Exception as e:
            print(f'❌ Error handling typing: {e}')

    # Optimized typing functions
    def start_typing(chat_id, user_id):
        """Start typing indicator for user in chat"""
        try:
            if chat_id not in typing_users:
                typing_users[chat_id] = {}
            if chat_id not in typing_timers:
                typing_timers[chat_id] = {}
            
            # Cancel existing timer if any
            if user_id in typing_timers.get(chat_id, {}):
                typing_timers[chat_id][user_id].cancel()
            
            # Mark user as typing
            typing_users[chat_id][user_id] = time.time()
            
            # Set auto-stop timer (3 seconds)
            timer = Timer(3.0, lambda: stop_typing(chat_id, user_id))
            typing_timers[chat_id][user_id] = timer
            timer.start()
            
            # Emit typing status
            typing_event = {
                'user_id': user_id,
                'is_typing': True,
                'chat_id': chat_id,
                'timestamp': time.time()
            }
            
            # Send to chat room (exclude sender)
            socketio.emit('user_typing', typing_event, room=chat_id, include_self=False)
            
            # For direct chats, ensure delivery to both users
            if not chat_id.startswith('group_'):
                try:
                    user_ids = [int(x) for x in chat_id.split('_') if x.isdigit()]
                    for uid in user_ids:
                        if uid != user_id:  # Don't send to self
                            socketio.emit('user_typing', typing_event, room=f"user_{uid}")
                except (ValueError, IndexError):
                    pass
            
        except Exception as e:
            print(f'❌ Error starting typing: {e}')

    def stop_typing(chat_id, user_id):
        """Stop typing indicator for user in chat"""
        try:
            # Remove from typing users
            if chat_id in typing_users and user_id in typing_users[chat_id]:
                del typing_users[chat_id][user_id]
                if not typing_users[chat_id]:
                    del typing_users[chat_id]
            
            # Cancel and remove timer
            if chat_id in typing_timers and user_id in typing_timers[chat_id]:
                typing_timers[chat_id][user_id].cancel()
                del typing_timers[chat_id][user_id]
                if not typing_timers[chat_id]:
                    del typing_timers[chat_id]
            
            # Emit stop typing status
            typing_event = {
                'user_id': user_id,
                'is_typing': False,
                'chat_id': chat_id,
                'timestamp': time.time()
            }
            
            # Send to chat room (exclude sender)
            socketio.emit('user_typing', typing_event, room=chat_id, include_self=False)
            
            # For direct chats, ensure delivery to both users
            if not chat_id.startswith('group_'):
                try:
                    user_ids = [int(x) for x in chat_id.split('_') if x.isdigit()]
                    for uid in user_ids:
                        if uid != user_id:  # Don't send to self
                            socketio.emit('user_typing', typing_event, room=f"user_{uid}")
                except (ValueError, IndexError):
                    pass
            
        except Exception as e:
            print(f'❌ Error stopping typing: {e}')

    def cleanup_typing_for_room(chat_id, user_id):
        """Clean up typing status for user in specific room"""
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
            
            # Emit stop typing
            if user_id:
                typing_event = {
                    'user_id': user_id,
                    'is_typing': False,
                    'chat_id': chat_id,
                    'timestamp': time.time()
                }
                socketio.emit('user_typing', typing_event, room=chat_id, include_self=False)
            
        except Exception as e:
            print(f'❌ Error cleaning up typing for room: {e}')

    def cleanup_user_typing(user_id):
        """Clean up all typing timers for a user"""
        try:
            # Clean up typing status
            rooms_to_clean = []
            for chat_id in list(typing_users.keys()):
                if user_id in typing_users[chat_id]:
                    rooms_to_clean.append(chat_id)
            
            for chat_id in rooms_to_clean:
                stop_typing(chat_id, user_id)
            
            # Clean up timers
            timer_rooms_to_clean = []
            for chat_id in list(typing_timers.keys()):
                if user_id in typing_timers[chat_id]:
                    timer_rooms_to_clean.append(chat_id)
            
            for chat_id in timer_rooms_to_clean:
                if user_id in typing_timers[chat_id]:
                    typing_timers[chat_id][user_id].cancel()
                    del typing_timers[chat_id][user_id]
                    if not typing_timers[chat_id]:
                        del typing_timers[chat_id]
                        
        except Exception as e:
            print(f'❌ Error cleaning up user typing: {e}')

    # New: Heartbeat for faster online/offline detection
    @socketio.on('heartbeat')
    def handle_heartbeat(data):
        """Handle client heartbeat for faster online status"""
        try:
            user_id = active_users.get(request.sid)
            if user_id:
                # Update last activity
                update_user_online_status(user_id, True)
                emit('heartbeat_ack', {'timestamp': time.time()})
        except Exception as e:
            print(f'❌ Heartbeat error: {e}')

    return socketio