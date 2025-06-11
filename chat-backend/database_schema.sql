USE chat_app;


ALTER TABLE users ADD COLUMN profile_picture VARCHAR(255) NULL;


CREATE TABLE IF NOT EXISTS groups_table (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT NULL,
    group_picture VARCHAR(255) NULL,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_created_by (created_by)
);

CREATE TABLE IF NOT EXISTS group_members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id INT NOT NULL,
    user_id INT NOT NULL,
    role ENUM('admin', 'member') DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES groups_table(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_group_member (group_id, user_id),
    INDEX idx_group_id (group_id),
    INDEX idx_user_id (user_id)
);


ALTER TABLE messages ADD COLUMN group_id INT NULL;
ALTER TABLE messages ADD FOREIGN KEY (group_id) REFERENCES groups_table(id) ON DELETE CASCADE;
ALTER TABLE messages ADD INDEX idx_group_id (group_id);

INSERT INTO groups_table (name, description, created_by) VALUES 
('General Chat', 'General discussion for everyone', 1),
('Project Team', 'Team collaboration and updates', 1),
('Random', 'Random conversations and fun', 2);

INSERT INTO group_members (group_id, user_id, role) VALUES 
(1, 1, 'admin'), (1, 2, 'member'), (1, 3, 'member'),
(2, 1, 'admin'), (2, 2, 'member'),
(3, 2, 'admin'), (3, 3, 'member'), (3, 4, 'member');