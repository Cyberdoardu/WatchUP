import os
import time
import subprocess
import requests
from threading import Thread
from flask import Flask, request, jsonify
import logging
logging.basicConfig(level=logging.INFO)


app = Flask(__name__)
targets = []
registered = False

def ping_check(target):
    try:
        result = subprocess.run(
            ['ping', '-c', '4', target],
            capture_output=True,
            text=True,
            timeout=10
        )
        return {
            'status': 'up' if result.returncode == 0 else 'down',
            'output': result.stdout
        }
    except Exception as e:
        return {'status': 'error', 'output': str(e)}

def register_agent():
    global registered
    max_retries = 10
    retry_count = 0
    
    while not registered and retry_count < max_retries:
        try:
            response = requests.post(
                f"{os.environ['CENTRAL_SERVER_URL']}/register",
                json={'agent_name': os.environ['AGENT_NAME']},
                timeout=10
            )
            if response.ok:
                registered = True
                print("Registro bem-sucedido!")
                return
            retry_count += 1
            time.sleep(2 ** retry_count)  # Backoff exponencial
        except Exception as e:
            print(f"Erro de registro ({retry_count}/{max_retries}): {str(e)}")
            retry_count += 1
            time.sleep(5)

            
def send_heartbeat():
    while True:
        try:
            requests.post(
                f"{os.environ['CENTRAL_SERVER_URL']}/heartbeat",
                json={'agent_name': os.environ['AGENT_NAME']},
                timeout=3
            )
        except Exception as e:
            print(f"Falha no heartbeat: {str(e)}")
        time.sleep(30)

def update_targets():
    while True:
        try:
            response = requests.get(
                f"{os.environ['CENTRAL_SERVER_URL']}/targets",
                params={'agent': os.environ['AGENT_NAME']},
                timeout=5
            )
            if response.ok:
                global targets
                targets = response.json() or []  # Garantir lista vazia se None
                print(f"Targets atualizados: {len(targets)} alvos")
            else:
                print(f"Erro ao buscar targets: HTTP {response.status_code}")
        except Exception as e:
            print(f"Erro ao buscar targets: {str(e)}")
        time.sleep(10)

def monitoring_loop():
    while True:
        try:
            if not registered:
                print("Agente não registrado, tentando novamente...")
                register_agent()
                time.sleep(5)
                continue
                
            if not targets:  # Verificar se targets está vazio
                print("Nenhum target definido, aguardando...")
                time.sleep(10)
                continue
                
            metrics = [{
                'monitor_name': t['monitor_name'],
                'target': t['address'],
                'type': t['type'],
                'result': ping_check(t['address'])
            } for t in targets]

            if metrics:
                try:
                    response = requests.post(
                        f"{os.environ['CENTRAL_SERVER_URL']}/metrics",
                        json={
                            'agent': os.environ['AGENT_NAME'],
                            'metrics': metrics
                        },
                        timeout=10
                    )
                    response.raise_for_status()
                except Exception as e:
                    print(f"Erro ao enviar métricas: {str(e)}")
            
        except Exception as e:
            print(f"Erro no loop de monitoramento: {str(e)}")
        
        time.sleep(int(os.environ['CHECK_INTERVAL']))


@app.route('/health')
def health_check():
    return jsonify({'status': 'active'}), 200

if __name__ == '__main__':
    register_agent()
    Thread(target=send_heartbeat, daemon=True).start()
    Thread(target=update_targets, daemon=True).start()
    Thread(target=monitoring_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5001)