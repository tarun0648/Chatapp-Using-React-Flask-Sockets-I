from config import get_db
from datetime import datetime

def create_group(name, description, created_by, group_picture=None):
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            INSERT INTO groups_table (name, description, created_by, group_picture) 
            VALUES (%s, %s, %s, %s)
        """, (name, description, created_by, group_picture))
        
        group_id = cursor.lastrowid
        
        # Add creator as admin
        cursor.execute("""
            INSERT INTO group_members (group_id, user_id, role) 
            VALUES (%s, %s, 'admin')
        """, (group_id, created_by))
        
        db.commit()
        cursor.close()
        return group_id
        
    except Exception as e:
        print(f"Error creating group: {e}")
        return None

def get_user_groups(user_id):
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT g.*, gm.role, gm.joined_at,
                   u.name as creator_name,
                   (SELECT COUNT(*) FROM group_members WHERE group_id = g.id) as member_count,
                   (SELECT COUNT(*) FROM messages WHERE group_id = g.id AND receiver_id = %s AND is_read = FALSE) as unread_count
            FROM groups_table g
            JOIN group_members gm ON g.id = gm.group_id
            LEFT JOIN users u ON g.created_by = u.id
            WHERE gm.user_id = %s
            ORDER BY g.updated_at DESC
        """, (user_id, user_id))
        
        result = cursor.fetchall()
        cursor.close()
        return result
        
    except Exception as e:
        print(f"Error getting user groups: {e}")
        return []

def get_group_members(group_id):
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT u.id, u.name, u.username, u.profile_picture, u.is_online,
                   gm.role, gm.joined_at
            FROM users u
            JOIN group_members gm ON u.id = gm.user_id
            WHERE gm.group_id = %s
            ORDER BY gm.role DESC, u.name ASC
        """, (group_id,))
        
        result = cursor.fetchall()
        cursor.close()
        return result
        
    except Exception as e:
        print(f"Error getting group members: {e}")
        return []

def add_group_member(group_id, user_id, added_by):
    try:
        # Check if user adding is admin
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT role FROM group_members 
            WHERE group_id = %s AND user_id = %s
        """, (group_id, added_by))
        
        admin_check = cursor.fetchone()
        if not admin_check or admin_check['role'] != 'admin':
            return False
        
        # Add member
        cursor.execute("""
            INSERT INTO group_members (group_id, user_id, role) 
            VALUES (%s, %s, 'member')
        """, (group_id, user_id))
        
        db.commit()
        cursor.close()
        return True
        
    except Exception as e:
        print(f"Error adding group member: {e}")
        return False

def remove_group_member(group_id, user_id, removed_by):
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Check if user removing is admin or removing themselves
        cursor.execute("""
            SELECT role FROM group_members 
            WHERE group_id = %s AND user_id = %s
        """, (group_id, removed_by))
        
        admin_check = cursor.fetchone()
        if not admin_check or (admin_check['role'] != 'admin' and removed_by != user_id):
            return False
        
        cursor.execute("""
            DELETE FROM group_members 
            WHERE group_id = %s AND user_id = %s
        """, (group_id, user_id))
        
        db.commit()
        cursor.close()
        return True
        
    except Exception as e:
        print(f"Error removing group member: {e}")
        return False

def get_group_by_id(group_id):
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT g.*, u.name as creator_name,
                   (SELECT COUNT(*) FROM group_members WHERE group_id = g.id) as member_count
            FROM groups_table g
            LEFT JOIN users u ON g.created_by = u.id
            WHERE g.id = %s
        """, (group_id,))
        
        result = cursor.fetchone()
        cursor.close()
        return result
        
    except Exception as e:
        print(f"Error getting group: {e}")
        return None