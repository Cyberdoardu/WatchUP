CREATE DATABASE IF NOT EXISTS watchup;
USE watchup;

CREATE TABLE IF NOT EXISTS usuarios (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    admin BOOLEAN NOT NULL DEFAULT 0
);

CREATE TABLE agents (
    agent_id VARCHAR(255) PRIMARY KEY,
    last_seen DATETIME,
    status VARCHAR(50),
    targets JSON
);

CREATE TABLE monitors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agent_id VARCHAR(255),
    monitor_name VARCHAR(255),
    timestamp DATETIME,
    status INT,
    INDEX idx_agent_monitor (agent_id, monitor_name),
    INDEX idx_timestamp (timestamp)
);

GRANT ALL PRIVILEGES ON watchup.* TO 'watchuser'@'%';
FLUSH PRIVILEGES;

CREATE INDEX idx_usuarios_email ON usuarios(email);
CREATE INDEX idx_usuarios_username ON usuarios(username);