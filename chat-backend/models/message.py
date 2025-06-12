from config import get_db
from datetime import datetime

def save_message(sender_id, receiver_id=None, content=None, group_id=None):
    """Save a new message to the database"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        if group_id:
            # Group message
            cursor.execute("""
                INSERT INTO messages (sender_id, content, group_id, delivered_at) 
                VALUES (%s, %s, %s, NOW())
            """, (sender_id, content, group_id))
        else:
            # Direct message
            cursor.execute("""
                INSERT INTO messages (sender_id, receiver_id, content, delivered_at) 
                VALUES (%s, %s, %s, NOW())
            """, (sender_id, receiver_id, content))
        
        message_id = cursor.lastrowid
        db.commit()
        cursor.close()
        return message_id
        
    except Exception as e:
        print(f"Error saving message: {e}")
        try:
            db.rollback()
        except:
            pass
        if 'cursor' in locals():
            cursor.close()
        return None

def get_messages(sender_id=None, receiver_id=None, group_id=None, limit=100):
    """Get messages for a chat or group"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        if group_id:
            # Get group messages
            cursor.execute("""
                SELECT m.*, 
                       s.username as sender_username,
                       s.name as sender_name,
                       s.profile_picture as sender_picture,
                       CASE 
                           WHEN m.read_at IS NOT NULL THEN 'read'
                           WHEN m.delivered_at IS NOT NULL THEN 'delivered'
                           ELSE 'sent'
                       END as status
                FROM messages m
                LEFT JOIN users s ON m.sender_id = s.id
                WHERE m.group_id = %s
                ORDER BY m.timestamp ASC
                LIMIT %s
            """, (group_id, limit))
        else:
            # Get direct messages
            cursor.execute("""
                SELECT m.*, 
                       s.username as sender_username,
                       s.name as sender_name,
                       s.profile_picture as sender_picture,
                       r.username as receiver_username,
                       CASE 
                           WHEN m.read_at IS NOT NULL THEN 'read'
                           WHEN m.delivered_at IS NOT NULL THEN 'delivered'
                           ELSE 'sent'
                       END as status
                FROM messages m
                LEFT JOIN users s ON m.sender_id = s.id
                LEFT JOIN users r ON m.receiver_id = r.id
                WHERE (sender_id = %s AND receiver_id = %s)
                   OR (sender_id = %s AND receiver_id = %s)
                ORDER BY timestamp ASC
                LIMIT %s
            """, (sender_id, receiver_id, receiver_id, sender_id, limit))
        
        messages = cursor.fetchall()
        cursor.close()
        return messages
        
    except Exception as e:
        print(f"Error fetching messages: {e}")
        if 'cursor' in locals():
            cursor.close()
        return []

def mark_group_messages_as_read(group_id, user_id):
    """Mark all unread group messages as read for a user"""
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            UPDATE messages 
            SET read_at = NOW(), is_read = TRUE
            WHERE group_id = %s AND sender_id != %s AND is_read = FALSE
        """, (group_id, user_id))
        
        affected_rows = cursor.rowcount
        db.commit()
        cursor.close()
        return affected_rows
        
    except Exception as e:
        print(f"Error marking group messages as read: {e}")
        if 'cursor' in locals():
            cursor.close()
        return 0

def mark_messages_as_read(sender_id, receiver_id, reader_id):
    """Mark messages as read in a direct chat"""
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            UPDATE messages 
            SET read_at = NOW(), is_read = TRUE
            WHERE sender_id = %s AND receiver_id = %s AND is_read = FALSE
        """, (sender_id, reader_id))
        
        affected_rows = cursor.rowcount
        db.commit()
        cursor.close()
        return affected_rows
        
    except Exception as e:
        print(f"Error marking messages as read: {e}")
        if 'cursor' in locals():
            cursor.close()
        return 0

def get_unread_count(user_id):
    """Get unread message count for a user"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT sender_id, COUNT(*) as unread_count
            FROM messages 
            WHERE receiver_id = %s AND is_read = FALSE AND group_id IS NULL
            GROUP BY sender_id
        """, (user_id,))
        
        result = cursor.fetchall()
        cursor.close()
        
        unread_dict = {row['sender_id']: row['unread_count'] for row in result}
        return unread_dict
        
    except Exception as e:
        print(f"Error getting unread count: {e}")
        if 'cursor' in locals():
            cursor.close()
        return {}

