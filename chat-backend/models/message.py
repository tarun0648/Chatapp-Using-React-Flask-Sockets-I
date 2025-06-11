from config import get_db
from datetime import datetime

def save_message(sender_id, receiver_id=None, content=None, group_id=None):
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
        return None

def get_messages(sender_id=None, receiver_id=None, group_id=None):
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
            """, (group_id,))
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
            """, (sender_id, receiver_id, receiver_id, sender_id))
        
        messages = cursor.fetchall()
        cursor.close()
        return messages
        
    except Exception as e:
        print(f"Error fetching messages: {e}")
        return []

def mark_group_messages_as_read(group_id, user_id):
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
        return 0

def mark_messages_as_read(sender_id, receiver_id, reader_id):
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
        return 0

def get_unread_count(user_id):
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
        return {}

def get_message_by_id(message_id):
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
        return None
