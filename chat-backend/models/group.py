from config import get_db
from datetime import datetime

def create_group(name, description, created_by, group_picture=None):
    """Create a new group and add creator as admin"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Insert group
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
        try:
            db.rollback()
        except:
            pass
        if 'cursor' in locals():
            cursor.close()
        return None

def get_user_groups(user_id):
    """Get all groups that a user is a member of"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT g.*, gm.role, gm.joined_at,
                   u.name as creator_name,
                   (SELECT COUNT(*) FROM group_members WHERE group_id = g.id) as member_count,
                   (SELECT COUNT(*) FROM messages WHERE group_id = g.id AND sender_id != %s AND is_read = FALSE) as unread_count
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
        if 'cursor' in locals():
            cursor.close()
        return []

def get_group_members(group_id):
    """Get all members of a group"""
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
        if 'cursor' in locals():
            cursor.close()
        return []

def add_group_member(group_id, user_id, added_by):
    """Add a member to a group (only admins can add)"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Check if user adding is admin
        cursor.execute("""
            SELECT role FROM group_members 
            WHERE group_id = %s AND user_id = %s
        """, (group_id, added_by))
        
        admin_check = cursor.fetchone()
        if not admin_check or admin_check['role'] != 'admin':
            cursor.close()
            return False
        
        # Check if user is already a member
        cursor.execute("""
            SELECT id FROM group_members 
            WHERE group_id = %s AND user_id = %s
        """, (group_id, user_id))
        
        if cursor.fetchone():
            cursor.close()
            return False  # User already in group
        
        # Add member
        cursor.execute("""
            INSERT INTO group_members (group_id, user_id, role) 
            VALUES (%s, %s, 'member')
        """, (group_id, user_id))
        
        # Update group's updated_at timestamp
        cursor.execute("""
            UPDATE groups_table SET updated_at = NOW() WHERE id = %s
        """, (group_id,))
        
        db.commit()
        cursor.close()
        return True
        
    except Exception as e:
        print(f"Error adding group member: {e}")
        try:
            db.rollback()
        except:
            pass
        if 'cursor' in locals():
            cursor.close()
        return False

def remove_group_member(group_id, user_id, removed_by):
    """Remove a member from a group (admin or self-removal)"""
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
            cursor.close()
            return False
        
        # Don't allow removing the group creator unless they're removing themselves
        cursor.execute("""
            SELECT created_by FROM groups_table WHERE id = %s
        """, (group_id,))
        
        group_info = cursor.fetchone()
        if group_info and group_info['created_by'] == user_id and removed_by != user_id:
            cursor.close()
            return False
        
        # Remove member
        cursor.execute("""
            DELETE FROM group_members 
            WHERE group_id = %s AND user_id = %s
        """, (group_id, user_id))
        
        # Update group's updated_at timestamp
        cursor.execute("""
            UPDATE groups_table SET updated_at = NOW() WHERE id = %s
        """, (group_id,))
        
        db.commit()
        cursor.close()
        return True
        
    except Exception as e:
        print(f"Error removing group member: {e}")
        try:
            db.rollback()
        except:
            pass
        if 'cursor' in locals():
            cursor.close()
        return False

def search_users_for_group(group_id, search_term=''):
    """Search users who are not in the group"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        search_pattern = f"%{search_term}%"
        
        cursor.execute("""
            SELECT u.id, u.name, u.username, u.profile_picture
            FROM users u
            WHERE u.id NOT IN (
                SELECT user_id FROM group_members WHERE group_id = %s
            )
            AND (u.name LIKE %s OR u.username LIKE %s)
            ORDER BY u.name ASC
            LIMIT 20
        """, (group_id, search_pattern, search_pattern))
        
        result = cursor.fetchall()
        cursor.close()
        return result
        
    except Exception as e:
        print(f"Error searching users for group: {e}")
        if 'cursor' in locals():
            cursor.close()
        return []

def get_group_by_id(group_id):
    """Get group details by ID"""
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
        if 'cursor' in locals():
            cursor.close()
        return None

def update_group(group_id, user_id, name=None, description=None, group_picture=None):
    """Update group details (only admins can update)"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Check if user is admin
        cursor.execute("""
            SELECT role FROM group_members 
            WHERE group_id = %s AND user_id = %s
        """, (group_id, user_id))
        
        admin_check = cursor.fetchone()
        if not admin_check or admin_check['role'] != 'admin':
            cursor.close()
            return False
        
        # Build dynamic update query
        update_fields = []
        values = []
        
        if name:
            update_fields.append("name = %s")
            values.append(name)
        if description is not None:  # Allow empty string
            update_fields.append("description = %s")
            values.append(description)
        if group_picture:
            update_fields.append("group_picture = %s")
            values.append(group_picture)
        
        if not update_fields:
            cursor.close()
            return False
        
        update_fields.append("updated_at = NOW()")
        values.append(group_id)
        
        query = f"UPDATE groups_table SET {', '.join(update_fields)} WHERE id = %s"
        cursor.execute(query, values)
        
        db.commit()
        cursor.close()
        return True
        
    except Exception as e:
        print(f"Error updating group: {e}")
        try:
            db.rollback()
        except:
            pass
        if 'cursor' in locals():
            cursor.close()
        return False

def delete_group(group_id, user_id):
    """Delete a group (only creator can delete)"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Check if user is the creator
        cursor.execute("""
            SELECT created_by FROM groups_table WHERE id = %s
        """, (group_id,))
        
        group_info = cursor.fetchone()
        if not group_info or group_info['created_by'] != user_id:
            cursor.close()
            return False
        
        # Delete group (CASCADE will handle members and messages)
        cursor.execute("DELETE FROM groups_table WHERE id = %s", (group_id,))
        
        db.commit()
        cursor.close()
        return True
        
    except Exception as e:
        print(f"Error deleting group: {e}")
        try:
            db.rollback()
        except:
            pass
        if 'cursor' in locals():
            cursor.close()
        return False