def get_group_unread_count(user_id):
    """Get unread message count for groups"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT m.group_id, COUNT(*) as unread_count
            FROM messages m
            JOIN group_members gm ON m.group_id = gm.group_id
            WHERE gm.user_id = %s AND m.sender_id != %s AND m.is_read = FALSE AND m.group_id IS NOT NULL
            GROUP BY m.group_id
        """, (user_id, user_id))
        
        result = cursor.fetchall()
        cursor.close()
        
        unread_dict = {row['group_id']: row['unread_count'] for row in result}
        return unread_dict
        
    except Exception as e:
        print(f"Error getting group unread count: {e}")
        if 'cursor' in locals():
            cursor.close()
        return {}

def get_message_by_id(message_id):
    """Get a single message by ID"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT m.*, 
                   s.username as sender_username,
                   s.name as sender_name,
                   s.profile_picture as sender_picture,
                   r.username as receiver_username,
                   CASE 
                       WHEN m.read_at IS NOT NULL THEN 'read'
                       WHEN m.delivered_at IS NOT NULL THEN 'delivered'
                       ELSE 'sent'
                   END as status
            FROM messages m
            LEFT JOIN users s ON m.sender_id = s.id
            LEFT JOIN users r ON m.receiver_id = r.id
            WHERE m.id = %s
        """, (message_id,))
        
        result = cursor.fetchone()
        cursor.close()
        return result
        
    except Exception as e:
        print(f"Error getting message by ID: {e}")
        if 'cursor' in locals():
            cursor.close()
        return None

def delete_message(message_id, user_id):
    """Delete a message (only by sender)"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Check if user is the sender
        cursor.execute("SELECT sender_id FROM messages WHERE id = %s", (message_id,))
        result = cursor.fetchone()
        
        if not result or result[0] != user_id:
            cursor.close()
            return False
        
        # Delete the message
        cursor.execute("DELETE FROM messages WHERE id = %s", (message_id,))
        
        db.commit()
        cursor.close()
        return True
        
    except Exception as e:
        print(f"Error deleting message: {e}")
        try:
            db.rollback()
        except:
            pass
        if 'cursor' in locals():
            cursor.close()
        return False

def get_recent_chats(user_id, limit=20):
    """Get recent chats for a user"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Get recent direct messages
        cursor.execute("""
            SELECT DISTINCT
                CASE 
                    WHEN m.sender_id = %s THEN m.receiver_id
                    ELSE m.sender_id
                END as other_user_id,
                u.name as other_user_name,
                u.username as other_user_username,
                u.profile_picture as other_user_picture,
                u.is_online as other_user_online,
                MAX(m.timestamp) as last_message_time,
                (SELECT content FROM messages WHERE 
                    (sender_id = %s AND receiver_id = other_user_id) OR 
                    (sender_id = other_user_id AND receiver_id = %s)
                    ORDER BY timestamp DESC LIMIT 1) as last_message,
                (SELECT COUNT(*) FROM messages WHERE 
                    sender_id = other_user_id AND receiver_id = %s AND is_read = FALSE
                ) as unread_count
            FROM messages m
            JOIN users u ON (u.id = CASE WHEN m.sender_id = %s THEN m.receiver_id ELSE m.sender_id END)
            WHERE (m.sender_id = %s OR m.receiver_id = %s) AND m.group_id IS NULL
            GROUP BY other_user_id, u.name, u.username, u.profile_picture, u.is_online
            ORDER BY last_message_time DESC
            LIMIT %s
        """, (user_id, user_id, user_id, user_id, user_id, user_id, user_id, limit))
        
        result = cursor.fetchall()
        cursor.close()
        return result
        
    except Exception as e:
        print(f"Error getting recent chats: {e}")
        if 'cursor' in locals():
            cursor.close()
        return []

def search_messages(user_id, search_term, limit=50):
    """Search messages by content"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        search_pattern = f"%{search_term}%"
        
        cursor.execute("""
            SELECT m.*, 
                   s.name as sender_name,
                   s.username as sender_username,
                   s.profile_picture as sender_picture,
                   r.name as receiver_name,
                   r.username as receiver_username,
                   g.name as group_name
            FROM messages m
            LEFT JOIN users s ON m.sender_id = s.id
            LEFT JOIN users r ON m.receiver_id = r.id
            LEFT JOIN groups_table g ON m.group_id = g.id
            WHERE m.content LIKE %s AND 
                  (m.sender_id = %s OR m.receiver_id = %s OR 
                   m.group_id IN (SELECT group_id FROM group_members WHERE user_id = %s))
            ORDER BY m.timestamp DESC
            LIMIT %s
        """, (search_pattern, user_id, user_id, user_id, limit))
        
        result = cursor.fetchall()
        cursor.close()
        return result
        
    except Exception as e:
        print(f"Error searching messages: {e}")
        if 'cursor' in locals():
            cursor.close()
        return []