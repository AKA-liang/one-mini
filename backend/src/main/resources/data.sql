-- One Mini Database Schema

CREATE DATABASE IF NOT EXISTS one_mini CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE one_mini;

-- Agent table (renamed from Employee)
CREATE TABLE IF NOT EXISTS agent (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(100),
    position VARCHAR(100),
    avatar VARCHAR(500),
    status VARCHAR(50) DEFAULT 'online',
    current_task VARCHAR(500),
    recent_output VARCHAR(500),
    is_on_duty BOOLEAN DEFAULT TRUE,
    schedule VARCHAR(50),
    category VARCHAR(50),
    skills VARCHAR(1000),
    tasks_completed INT DEFAULT 0,
    accuracy VARCHAR(20) DEFAULT '95.0%',
    avg_response_time VARCHAR(20) DEFAULT '0.5s',
    prompt TEXT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Boss table
CREATE TABLE IF NOT EXISTS boss (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    position VARCHAR(200),
    email VARCHAR(200),
    phone VARCHAR(50),
    department VARCHAR(200),
    bio VARCHAR(500),
    avatar VARCHAR(500),
    join_date VARCHAR(20),
    team_size INT DEFAULT 13,
    projects_completed INT DEFAULT 48,
    efficiency VARCHAR(50) DEFAULT '98.5%',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Site config table
CREATE TABLE IF NOT EXISTS site_config (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    site_name VARCHAR(200),
    site_subtitle VARCHAR(500),
    total_employees INT DEFAULT 13,
    online_employees INT DEFAULT 13,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Task table (new)
CREATE TABLE IF NOT EXISTS task (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(64) UNIQUE NOT NULL,
    trace_id VARCHAR(64),
    type VARCHAR(50) NOT NULL COMMENT 'product_analysis / finance_review',
    status VARCHAR(20) DEFAULT 'pending' COMMENT 'pending / running / completed / failed',
    input_json TEXT,
    output_json TEXT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Task step table (new)
CREATE TABLE IF NOT EXISTS task_step (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL,
    agent_name VARCHAR(50) NOT NULL COMMENT 'product_picker / finance_analyst',
    status VARCHAR(20) DEFAULT 'pending',
    input_json TEXT,
    output_json TEXT,
    error_message TEXT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Agent log table (new)
CREATE TABLE IF NOT EXISTS agent_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(64),
    agent_name VARCHAR(50),
    action VARCHAR(100),
    level VARCHAR(10) DEFAULT 'info' COMMENT 'info / warn / error',
    message TEXT,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_agent_name (agent_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default boss
INSERT INTO boss (name, position, email, phone, department, bio, avatar, join_date, team_size, projects_completed, efficiency)
VALUES ('张总', '智能体控制中心负责人', 'boss@company.com', '138-0013-8000', 'AI运营中心', '致力于打造最优秀的AI数字员工团队，推动企业智能化转型', '', '2024-01-15', 13, 48, '98.5%')
ON DUPLICATE KEY UPDATE name=name;

-- Insert default site config
INSERT INTO site_config (site_name, site_subtitle, total_employees, online_employees)
VALUES ('One Mini', '智能体控制中心', 13, 13)
ON DUPLICATE KEY UPDATE site_name=site_name;