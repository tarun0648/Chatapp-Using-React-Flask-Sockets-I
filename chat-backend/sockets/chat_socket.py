# backend/sockets/chat_socket.py - FIXED BLUE TICK FOR DIRECT CHATS
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
                
                # Join user to their personal room for notifications
                join_room(f"user_{user_id}")
                
                # Emit to all users that this user is online
                socketio.emit('user_online', {'user_id': user_id}, broadcast=True)
                
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
                        socketio.emit('user_offline', {'user_id': user_id}, broadcast=True)
                
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
            
            print(f'User {user_id} attempting to join room: {chat_id}')
            
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
                    
                    # Ensure both users can join the same room
                    # Normalize room name to ensure consistency (smaller_id_larger_id)
                    user_ids.sort()
                    normalized_chat_id = f"{user_ids[0]}_{user_ids[1]}"
                    if chat_id != normalized_chat_id:
                        chat_id = normalized_chat_id
                        print(f'Normalized chat_id to: {chat_id}')
                    
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
            
            print(f'User {user_id} successfully joined room: {chat_id}')
            
            # Emit join confirmation
            emit('room_joined', {'chat_id': chat_id, 'status': 'success'})
            
        except Exception as e:
            print(f'Join error: {e}')
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
            
            chat_id = data['chat_id']
            print(f"Processing message for chat: {chat_id}")
            
            # For direct chats, normalize the chat_id
            if not chat_id.startswith('group_'):
                try:
                    user_ids = [int(x) for x in chat_id.split('_') if x.isdigit()]
                    if len(user_ids) == 2:
                        user_ids.sort()
                        normalized_chat_id = f"{user_ids[0]}_{user_ids[1]}"
                        if chat_id != normalized_chat_id:
                            chat_id = normalized_chat_id
                            print(f'Normalized chat_id to: {chat_id}')
                except (ValueError, IndexError):
                    pass
            
            # Save message to database first
            if data.get('group_id'):
                # Group message
                if not is_user_group_member(data['group_id'], user_id):
                    emit('error', {'message': 'Not authorized to send to this group'})
                    return
                
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
            
            if not message_id:
                print("Failed to save message to database")
                emit('error', {'message': 'Failed to save message'})
                return
            
            # Get the saved message data
            message_data = get_message_by_id(message_id)
            if not message_data:
                print("Failed to retrieve saved message")
                emit('error', {'message': 'Failed to retrieve message'})
                return
            
            print(f"Message saved with ID: {message_id}")
            
            # Clean up typing status for sender
            cleanup_typing_for_room(chat_id, user_id)
            
            # Prepare message data for emission
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
            
            print(f"Broadcasting message to room: {chat_id}")
            
            # Broadcast to the chat room
            socketio.emit('receive_message', message_payload, room=chat_id)
            
            # Also emit to individual user rooms for direct chats to ensure delivery
            if not data.get('group_id') and data.get('receiver_id'):
                receiver_id = data['receiver_id']
                sender_id = data['sender_id']
                
                # Emit to both users' personal rooms as backup
                socketio.emit('receive_message', message_payload, room=f"user_{receiver_id}")
                socketio.emit('receive_message', message_payload, room=f"user_{sender_id}")
                
                print(f"Also sent to individual user rooms: user_{receiver_id}, user_{sender_id}")
            
            # Send delivery confirmation to sender
            emit('message_delivered', {
                'message_id': message_id,
                'chat_id': chat_id
            })
            
            print(f"Message delivery completed for chat: {chat_id}")
                    
        except Exception as e:
            print(f'Error sending message: {e}')
            emit('error', {'message': f'Failed to send message: {str(e)}'})

    @socketio.on('mark_read')
    def handle_mark_read(data):
        """Handle marking messages as read - FIXED FOR BLUE TICK"""
        try:
            user_id = active_users.get(request.sid)
            if not user_id:
                return
            
            print(f"Marking messages as read: {data}")
            
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
                                'count': affected_count
                            }, room=f"user_{member['id']}")
                except Exception as e:
                    print(f"Error notifying group read status: {e}")
            else:
                # Direct message read - ENHANCED FOR BLUE TICK
                sender_id = data['sender_id']
                receiver_id = data['receiver_id']
                reader_id = data['reader_id']
                
                print(f"Direct chat read: sender={sender_id}, receiver={receiver_id}, reader={reader_id}")
                
                affected_count = mark_messages_as_read(sender_id, receiver_id, reader_id)
                
                if affected_count > 0:
                    # Create normalized chat_id for direct messages
                    user_ids = sorted([sender_id, receiver_id])
                    chat_id = f"{user_ids[0]}_{user_ids[1]}"
                    
                    # Enhanced read notification for blue tick
                    read_notification = {
                        'reader_id': reader_id,
                        'sender_id': sender_id,
                        'receiver_id': receiver_id,
                        'chat_id': chat_id,
                        'count': affected_count,
                        'type': 'direct_chat_read'
                    }
                    
                    print(f"Sending blue tick notification: {read_notification}")
                    
                    # Send to sender's personal room (CRITICAL FOR BLUE TICK)
                    socketio.emit('messages_read', read_notification, room=f"user_{sender_id}")
                    
                    # Also send to the chat room
                    socketio.emit('messages_read', read_notification, room=chat_id)
                    
                    # Send to all active sockets of the sender for redundancy
                    if sender_id in user_sockets:
                        for socket_id in user_sockets[sender_id]:
                            socketio.emit('messages_read', read_notification, room=socket_id)
                    
                    print(f'✅ Blue tick notification sent to user {sender_id} - {affected_count} messages read by {reader_id}')
                else:
                    print(f"No messages were marked as read for sender {sender_id}")
            
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
            
            print(f"Typing event: user {user_id}, chat {chat_id}, typing: {is_typing}")
            
            # Verify user is authenticated
            if user_id != active_users.get(request.sid):
                print(f"User {user_id} not authenticated for typing")
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
                            print(f'Normalized typing chat_id to: {chat_id}')
                        
                        # Verify user is part of the conversation
                        if user_id not in user_ids:
                            print(f"User {user_id} not part of direct chat {chat_id}")
                            return
                except (ValueError, IndexError):
                    print(f"Invalid chat ID format for typing: {chat_id}")
                    return
            else:
                # Verify user can send to this group
                group_id = int(chat_id.split('_')[1])
                if not is_user_group_member(group_id, user_id):
                    print(f"User {user_id} not member of group {group_id}")
                    return
            
            if is_typing:
                start_typing(chat_id, user_id)
            else:
                stop_typing(chat_id, user_id)
            
        except Exception as e:
            print(f'Error handling typing: {e}')

    # Helper functions for typing management
    def start_typing(chat_id, user_id):
        """Start typing indicator for user in chat"""
        try:
            print(f"Starting typing: user {user_id} in room {chat_id}")
            
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
            
            # Emit typing status to room (except sender)
            typing_event = {
                'user_id': user_id,
                'is_typing': True,
                'chat_id': chat_id
            }
            
            socketio.emit('user_typing', typing_event, room=chat_id, include_self=False)
            
            # For direct chats, also emit to both user rooms to ensure delivery
            if not chat_id.startswith('group_'):
                try:
                    user_ids = [int(x) for x in chat_id.split('_') if x.isdigit()]
                    for uid in user_ids:
                        if uid != user_id:  # Don't send to self
                            socketio.emit('user_typing', typing_event, room=f"user_{uid}")
                except (ValueError, IndexError):
                    pass
            
            print(f"Broadcasted typing start to room {chat_id}")
            
        except Exception as e:
            print(f'Error starting typing: {e}')

    def stop_typing(chat_id, user_id):
        """Stop typing indicator for user in chat"""
        try:
            print(f"Stopping typing: user {user_id} in room {chat_id}")
            
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
            
            # Emit stop typing status to room (except sender)
            typing_event = {
                'user_id': user_id,
                'is_typing': False,
                'chat_id': chat_id
            }
            
            socketio.emit('user_typing', typing_event, room=chat_id, include_self=False)
            
            # For direct chats, also emit to both user rooms to ensure delivery
            if not chat_id.startswith('group_'):
                try:
                    user_ids = [int(x) for x in chat_id.split('_') if x.isdigit()]
                    for uid in user_ids:
                        if uid != user_id:  # Don't send to self
                            socketio.emit('user_typing', typing_event, room=f"user_{uid}")
                except (ValueError, IndexError):
                    pass
            
            print(f"Broadcasted typing stop to room {chat_id}")
            
        except Exception as e:
            print(f'Error stopping typing: {e}')

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
                    'chat_id': chat_id
                }
                socketio.emit('user_typing', typing_event, room=chat_id, include_self=False)
            
        except Exception as e:
            print(f'Error cleaning up typing for room: {e}')

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
            print(f'Error cleaning up user typing: {e}')

    return socketio