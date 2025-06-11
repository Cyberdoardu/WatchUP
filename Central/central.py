import json
import os
import time
import hashlib
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import threading
import mysql.connector
from mysql.connector import Error, pooling
from dotenv import load_dotenv
from functools import wraps
import secrets

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

SALT = "salzinho_pra_dar_g0st0"
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

# --- DECORATOR DE AUTENTICAÇÃO DE AGENTE ---
def agent_api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        agent_id = request.headers.get('X-Agent-ID')

        if not api_key or not agent_id:
            return jsonify({'error': 'Cabeçalhos de autenticação do agente ausentes'}), 401

        conn = None
        cursor = None
        try:
            conn = connection_pool.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT api_key_hash FROM agents WHERE agent_id = %s AND status = 'active'", (agent_id,))
            agent = cursor.fetchone()

            if not agent or not hashlib.sha256(api_key.encode()).hexdigest() == agent['api_key_hash']:
                return jsonify({'error': 'Agente não autorizado ou chave inválida'}), 403
            
            # Passa o ID do agente para a função da rota
            kwargs['agent_id'] = agent_id
            
        except Error as e:
            app.logger.error(f"Erro de banco de dados na autenticação do agente: {e}")
            return jsonify({'error': 'Erro interno do servidor'}), 500
        finally:
            if conn and conn.is_connected():
                if cursor:
                    cursor.close()
                conn.close()
        
        return f(*args, **kwargs)
    return decorated_function

def hash_agent_name(agent_name, salt):
    combined = f"{agent_name}:{salt}"
    hashed = hashlib.sha256(combined.encode()).hexdigest()
    return hashed


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



@app.route('/preregister-agent', methods=['POST'])
def preregister_agent():
    """
    Endpoint para a WebApp pré-registrar um agente.
    Cria um agente com status 'pending' e um tempo de expiração.
    """
    conn = None
    cursor = None
    try:
        data = request.json
        agent_name = data.get('agent_name')
        if not agent_name:
            return jsonify({'error': 'O nome do agente é obrigatório'}), 400

        # Gera um ID único para o agente no momento do pré-registro
        agent_id = hashlib.sha256(f"{agent_name}-{secrets.token_hex(8)}".encode()).hexdigest()
        expiration_time = datetime.now() + timedelta(minutes=15)

        conn = connection_pool.get_connection()
        cursor = conn.cursor()
        
        # Inserir ou atualizar o pré-registro
        cursor.execute(
            """INSERT INTO agents (agent_id, name, status, prereg_expires)
               VALUES (%s, %s, 'pending', %s)
               ON DUPLICATE KEY UPDATE agent_id = VALUES(agent_id), status = 'pending', prereg_expires = VALUES(prereg_expires)""",
            (agent_id, agent_name, expiration_time)
        )
        conn.commit()

        return jsonify({
            'message': 'Agente pré-registrado com sucesso. O agente tem 15 minutos para completar o registro.',
            'agent_id': agent_id,
            'agent_name': agent_name
        }), 201

    except Error as e:
        if conn: conn.rollback()
        app.logger.error(f"Erro ao pré-registrar agente: {e}")
        return jsonify({'error': f'Erro de banco de dados: {e}'}), 500
    finally:
        if conn and conn.is_connected():
            if cursor: cursor.close()
            conn.close()

