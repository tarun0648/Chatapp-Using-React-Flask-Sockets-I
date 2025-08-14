from config import get_db
from datetime import datetime
import os

def update_user_profile(user_id, name=None, email=None, phone=None, profile_picture=None):
    """Update user profile with provided fields"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Build dynamic update query
        update_fields = []
        values = []
        
        if name:
            update_fields.append("name = %s")
            values.append(name)
        if email:
            update_fields.append("email = %s")
            values.append(email)
        if phone:
            update_fields.append("phone = %s")
            values.append(phone)
        if profile_picture:
            update_fields.append("profile_picture = %s")
            values.append(profile_picture)
        
        if not update_fields:
            cursor.close()
            return False
        
        values.append(user_id)
        
        query = f"UPDATE users SET {', '.join(update_fields)}, last_active = NOW() WHERE id = %s"
        cursor.execute(query, values)
        
        db.commit()
        cursor.close()
        return True
        
    except Exception as e:
        print(f"Error updating user profile: {e}")
        if 'cursor' in locals():
            cursor.close()
        return False

def get_user_by_username(username):
    """Get user by username"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        print(f"Error fetching user by username: {e}")
        if 'cursor' in locals():
            cursor.close()
        return None

def get_user_by_email(email):
    """Get user by email"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        print(f"Error fetching user by email: {e}")
        if 'cursor' in locals():
            cursor.close()
        return None

def get_user_by_id(user_id):
    """Get user by ID"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        print(f"Error fetching user by ID: {e}")
        if 'cursor' in locals():
            cursor.close()
        return None

def get_all_users_except(user_id):
    """Get all users except the specified user ID"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, name, username, email, profile_picture, is_online, last_active,
                   CASE 
                       WHEN is_online = TRUE THEN 'online'
                       WHEN last_active > NOW() - INTERVAL 5 MINUTE THEN 'recently_active'
                       ELSE 'offline'
                   END as status
            FROM users 
            WHERE id != %s
            ORDER BY is_online DESC, last_active DESC
        """, (user_id,))
        result = cursor.fetchall()
        cursor.close()
        return result
    except Exception as e:
        print(f"Error fetching users: {e}")
        if 'cursor' in locals():
            cursor.close()
        return []

def create_user(name, username, email, password, phone=None):
    """Create a new user"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        query = """
        INSERT INTO users (name, username, email, password, phone, is_online, last_active) 
        VALUES (%s, %s, %s, %s, %s, FALSE, NOW())
        """
        values = (name, username, email, password, phone)
        
        cursor.execute(query, values)
        db.commit()
        cursor.close()
        
        return True
        
    except Exception as e:
        print(f"Error creating user: {e}")
        try:
            db.rollback()
        except:
            pass
        if 'cursor' in locals():
            cursor.close()
        return False

def update_user_online_status(user_id, is_online, socket_id=None):
    """Update user's online status"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            UPDATE users 
            SET is_online = %s, last_active = NOW() 
            WHERE id = %s
        """, (is_online, user_id))
        
        db.commit()
        cursor.close()
        return True
        
    except Exception as e:
        print(f"Error updating online status: {e}")
        if 'cursor' in locals():
            cursor.close()
        return False

def get_users_by_ids(user_ids):
    """Get multiple users by their IDs"""
    try:
        if not user_ids:
            return []
            
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        placeholders = ','.join(['%s'] * len(user_ids))
        cursor.execute(f"""
            SELECT id, name, username, profile_picture, is_online
            FROM users 
            WHERE id IN ({placeholders})
        """, user_ids)
        
        result = cursor.fetchall()
        cursor.close()
        return result
        
    except Exception as e:
        print(f"Error fetching users by IDs: {e}")
        if 'cursor' in locals():
            cursor.close()
        return []

def search_users(search_term, exclude_user_id=None):
    """Search users by name or username"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        search_pattern = f"%{search_term}%"
        
        if exclude_user_id:
            cursor.execute("""
                SELECT id, name, username, profile_picture
                FROM users 
                WHERE (name LIKE %s OR username LIKE %s) AND id != %s
                ORDER BY name ASC
                LIMIT 20
            """, (search_pattern, search_pattern, exclude_user_id))
        else:
            cursor.execute("""
                SELECT id, name, username, profile_picture
                FROM users 
                WHERE name LIKE %s OR username LIKE %s
                ORDER BY name ASC
                LIMIT 20
            """, (search_pattern, search_pattern))
        
        result = cursor.fetchall()
        cursor.close()
        return result
        
    except Exception as e:
        print(f"Error searching users: {e}")
        if 'cursor' in locals():
            cursor.close()
        return []

def delete_user(user_id):
    """Delete a user and all related data"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Delete user (CASCADE will handle related data)
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        
        db.commit()
        cursor.close()
        return True
        
    except Exception as e:
        print(f"Error deleting user: {e}")
        try:
            db.rollback()
        except:
            pass
        if 'cursor' in locals():
            cursor.close()
        return False