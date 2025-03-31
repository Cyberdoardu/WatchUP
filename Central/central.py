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
    create_agents_table = """
    CREATE TABLE IF NOT EXISTS agents (
        agent_id VARCHAR(255) PRIMARY KEY,
        last_seen DATETIME,
        status VARCHAR(50),
        targets JSON
    )
    """

    create_monitors_table = """
    CREATE TABLE IF NOT EXISTS monitors (
        id INT AUTO_INCREMENT PRIMARY KEY,
        agent_id VARCHAR(255),
        monitor_name VARCHAR(255),
        timestamp DATETIME,
        status INT,
        INDEX idx_agent_monitor (agent_id, monitor_name),
        INDEX idx_timestamp (timestamp)
    )
    """

    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(create_agents_table)
        cursor.execute(create_monitors_table)
        
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

@app.route('/register', methods=['POST'])
def register_agent():
    data = request.json
    agent_id = data['agent_name']
    
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO agents (agent_id, last_seen, status, targets) VALUES (%s, %s, %s, %s)",
            (agent_id, datetime.now(), 'active', '[]')
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

@app.route('/metrics', methods=['POST'])
def receive_metrics():
    data = request.json
    agent_id = data['agent']
    
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor()
        
        query = """
            INSERT INTO monitors 
            (agent_id, monitor_name, timestamp, status)
            VALUES (%s, %s, %s, %s)
        """
        
        values = [
            (agent_id, 
             metric['monitor_name'], 
             datetime.now(), 
             1 if metric['result']['status'] == 'up' else 0)
            for metric in data['metrics']
        ]
        
        cursor.executemany(query, values)
        conn.commit()
        return jsonify({'status': 'received'})
    
    except Error as e:
        return jsonify({'error': str(e)}), 500
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
            targets = request.json
            cursor.execute(
                "UPDATE agents SET targets = %s WHERE agent_id = %s",
                (str(targets), agent_id)
            )
            conn.commit()
            return jsonify({'status': 'targets updated'})
        
        cursor.execute(
            "SELECT targets FROM agents WHERE agent_id = %s",
            (agent_id,)
        )
        result = cursor.fetchone()
        
        return jsonify(result['targets'] if result and result['targets'] else [])
    
    except Error as e:
        app.logger.error(f"Targets error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/metrics', methods=['GET'])
def get_metrics():
    agent_id = request.args.get('agent')
    monitor_name = request.args.get('monitor')
    
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(
            "SELECT timestamp, status FROM monitors WHERE agent_id = %s AND monitor_name = %s ORDER BY timestamp DESC",
            (agent_id, monitor_name)
        )
        
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