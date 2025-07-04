CREATE DATABASE IF NOT EXISTS watchup;
USE watchup;

CREATE TABLE IF NOT EXISTS usuarios (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    admin BOOLEAN NOT NULL DEFAULT 0,
    role VARCHAR(20) NOT NULL DEFAULT 'user' -- Adicionado para RBAC
);

CREATE TABLE IF NOT EXISTS agents (
    agent_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE, -- Nome do agente deve ser único
    last_seen DATETIME,
    status ENUM('active', 'inactive', 'maintenance', 'pending') DEFAULT 'pending', -- 'pending' para pré-registro
    api_key_hash VARCHAR(255) DEFAULT NULL, -- Hash da chave de API
    prereg_expires DATETIME DEFAULT NULL -- Timestamp de expiração do pré-registro
);

CREATE TABLE IF NOT EXISTS incidentes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  titulo VARCHAR(255) NOT NULL,
  descricao TEXT NOT NULL,
  impacto VARCHAR(50) NOT NULL,
  tipo VARCHAR(50) NOT NULL,
  servico VARCHAR(100) NOT NULL,
  estado_atual VARCHAR(50) NOT NULL DEFAULT 'Identificado',
  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  resolvido_em TIMESTAMP DEFAULT NULL
);

-- Nova tabela de definição de monitores
CREATE TABLE IF NOT EXISTS monitors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    monitor_name VARCHAR(255) NOT NULL,
    failure_threshold_downtime INT DEFAULT 3,
    failure_threshold_partial_degradation INT DEFAULT 1,
    response_time_threshold_degraded INT DEFAULT 500,
    response_time_threshold_critical INT DEFAULT 1000,
    current_status ENUM('operational', 'degraded', 'partially_degraded', 'critical', 'downtime') DEFAULT 'operational',

    check_type ENUM('ping', 'http_status', 'api_response', 'custom_script') NOT NULL,
    parameters JSON NOT NULL,
    expected_match VARCHAR(255) DEFAULT NULL,
    retention_days INT DEFAULT 30,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_monitor (monitor_name)
);

-- Tabela de associação agentes-monitores
CREATE TABLE IF NOT EXISTS monitor_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    monitor_id INT NOT NULL,
    is_primary BOOLEAN DEFAULT true,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (monitor_id) REFERENCES monitors(id),
    UNIQUE KEY unique_assignment (agent_id, monitor_id)
);

-- Tabela de dados brutos (principal)
CREATE TABLE IF NOT EXISTS raw_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    monitor_id INT NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    timestamp DATETIME(6) NOT NULL,
    response_time FLOAT,
    success TINYINT(1) NOT NULL,
    raw_result TEXT DEFAULT NULL,
    FOREIGN KEY (monitor_id) REFERENCES monitors(id),
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- Índices para consultas rápidas
CREATE INDEX idx_timestamp ON raw_data(timestamp);
CREATE INDEX idx_monitor ON raw_data(monitor_id);
CREATE INDEX idx_check_type ON monitors(check_type);


GRANT ALL PRIVILEGES ON watchup.* TO 'watchuser'@'%';
FLUSH PRIVILEGES;