def promote_to_admin(group_id, user_id, promoted_by):
    """Promote a member to admin (only admins can promote)"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Check if user promoting is admin
        cursor.execute("""
            SELECT role FROM group_members 
            WHERE group_id = %s AND user_id = %s
        """, (group_id, promoted_by))
        
        admin_check = cursor.fetchone()
        if not admin_check or admin_check['role'] != 'admin':
            cursor.close()
            return False
        
        # Check if target user is a member
        cursor.execute("""
            SELECT role FROM group_members 
            WHERE group_id = %s AND user_id = %s
        """, (group_id, user_id))
        
        member_check = cursor.fetchone()
        if not member_check:
            cursor.close()
            return False
        
        # Promote to admin
        cursor.execute("""
            UPDATE group_members 
            SET role = 'admin' 
            WHERE group_id = %s AND user_id = %s
        """, (group_id, user_id))
        
        # Update group's updated_at timestamp
        cursor.execute("""
            UPDATE groups_table SET updated_at = NOW() WHERE id = %s
        """, (group_id,))
        
        db.commit()
        cursor.close()
        return True
        
    except Exception as e:
        print(f"Error promoting to admin: {e}")
        try:
            db.rollback()
        except:
            pass
        if 'cursor' in locals():
            cursor.close()
        return False

def demote_from_admin(group_id, user_id, demoted_by):
    """Demote an admin to member (only other admins or group creator)"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Check if user demoting is admin
        cursor.execute("""
            SELECT role FROM group_members 
            WHERE group_id = %s AND user_id = %s
        """, (group_id, demoted_by))
        
        admin_check = cursor.fetchone()
        if not admin_check or admin_check['role'] != 'admin':
            cursor.close()
            return False
        
        # Check if target user is admin
        cursor.execute("""
            SELECT role FROM group_members 
            WHERE group_id = %s AND user_id = %s
        """, (group_id, user_id))
        
        target_check = cursor.fetchone()
        if not target_check or target_check['role'] != 'admin':
            cursor.close()
            return False
        
        # Don't allow demoting the group creator
        cursor.execute("""
            SELECT created_by FROM groups_table WHERE id = %s
        """, (group_id,))
        
        group_info = cursor.fetchone()
        if group_info and group_info['created_by'] == user_id:
            cursor.close()
            return False
        
        # Demote to member
        cursor.execute("""
            UPDATE group_members 
            SET role = 'member' 
            WHERE group_id = %s AND user_id = %s
        """, (group_id, user_id))
        
        # Update group's updated_at timestamp
        cursor.execute("""
            UPDATE groups_table SET updated_at = NOW() WHERE id = %s
        """, (group_id,))
        
        db.commit()
        cursor.close()
        return True
        
    except Exception as e:
        print(f"Error demoting from admin: {e}")
        try:
            db.rollback()
        except:
            pass
        if 'cursor' in locals():
            cursor.close()
        return False

def get_user_role_in_group(group_id, user_id):
    """Get user's role in a specific group"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT role FROM group_members 
            WHERE group_id = %s AND user_id = %s
        """, (group_id, user_id))
        
        result = cursor.fetchone()
        cursor.close()
        
        return result['role'] if result else None
        
    except Exception as e:
        print(f"Error getting user role in group: {e}")
        if 'cursor' in locals():
            cursor.close()
        return None

def is_user_group_member(group_id, user_id):
    """Check if user is a member of the group"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            SELECT 1 FROM group_members 
            WHERE group_id = %s AND user_id = %s
        """, (group_id, user_id))
        
        result = cursor.fetchone()
        cursor.close()
        
        return result is not None
        
    except Exception as e:
        print(f"Error checking group membership: {e}")
        if 'cursor' in locals():
            cursor.close()
        return False

def get_group_admins(group_id):
    """Get all admins of a group"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT u.id, u.name, u.username, u.profile_picture
            FROM users u
            JOIN group_members gm ON u.id = gm.user_id
            WHERE gm.group_id = %s AND gm.role = 'admin'
            ORDER BY u.name ASC
        """, (group_id,))
        
        result = cursor.fetchall()
        cursor.close()
        return result
        
    except Exception as e:
        print(f"Error getting group admins: {e}")
        if 'cursor' in locals():
            cursor.close()
        return []

def get_recent_group_activity(group_id, limit=10):
    """Get recent activity in a group"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("""
            (SELECT 'message' as activity_type, m.timestamp, m.content as activity_data, 
                    u.name as user_name, u.id as user_id
             FROM messages m
             JOIN users u ON m.sender_id = u.id
             WHERE m.group_id = %s)
            UNION ALL
            (SELECT 'member_joined' as activity_type, gm.joined_at as timestamp, 
                    NULL as activity_data, u.name as user_name, u.id as user_id
             FROM group_members gm
             JOIN users u ON gm.user_id = u.id
             WHERE gm.group_id = %s AND gm.joined_at > DATE_SUB(NOW(), INTERVAL 7 DAY))
            ORDER BY timestamp DESC
            LIMIT %s
        """, (group_id, group_id, limit))
        
        result = cursor.fetchall()
        cursor.close()
        return result
        
    except Exception as e:
        print(f"Error getting recent group activity: {e}")
        if 'cursor' in locals():
            cursor.close()
        return []