@app.route('/register', methods=['POST'])
def register_agent():
    """
    Endpoint para o Agente se registrar.
    Verifica se existe um pré-registro válido e, em caso afirmativo, gera e retorna uma chave de API.
    """
    conn = None
    cursor = None
    try:
        data = request.json
        agent_name = data.get('agent_name')
        agent_id = data.get('agent_id') # O ID gerado no pré-registro

        if not agent_name or not agent_id:
            return jsonify({'error': 'Nome e ID do agente são obrigatórios'}), 400

        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True)

        # Caso especial para o primeiro agente (do docker-compose)
        cursor.execute("SELECT COUNT(*) as count FROM agents")
        is_first_agent = cursor.fetchone()['count'] == 0

        if is_first_agent:
            # Registro automático para o primeiro agente
            api_key = secrets.token_hex(32)
            api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            cursor.execute(
                """INSERT INTO agents (agent_id, name, status, api_key_hash, last_seen)
                   VALUES (%s, %s, 'active', %s, %s)""",
                (agent_id, agent_name, api_key_hash, datetime.now())
            )
            conn.commit()
            return jsonify({
                'message': 'Primeiro agente registrado automaticamente com sucesso!',
                'api_key': api_key
            }), 200

        # Verificação do pré-registro para outros agentes
        cursor.execute(
            "SELECT * FROM agents WHERE agent_id = %s AND name = %s AND status = 'pending' AND prereg_expires > NOW()",
            (agent_id, agent_name)
        )
        agent = cursor.fetchone()

        if not agent:
            return jsonify({'error': 'Registro inválido, expirado ou não encontrado. Contate o administrador.'}), 403

        # Gera a chave de API e atualiza o agente para 'active'
        api_key = secrets.token_hex(32)
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        cursor.execute(
            "UPDATE agents SET status = 'active', api_key_hash = %s, last_seen = %s, prereg_expires = NULL WHERE agent_id = %s",
            (api_key_hash, datetime.now(), agent_id)
        )
        conn.commit()

        return jsonify({
            'message': 'Agente registrado com sucesso!',
            'api_key': api_key
        }), 200

    except Error as e:
        if conn: conn.rollback()
        app.logger.error(f"Erro no registro do agente: {e}")
        return jsonify({'error': f'Database error: {e}'}), 500
    finally:
        if conn and conn.is_connected():
            if cursor: cursor.close()
            conn.close()


