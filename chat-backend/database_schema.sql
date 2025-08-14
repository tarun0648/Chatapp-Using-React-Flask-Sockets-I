-- Enhanced Chat Application Database Schema (Fixed)
DROP DATABASE IF EXISTS chat_app;
CREATE DATABASE chat_app;
USE chat_app;

-- Drop existing tables
DROP TABLE IF EXISTS message_read_status;
DROP TABLE IF EXISTS group_members;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS groups_table;
DROP TABLE IF EXISTS user_sessions;
DROP TABLE IF EXISTS users;

-- Users table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NULL,
    profile_picture TEXT NULL,
    is_online BOOLEAN DEFAULT FALSE,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    socket_id VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_online (is_online),
    INDEX idx_last_active (last_active)
);

-- User sessions
CREATE TABLE user_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    socket_id VARCHAR(255) NOT NULL,
    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_ping TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_socket (socket_id),
    INDEX idx_user_id (user_id),
    INDEX idx_socket_id (socket_id),
    INDEX idx_active (is_active)
);

-- Groups table
CREATE TABLE groups_table (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT NULL,
    group_picture TEXT NULL,
    created_by INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    max_members INT DEFAULT 100,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_created_by (created_by),
    INDEX idx_active (is_active),
    INDEX idx_created_at (created_at)
);

-- Group members
CREATE TABLE group_members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id INT NOT NULL,
    user_id INT NOT NULL,
    role ENUM('admin', 'moderator', 'member') DEFAULT 'member',
    added_by INT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    last_read_message_id INT NULL,
    FOREIGN KEY (group_id) REFERENCES groups_table(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (added_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE KEY unique_group_member (group_id, user_id),
    INDEX idx_group_id (group_id),
    INDEX idx_user_id (user_id),
    INDEX idx_active (is_active),
    INDEX idx_role (role)
);

-- Messages table
CREATE TABLE messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT NOT NULL,
    receiver_id INT NULL,
    group_id INT NULL,
    content TEXT NOT NULL,
    message_type ENUM('text', 'image', 'file', 'audio', 'video') DEFAULT 'text',
    file_url TEXT NULL,
    file_name VARCHAR(255) NULL,
    file_size INT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    is_delivered BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    reply_to_message_id INT NULL,
    edited_at TIMESTAMP NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delivered_at TIMESTAMP NULL,
    read_at TIMESTAMP NULL,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (group_id) REFERENCES groups_table(id) ON DELETE CASCADE,
    FOREIGN KEY (reply_to_message_id) REFERENCES messages(id) ON DELETE SET NULL,
    INDEX idx_sender (sender_id),
    INDEX idx_receiver (receiver_id),
    INDEX idx_group (group_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_read_status (is_read),
    INDEX idx_delivered_status (is_delivered),
    INDEX idx_deleted (is_deleted),
    INDEX idx_type (message_type),
    CHECK ((receiver_id IS NOT NULL AND group_id IS NULL) OR (receiver_id IS NULL AND group_id IS NOT NULL))
);

-- Message read status
CREATE TABLE message_read_status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_id INT NOT NULL,
    user_id INT NOT NULL,
    read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_message_user_read (message_id, user_id),
    INDEX idx_message_id (message_id),
    INDEX idx_user_id (user_id),
    INDEX idx_read_at (read_at)
);

-- Link last_read_message_id
ALTER TABLE group_members ADD CONSTRAINT fk_last_read_message FOREIGN KEY (last_read_message_id) REFERENCES messages(id) ON DELETE SET NULL;

-- Sample data (users, groups, members, messages)
INSERT INTO users (name, username, email, password, phone, is_online) VALUES 
('Demo User', 'demo', 'demo@example.com', 'hashedpassword', '1234567890', TRUE),
('John Doe', 'john', 'john@example.com', 'hashedpassword', '0987654321', FALSE),
('Jane Smith', 'jane', 'jane@example.com', 'hashedpassword', '1122334455', TRUE),
('Bob Wilson', 'bob', 'bob@example.com', 'hashedpassword', '5566778899', FALSE),
('Alice Brown', 'alice', 'alice@example.com', 'hashedpassword', '9988776655', TRUE),
('Charlie Davis', 'charlie', 'charlie@example.com', 'hashedpassword', '4433221100', FALSE);

INSERT INTO groups_table (name, description, created_by) VALUES 
('General Chat', 'General discussion for everyone.', 1),
('Project Team', 'Team collaboration and updates.', 1),
('Random', 'Random conversations.', 2),
('Tech Talk', 'Technology discussions.', 3),
('Study Group', 'Academic collaboration.', 4);

INSERT INTO group_members (group_id, user_id, role, added_by) VALUES 
(1, 1, 'admin', NULL), (1, 2, 'member', 1), (1, 3, 'moderator', 1),
(1, 4, 'member', 1), (1, 5, 'member', 1), (2, 1, 'admin', NULL),
(2, 2, 'member', 1), (2, 3, 'member', 1), (3, 2, 'admin', NULL),
(3, 3, 'member', 2), (3, 4, 'member', 2), (3, 5, 'member', 2),
(3, 6, 'member', 2), (4, 3, 'admin', NULL), (4, 1, 'member', 3),
(4, 2, 'member', 3), (4, 6, 'member', 3), (5, 4, 'admin', NULL),
(5, 5, 'member', 4), (5, 6, 'member', 4);

INSERT INTO messages (sender_id, receiver_id, content, is_delivered, timestamp) VALUES
(1, 2, 'Hey John! How are you?', TRUE, NOW() - INTERVAL 2 HOUR),
(2, 1, 'I am great! You?', TRUE, NOW() - INTERVAL 90 MINUTE),
(1, 2, 'All good here.', TRUE, NOW() - INTERVAL 60 MINUTE);

INSERT INTO messages (sender_id, group_id, content, is_delivered, timestamp) VALUES
(1, 1, 'Welcome to General Chat!', TRUE, NOW() - INTERVAL 3 HOUR),
(2, 1, 'Glad to be here!', TRUE, NOW() - INTERVAL 2 HOUR),
(3, 1, 'Excited to collaborate!', TRUE, NOW() - INTERVAL 1 HOUR);

-- Mark some messages as read
UPDATE messages SET is_read = TRUE, read_at = NOW() WHERE id IN (1, 2, 4);

-- Trigger setup
DELIMITER //

CREATE TRIGGER update_group_timestamp AFTER INSERT ON messages FOR EACH ROW BEGIN
    IF NEW.group_id IS NOT NULL THEN
        UPDATE groups_table SET updated_at = NOW() WHERE id = NEW.group_id;
    END IF;
END//

CREATE TRIGGER set_message_delivered BEFORE INSERT ON messages FOR EACH ROW BEGIN
    SET NEW.is_delivered = TRUE;
    SET NEW.delivered_at = NOW();
END//

CREATE TRIGGER update_user_activity AFTER INSERT ON messages FOR EACH ROW BEGIN
    UPDATE users SET last_active = NOW() WHERE id = NEW.sender_id;
END//

CREATE TRIGGER cleanup_user_sessions AFTER DELETE ON users FOR EACH ROW BEGIN
    DELETE FROM user_sessions WHERE user_id = OLD.id;
END//

DELIMITER ;
