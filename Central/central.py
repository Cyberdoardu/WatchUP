import json
import os
import time
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import threading
import mysql.connector
from mysql.connector import Error, pooling
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configuração do pool de conexões MariaDB
db_config = {
    "host": os.getenv('DB_HOST', 'mariadb'),
    "database": os.getenv('DB_NAME', 'watchup'),
    "user": os.getenv('DB_USER', 'watchuser'),
    "password": os.getenv('DB_PASSWORD', 'watchpassword'),
    "pool_name": "monitoring_pool",
    "pool_size": 5,
    "pool_reset_session": True
}

# Criar pool de conexões
def create_connection_pool():
    for _ in range(10):  # 10 tentativas
        try:
            print(f"Tentando conectar ao MariaDB... Tentativa {_+1}/10")
            return pooling.MySQLConnectionPool(**db_config)
        except Error as e:
            app.logger.error(f"Erro ao conectar: {e}")
            time.sleep(10)
    raise Exception("Não foi possível conectar ao MariaDB após 10 tentativas")

connection_pool = create_connection_pool()

# Criação das tabelas
def create_tables():
    tables = [
        """
        CREATE TABLE IF NOT EXISTS agents (
            agent_id VARCHAR(255) PRIMARY KEY,
            last_seen DATETIME,
            status ENUM('active', 'inactive', 'maintenance') DEFAULT 'active'
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS monitors (
            id INT AUTO_INCREMENT PRIMARY KEY,
            monitor_name VARCHAR(255) NOT NULL,
            check_type ENUM('ping', 'http_status', 'api_response', 'custom_script') NOT NULL,
            parameters JSON NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_monitor (monitor_name)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS monitor_assignments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            agent_id VARCHAR(255) NOT NULL,
            monitor_id INT NOT NULL,
            is_primary BOOLEAN DEFAULT true,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
            FOREIGN KEY (monitor_id) REFERENCES monitors(id),
            UNIQUE KEY unique_assignment (agent_id, monitor_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS raw_data (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            monitor_id INT NOT NULL,
            agent_id VARCHAR(255) NOT NULL,
            timestamp DATETIME(6) NOT NULL,
            response_time FLOAT,
            result_code INT,
            raw_result JSON NOT NULL,
            FOREIGN KEY (monitor_id) REFERENCES monitors(id),
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    ]

    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor()
        
        for table in tables:
            cursor.execute(table)
            
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON raw_data(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_monitor ON raw_data(monitor_id)
        """)
        
        conn.commit()
    except Error as e:
        app.logger.error(f"Erro ao criar tabelas: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# Executar criação de tabelas na inicialização
create_tables()

def cleanup_inactive_agents():
    while True:
        try:
            conn = connection_pool.get_connection()
            cursor = conn.cursor()
            
            cutoff_time = datetime.now() - timedelta(hours=1)
            
            cursor.execute(
                "DELETE FROM agents WHERE last_seen < %s",
                (cutoff_time,)
            )
            
            conn.commit()
        except Error as e:
            app.logger.error(f"Cleanup error: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
        time.sleep(3600)

@app.route('/monitors', methods=['POST'])
def create_monitor():
    try:
        data = request.json
        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar se o agent existe
        cursor.execute("SELECT 1 FROM agents WHERE agent_id = %s", (data['agent'],))
        if not cursor.fetchone():
            return jsonify({'error': 'Agent não encontrado'}), 404
        
        # Criar o monitor
        cursor.execute(
            """INSERT INTO monitors 
            (monitor_name, check_type, parameters) 
            VALUES (%s, %s, %s)""",
            (data['monitor_name'], data['check_type'], json.dumps(data['parameters']))
        )
        monitor_id = cursor.lastrowid
        
        # Associar ao agent
        cursor.execute(
            """INSERT INTO monitor_assignments 
            (agent_id, monitor_id, is_primary) 
            VALUES (%s, %s, %s)""",
            (data['agent'], monitor_id, data.get('is_primary', True))
        )
        
        conn.commit()
        
        return jsonify({
            'id': monitor_id,
            'agent_id': data['agent'],
            'monitor_name': data['monitor_name'],
            'check_type': data['check_type'],
            'parameters': data['parameters']
        }), 201
        
    except Error as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/register', methods=['POST'])
def register_agent():
    data = request.json
    agent_id = data['agent_name']
    
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor()
        
        # Query corrigida para nova estrutura da tabela agents
        cursor.execute(
            "INSERT INTO agents (agent_id, last_seen, status) VALUES (%s, %s, %s)",
            (agent_id, datetime.now(), 'active')  # Removido o campo targets
        )
        
        conn.commit()
        return jsonify({'status': 'registered'})
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/heartbeat', methods=['POST'])
def receive_heartbeat():
    data = request.json
    agent_id = data['agent_name']
    
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE agents SET last_seen = %s WHERE agent_id = %s",
            (datetime.now(), agent_id)
        )
        
        conn.commit()
        return jsonify({'status': 'acknowledged'})
    except Error as e:
        app.logger.error(f"Erro no heartbeat: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/health')
def health_check():
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        return jsonify({'status': 'healthy'}), 200
    except Error as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

            
@app.route('/targets', methods=['GET', 'POST'])
def handle_targets():
    agent_id = request.args.get('agent')
    
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'POST':
            # Nova forma de armazenar targets usando a tabela monitor_assignments
            monitors = request.json
            cursor.execute("DELETE FROM monitor_assignments WHERE agent_id = %s", (agent_id,))
            
            for monitor in monitors:
                cursor.execute(
                    """INSERT INTO monitor_assignments 
                    (agent_id, monitor_id, is_primary) 
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE is_primary = VALUES(is_primary)""",
                    (agent_id, monitor['id'], monitor.get('is_primary', True))
                )
            
            conn.commit()
            return jsonify({'status': 'targets updated'})
        
        # Buscar monitors atribuídos ao agent
        cursor.execute("""
            SELECT m.id, m.monitor_name, m.check_type, m.parameters 
            FROM monitors m
            INNER JOIN monitor_assignments ma ON m.id = ma.monitor_id
            WHERE ma.agent_id = %s
        """, (agent_id,))
        
        results = cursor.fetchall()
        return jsonify(results)
    
    except Error as e:
        app.logger.error(f"Targets error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/metrics', methods=['POST'])
def receive_metrics():
    try:
        data = request.json
        required_fields = ['agent_id', 'metrics']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Campos obrigatórios faltando'}), 400

        conn = connection_pool.get_connection()
        cursor = conn.cursor()
        
        values = []
        for metric in data['metrics']:
            values.append((
                metric['monitor_id'],
                data['agent_id'],
                datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                metric.get('response_time'),
                metric['result_code'],
                json.dumps(metric['raw_result'])
            ))
        
        cursor.executemany("""
            INSERT INTO raw_data 
            (monitor_id, agent_id, timestamp, response_time, result_code, raw_result)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, values)
        
        conn.commit()
        return jsonify({'status': 'received', 'count': len(values)})
    
    except Error as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/metrics', methods=['GET'])
def get_metrics():
    agent_id = request.args.get('agent')
    monitor_name = request.args.get('monitor')
    
    if not agent_id or not monitor_name:
        return jsonify({'error': 'Parâmetros agent e monitor são obrigatórios'}), 400
    
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar existência do monitor
        cursor.execute("""
            SELECT m.id 
            FROM monitors m
            JOIN monitor_assignments ma ON m.id = ma.monitor_id
            WHERE 
                ma.agent_id = %s AND
                m.monitor_name = %s
            LIMIT 1
        """, (agent_id, monitor_name))
        
        monitor = cursor.fetchone()
        if not monitor:
            return jsonify({'error': 'Monitor não encontrado'}), 404
        
        # Buscar dados
        cursor.execute("""
            SELECT 
                timestamp,
                response_time,
                result_code AS status,
                raw_result
            FROM raw_data
            WHERE 
                agent_id = %s AND
                monitor_id = %s
            ORDER BY timestamp DESC
            LIMIT 100
        """, (agent_id, monitor['id']))
        
        results = cursor.fetchall()
        return jsonify(results)
    
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    threading.Thread(target=cleanup_inactive_agents, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)