@app.route('/agents', methods=['GET'])
def list_agents():
    conn = None
    cursor = None
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT name, agent_id FROM agents")
        agents = cursor.fetchall()

        return jsonify(agents), 200
    except Error as e:
        app.logger.error(f"Database error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            if cursor:
                cursor.close()
            conn.close()

@app.route('/create-agent', methods=['POST'])
def create_agent():
    conn = None
    cursor = None
    try:
        data = request.json
        agent_name = data['agent_name']
        hashed_agent_id = hash_agent_name(agent_name, SALT)

        conn = connection_pool.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO agents (agent_id, name) VALUES (%s, %s)",
            (hashed_agent_id, agent_name)
        )
        conn.commit()

        return jsonify({
            'message': 'Agent created successfully',
            'agent_name': agent_name,
            'hashed_agent_id': hashed_agent_id
        }), 201
    except Error as e:
        app.logger.error(f"Error creating agent: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()



@app.route('/heartbeat', methods=['POST'])
@agent_api_key_required
def receive_heartbeat(agent_id): # <<< CORREÇÃO: Adicionado o parâmetro 'agent_id'
    """Recebe um sinal de vida do agente e atualiza seu status no banco."""
    conn = None
    cursor = None
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE agents SET last_seen = %s WHERE agent_id = %s",
            (datetime.now(), agent_id) # Usa o agent_id passado pelo decorator
        )
        
        conn.commit()
        return jsonify({'status': 'acknowledged'})
    except Error as e:
        app.logger.error(f"Erro no heartbeat para o agente {agent_id}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            if cursor: cursor.close()
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

            
@app.route('/targets', methods=['GET'])
@agent_api_key_required
def handle_targets(agent_id): # <<< CORREÇÃO: Adicionado o parâmetro 'agent_id'
    """Retorna a lista de monitores (alvos) para um agente autenticado."""
    conn = None
    cursor = None
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # A lógica da query agora usa o agent_id seguro vindo do decorator
        cursor.execute("""
            SELECT 
                m.id, m.monitor_name, m.check_type,
                JSON_UNQUOTE(m.parameters) as parameters
            FROM monitors m
            INNER JOIN monitor_assignments ma ON m.id = ma.monitor_id
            WHERE ma.agent_id = %s
        """, (agent_id,))
        
        results = cursor.fetchall()
        
        for item in results:
            try:
                # O ideal é que o JSON no banco seja sempre válido,
                # mas uma verificação extra não custa nada.
                if isinstance(item['parameters'], str):
                    item['parameters'] = json.loads(item['parameters'])
            except (json.JSONDecodeError, TypeError):
                item['parameters'] = {}

        return jsonify(results)
    
    except Error as e:
        app.logger.error(f"Erro ao buscar targets para o agente {agent_id}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn and conn.is_connected():
            if cursor: cursor.close()
            conn.close()

def count_consecutive_failures(cursor, monitor_id):
    cursor.execute("""
        SELECT COUNT(*) FROM raw_data
        WHERE monitor_id = %s AND success = 0
        ORDER BY timestamp DESC
    """, (monitor_id,))
    return cursor.fetchone()[0]

def update_monitor_status(conn, cursor, monitor_id, response_time, success):
    """Atualiza o status do monitor com base no tempo de resposta e sucesso."""
    try:
        # Busca a configuração do monitor
        cursor.execute("""
            SELECT failure_threshold_downtime, response_time_threshold_degraded
            FROM monitors WHERE id = %s
        """, (monitor_id,))
        monitor_config = cursor.fetchone()

        if not monitor_config:
            app.logger.error(f"Configuração do monitor não encontrada para o ID: {monitor_id}")
            return

        # Define o status padrão
        current_status = "operational"

        # 1. Verifica falha crítica (success = 0)
        if success == 0:
            current_status = "critical"
        # 2. Se não for crítico, verifica se está degradado por lentidão
        elif response_time is not None:
            # Busca a média de tempo de resposta das últimas 30 checagens
            cursor.execute("""
                SELECT AVG(response_time) as avg_response 
                FROM (
                    SELECT response_time FROM raw_data
                    WHERE monitor_id = %s
                    ORDER BY timestamp DESC
                    LIMIT 30
                ) as recent_checks;
            """, (monitor_id,))
            avg_response_data = cursor.fetchone()
            
            # Garante que temos um valor para comparar
            avg_response_time = avg_response_data[0] if avg_response_data else 0

            if avg_response_time > monitor_config[1]: # monitor_config[1] é response_time_threshold_degraded
                current_status = "degraded"
        
        # Atualiza o status no banco de dados
        cursor.execute("UPDATE monitors SET current_status = %s WHERE id = %s", (current_status, monitor_id))

    except Error as e:
        app.logger.error(f"Erro ao atualizar o status do monitor: {e}")
        raise
        

    except Error as e:
        app.logger.error(f"Error updating monitor status: {e}")
        # Lançar a exceção permite que a transação seja revertida na função que a chamou.
        raise



@app.route('/metrics', methods=['POST'])
@agent_api_key_required
def receive_metrics(agent_id):
    try:
        data = request.json
        if 'metrics' not in data:
            return jsonify({'error': "Campos 'metrics' faltando"}), 400

        conn = connection_pool.get_connection()
        cursor = conn.cursor()
        
        values = []
        for metric in data['metrics']:
            # Validação do novo campo 'timestamp'
            if 'timestamp' not in metric:
                return jsonify({'error': "Campo 'timestamp' faltando em uma das métricas"}), 400
            
            values.append((
                metric['monitor_id'],
                agent_id,
                metric['timestamp'],  # UTILIZA O TIMESTAMP VINDO DO AGENTE
                metric.get('response_time'),
                metric['success'],
                metric.get('raw_result', '')
            ))
        
        cursor.executemany("""
            INSERT INTO raw_data 
            (monitor_id, agent_id, timestamp, response_time, success, raw_result)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, values)
        
        for metric in data['metrics']:
            monitor_id = metric['monitor_id']
            response_time = metric.get('response_time')
            success = metric['success']
            
            update_monitor_status(conn, cursor, monitor_id, response_time, success)

        conn.commit()
        return jsonify({'status': 'received', 'count': len(values)})
        
    except Error as e:
        if conn and conn.is_connected():
            conn.rollback()
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        if conn and conn.is_connected():
            if cursor:
                cursor.close()
            conn.close()

@app.route('/metrics', methods=['GET'])
def get_metrics():
    agent_id = request.args.get('agent_id')
    monitor_name = request.args.get('monitor')
    
    if not agent_id or not monitor_name:
        return jsonify({'error': 'Parâmetros agent_id e monitor são obrigatórios'}), 400
    
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
        
        # Check if the agent exists
        cursor.execute("SELECT agent_id FROM agents WHERE agent_id = %s", (data['agent'],))
        agent_exists = cursor.fetchone()

        if not agent_exists:
            return jsonify({'error': 'Agent not found'}), 404

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