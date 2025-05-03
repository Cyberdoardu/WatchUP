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

def count_consecutive_failures(cursor, monitor_id):
    cursor.execute("""
        SELECT COUNT(*) FROM raw_data
        WHERE monitor_id = %s AND success = 0
        ORDER BY timestamp DESC
    """, (monitor_id,))
    return cursor.fetchone()[0]

def update_monitor_status(conn, cursor, monitor_id, response_time, success):
    """Updates the monitor status based on response time and success rate."""
    try:
        cursor.execute("""
            SELECT failure_threshold_downtime, failure_threshold_partial_degradation,
                   response_time_threshold_degraded, response_time_threshold_critical
            FROM monitors WHERE id = %s
        """, (monitor_id,))
        monitor_config = cursor.fetchone()

        if monitor_config is None:
            app.logger.error(f"Monitor config not found for ID: {monitor_id}")
            return

        failure_threshold_downtime, failure_threshold_partial_degradation, response_time_threshold_degraded, response_time_threshold_critical = monitor_config
        
        current_status = "operational"
        
        if response_time is not None:
            if response_time > response_time_threshold_critical:
                current_status = "critical"
            elif response_time > response_time_threshold_degraded:
                current_status = "degraded"

        if success == 0:
            cursor.execute("""
                    SELECT success FROM raw_data
                    WHERE monitor_id = %s
                    ORDER BY timestamp DESC
                """, (monitor_id,))

            all_results = cursor.fetchall()
            consecutive_failures = 0
            for result in all_results:
                consecutive_failures = cursor.fetchone()[0]
            
            if consecutive_failures >= failure_threshold_downtime:
                current_status = "downtime"
            elif consecutive_failures >= failure_threshold_partial_degradation:
                current_status = "partially_degraded"

        cursor.execute("""
            UPDATE monitors SET current_status = %s WHERE id = %s
        """, (current_status, monitor_id))
        
        conn.commit()

    except Error as e:
        app.logger.error(f"Error updating monitor status: {e}")







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
        
            
        # Insert all metrics for this monitor_id
        cursor.executemany("""
            INSERT INTO raw_data 
            (monitor_id, agent_id, timestamp, response_time, success, raw_result)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, values)
        
        conn.commit()
        return jsonify({'status': 'received', 'count': len(values)})
        
        for metric in data['metrics']:
            monitor_id = metric['monitor_id']
            response_time = metric.get('response_time')
            success = metric['success']
            
            update_monitor_status(conn, cursor, monitor_id, response_time, success)

    
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
    conn = None
    cursor = None
    try:
        data = request.json
        required_fields = ['monitor_name', 'check_type', 'parameters', 'agent']
        
        # Validação de campos obrigatórios
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Campos obrigatórios faltando: ' + ', '.join(required_fields)}), 400

        params = data['parameters']
        check_type = data['check_type']
        
        # Validação específica por tipo
        if check_type in ['http_status', 'api_response']:
            if 'match' not in params:
                return jsonify({'error': f'Parâmetro "match" obrigatório para check_type {check_type}'}), 400
            if check_type == 'api_response' and not any(key in params for key in ['match', 'regex']):
                return jsonify({'error': 'Necessário "match" ou "regex" para api_response'}), 400

        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Inserir monitor principal
        cursor.execute("""
            INSERT INTO monitors 
            (monitor_name, check_type, parameters, expected_match, retention_days)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            data['monitor_name'],
            check_type,
            json.dumps(params),
            params.get('match'),  # Mapeia 'match' do payload para 'expected_match' no banco
            data.get('retention_days', 30)
        ))
        
        monitor_id = cursor.lastrowid
        
        # Criar associação com agent
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
        
        # Montar resposta
        response_data = {
            'id': monitor_id,
            'monitor_name': data['monitor_name'],
            'check_type': check_type,
            'parameters': params,
            'expected_match': params.get('match'),
            'retention_days': data.get('retention_days', 30),
            'agent_assignment': {
                'agent_id': data['agent'],
                'is_primary': data.get('is_primary', True)
            }
        }
        
        return jsonify(response_data), 201
        
    except Error as e:
        if conn:
            conn.rollback()
        app.logger.error(f"Database error: {str(e)}")
        return jsonify({'error': 'Erro de banco de dados: ' + str(e)}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        app.logger.error(f"General error: {str(e)}")
        return jsonify({'error': 'Erro inesperado: ' + str(e)}), 500
    finally:
        if conn and conn.is_connected():
            if cursor:
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