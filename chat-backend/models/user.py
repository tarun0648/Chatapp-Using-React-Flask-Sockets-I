from config import get_db
from datetime import datetime
import os

def update_user_profile(user_id, name=None, email=None, phone=None, profile_picture=None):
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
            return False
        
        values.append(user_id)
        
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s"
        cursor.execute(query, values)
        
        db.commit()
        cursor.close()
        return True
        
    except Exception as e:
        print(f"Error updating user profile: {e}")
        return False

def get_user_by_username(username):
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        print(f"Error fetching user by username: {e}")
        return None

def get_user_by_email(email):
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        print(f"Error fetching user by email: {e}")
        return None

def get_user_by_id(user_id):
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        print(f"Error fetching user by ID: {e}")
        return None

def get_all_users_except(user_id):
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
        """, (user_id,))
        result = cursor.fetchall()
        cursor.close()
        return result
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []

def create_user(name, username, email, password, phone=None):
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
        return False

def update_user_online_status(user_id, is_online, socket_id=None):
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
        return False