import os
import time
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import threading
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import dict_factory
from cassandra.policies import ExponentialReconnectionPolicy
from cassandra.cluster import NoHostAvailable, ExecutionProfile, EXEC_PROFILE_DEFAULT
from cassandra import ConsistencyLevel
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configuração do ScyllaDB
profile = ExecutionProfile(
    consistency_level=ConsistencyLevel.LOCAL_ONE,
    row_factory=dict_factory
)

cluster = Cluster(
    contact_points=[os.getenv('SCYLLA_HOSTS', 'scylladb')],
    auth_provider=None,  # ScyllaDB não requer autenticação por padrão
    protocol_version=4,
    connect_timeout=30,
    reconnection_policy=ExponentialReconnectionPolicy(1, 30),
    idle_heartbeat_interval=15,
    execution_profiles={EXEC_PROFILE_DEFAULT: profile},  # Agora usando o profile definido
    compression=True
)

# Lógica de tentativa de conexão
max_retries = 10
retry_count = 0
session = None

while retry_count < max_retries:
    try:
        session = cluster.connect()
        break
    except NoHostAvailable as e:
        retry_count += 1
        print(f"Tentativa de conexão {retry_count} falhou: {str(e)}")
        time.sleep(10)
else:
    raise RuntimeError("Falha ao conectar ao ScyllaDB após várias tentativas")

# Criação do keyspace e tabelas
session.execute("""
    CREATE KEYSPACE IF NOT EXISTS watchup 
    WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}
""")

session.execute("""
    CREATE TABLE IF NOT EXISTS watchup.monitors (
        agent_id text,
        monitor_name text,
        timestamp timestamp,
        status int,
        PRIMARY KEY ((agent_id, monitor_name), timestamp)
    ) WITH CLUSTERING ORDER BY (timestamp DESC)
""")

session.execute("""
    CREATE TABLE IF NOT EXISTS watchup.agents (
        agent_id text PRIMARY KEY,
        last_seen timestamp,
        targets list<frozen<map<text, text>>>,
        status text
    )
""")

session.set_keyspace('watchup')

def cleanup_inactive_agents():
    while True:
        try:
            # Query otimizada sem ALLOW FILTERING
            result = session.execute(
                "SELECT agent_id FROM agents WHERE status = 'active'"
            )
            
            now = datetime.now()
            for row in result:
                agent_result = session.execute(
                    "SELECT last_seen FROM agents WHERE agent_id = %s",
                    (row['agent_id'],)
                ).one()
                
                if agent_result and (now - agent_result['last_seen']) > timedelta(hours=1):
                    session.execute(
                        "DELETE FROM agents WHERE agent_id = %s",
                        (row['agent_id'],)
                    )
                    
        except Exception as e:
            app.logger.error(f"Cleanup error: {str(e)}")
        time.sleep(3600)

@app.route('/register', methods=['POST'])
def register_agent():
    data = request.json
    agent_id = data['agent_name']
    
    try:
        session.execute(
            "INSERT INTO agents (agent_id, last_seen, targets, status) VALUES (%s, %s, %s, %s)",
            (agent_id, datetime.now(), [], 'active')
        )
        return jsonify({'status': 'registered'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Corrigir a rota /heartbeat e adicionar tratamento de erros
@app.route('/heartbeat', methods=['POST'])
def receive_heartbeat():
    data = request.json
    agent_id = data['agent_name']
    
    try:
        session.execute(
            "UPDATE agents SET last_seen = %s WHERE agent_id = %s",
            (datetime.now(), agent_id)
        )
        return jsonify({'status': 'acknowledged'})
    except Exception as e:
        app.logger.error(f"Erro no heartbeat: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Adicionar endpoint de health check
@app.route('/health')
def health_check():
    try:
        session.execute("SELECT * FROM system.local")
        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
    

@app.route('/metrics', methods=['POST'])
def receive_metrics():
    data = request.json
    agent_id = data['agent']
    
    try:
        batch = []
        for metric in data['metrics']:
            batch.append(
                session.prepare("""
                    INSERT INTO monitors (agent_id, monitor_name, timestamp, status)
                    VALUES (?, ?, ?, ?)
                """).bind((
                    agent_id,
                    metric['monitor_name'],
                    datetime.now(),
                    1 if metric['result']['status'] == 'up' else 0
                ))
            )
        
        session.execute(batch, execution_profile='batch')
        return jsonify({'status': 'received'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/targets', methods=['GET', 'POST'])
def handle_targets():
    agent_id = request.args.get('agent')
    
    try:
        if request.method == 'POST':
            targets = request.json
            session.execute(
                "UPDATE agents SET targets = %s WHERE agent_id = %s",
                (targets, agent_id)
            )
            return jsonify({'status': 'targets updated'})
        
        result = session.execute(
            "SELECT targets FROM agents WHERE agent_id = %s",
            (agent_id,)
        ).one()
        
        # Retornar lista vazia se não encontrar resultados
        return jsonify(result['targets'] if result and result['targets'] else [])
    
    except Exception as e:
        app.logger.error(f"Targets error: {str(e)}")
        return jsonify({'error': str(e)}), 500
    

@app.route('/metrics', methods=['GET'])
def get_metrics():
    agent_id = request.args.get('agent')
    monitor_name = request.args.get('monitor')
    
    try:
        result = session.execute(
            "SELECT timestamp, status FROM monitors WHERE agent_id = %s AND monitor_name = %s",
            (agent_id, monitor_name)
        )
        return jsonify([dict(row) for row in result])
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    threading.Thread(target=cleanup_inactive_agents, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)