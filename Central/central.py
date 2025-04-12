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
            SELECT 
                m.id,
                m.monitor_name,
                m.check_type,
                JSON_UNQUOTE(m.parameters) as parameters  # Deserializa JSON
            FROM monitors m
            INNER JOIN monitor_assignments ma ON m.id = ma.monitor_id
            WHERE ma.agent_id = %s
        """, (agent_id,))
        
        results = cursor.fetchall()
        
        # Parsear os parâmetros para dicionários
        for item in results:
            try:
                item['parameters'] = json.loads(item['parameters'])
            except Exception as e:
                app.logger.error(f"Erro ao parsear parâmetros: {e}")
                item['parameters'] = {}

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
                metric['success'],
                metric.get('raw_output', '')
            ))
        
        cursor.executemany("""
            INSERT INTO raw_data 
            (monitor_id, agent_id, timestamp, response_time, success, raw_result)
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
        
        # Buscar dados CRUS sem parsear JSON
        cursor.execute("""
            SELECT 
                timestamp,
                success,
                raw_result AS output
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
            
@app.route('/monitors', methods=['POST'])
def create_monitor():
    try:
        data = request.json
        required_fields = ['monitor_name', 'check_type', 'parameters', 'agent']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Campos obrigatórios faltando'}), 400

        # Validação de parâmetros
        params = data['parameters']
        if data['check_type'] in ['http_status', 'api_response'] and 'expected_match' not in params:
            return jsonify({'error': 'expected_match é obrigatório para este tipo de monitor'}), 400

        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Inserir monitor
        cursor.execute("""
            INSERT INTO monitors 
            (monitor_name, check_type, parameters, expected_match, retention_days)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            data['monitor_name'],
            data['check_type'],
            json.dumps(data['parameters']),
            params.get('expected_match'),
            data.get('retention_days', 30)
        ))
        
        monitor_id = cursor.lastrowid
        
        # Associar ao agent
        cursor.execute("""
            INSERT INTO monitor_assignments 
            (agent_id, monitor_id, is_primary)
            VALUES (%s, %s, %s)
        """, (
            data['agent'],
            monitor_id,
            data.get('is_primary', True)
        ))
        
        conn.commit()
        
        return jsonify({
            'id': monitor_id,
            'monitor_name': data['monitor_name'],
            'check_type': data['check_type'],
            'parameters': data['parameters'],
            'retention_days': data.get('retention_days', 30)
        }), 201
        
    except Error as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def cleanup_old_data():
    while True:
        try:
            conn = connection_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE rd FROM raw_data rd
                JOIN monitors m ON rd.monitor_id = m.id
                WHERE rd.timestamp < NOW() - INTERVAL m.retention_days DAY
            """)
            
            conn.commit()
        except Error as e:
            app.logger.error(f"Cleanup error: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
        time.sleep(86400)  # Executar diariamente

if __name__ == '__main__':
    threading.Thread(target=cleanup_inactive_agents, daemon=True).start()
    threading.Thread(target=cleanup_old_data, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)