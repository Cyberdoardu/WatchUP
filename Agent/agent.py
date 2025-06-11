import os
import time
import subprocess
import requests
import re
import hashlib
import json
from threading import Thread, Lock
from flask import Flask, request, jsonify
import logging
from datetime import datetime
import json
from collections import deque
logging.basicConfig(level=logging.INFO)

targets = []
agent_credentials = {}
credentials_lock = Lock()
CREDENTIALS_PATH = '/credentials/credentials.json'
CENTRAL_SERVER_URL = os.environ.get('CENTRAL_SERVER_URL')

SALT = "salzinho_pra_dar_g0st0"

# --- Fila para Métricas
metrics_queue = deque()
queue_lock = Lock()


# --- Lógica de Credenciais ---
def load_credentials():
    """Carrega as credenciais do arquivo JSON, se existir."""
    global agent_credentials
    if os.path.exists(CREDENTIALS_PATH):
        try:
            with credentials_lock:
                with open(CREDENTIALS_PATH, 'r') as f:
                    agent_credentials = json.load(f)
                    if 'agent_id' in agent_credentials and 'api_key' in agent_credentials:
                        logging.info("Credenciais do agente carregadas do arquivo.")
                        return True
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Não foi possível carregar o arquivo de credenciais: {e}")
    return False

def save_credentials():
    """Salva as credenciais no arquivo JSON."""
    try:
        os.makedirs(os.path.dirname(CREDENTIALS_PATH), exist_ok=True)
        with credentials_lock:
            with open(CREDENTIALS_PATH, 'w') as f:
                json.dump(agent_credentials, f, indent=4)
            logging.info(f"Credenciais salvas para o agente ID: {agent_credentials.get('agent_id')}")
    except IOError as e:
        logging.error(f"Não foi possível salvar o arquivo de credenciais: {e}")

def ping_check(target, timeout=5, count=4):
    command = f"ping -c {count} -W {timeout} {target}"
    print(f"\n=== EXECUTANDO PING ===")
    print(f"Comando: {command}")
    
    try:
        # Executar com timeout adicional como fallback
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout + 2  # Tempo extra como margem de segurança
        )
        
        print("=== SAÍDA COMPLETA ===")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        print(f"STATUS CODE: {result.returncode}")
        print("======================")
        
        return {
            'success': 1 if result.returncode == 0 else 0,
            'output': f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        }
        
    except subprocess.TimeoutExpired as e:
        print("=== TIMEOUT ===")
        print(f"Erro: {str(e)}")
        print(f"Saída parcial: {e.stdout.decode() if e.stdout else ''}")
        print("================")
        return {
            'success': 0,
            'output': f"Timeout: {str(e)}"
        }
        
    except Exception as e:
        print("=== ERRO GENÉRICO ===")
        print(f"Tipo do erro: {type(e).__name__}")
        print(f"Detalhes: {str(e)}")
        print("=====================")
        return {
            'success': 0,
            'output': f"Erro: {str(e)}"
        }

def process_monitor(monitor):
    """Executa a verificação específica do monitor com logging detalhado"""
    result = {'success': 0, 'raw_result': None, 'response_time': 0}
    start_time = time.time()
    
    try:
        params = monitor['parameters']
        check_type = monitor['check_type']
        
        # CORRIGIDO: Adicionado 'params.get('url')' para compatibilidade com monitores antigos.
        target_address = params.get('target') or params.get('host') or params.get('url')
        if not target_address:
            # CORRIGIDO: Mensagem de erro atualizada para incluir 'url'.
            raise ValueError("Parâmetro 'target', 'host' ou 'url' não encontrado no monitor")

        print(f"\n=== PROCESSANDO {check_type.upper()} ===")
        print(f"Alvo: {target_address}") 
        
        if check_type == 'ping':
            ping_result = ping_check(
                target_address, 
                count=int(params.get('count', 4)),
                timeout=int(params.get('timeout', 2))
            )
            result['success'] = ping_result['success']
            result['raw_result'] = ping_result['output']
            
        elif check_type == 'http_status':
            expected_status = int(params.get('match', 200))
            response = requests.get(target_address, timeout=int(params.get('timeout', 5)))
            result['success'] = 1 if response.status_code == expected_status else 0
            result['raw_result'] = f"Status Recebido: {response.status_code}"
            
        elif check_type == 'api_response':
            response = requests.get(target_address, timeout=int(params.get('timeout', 5)))
            content = response.text[:500] + '...' if len(response.text) > 500 else response.text
            
            if 'regex' in params and params['regex']:
                match = re.search(params['regex'], response.text)
                result['success'] = 1 if match else 0
            elif 'match' in params and params['match']:
                result['success'] = 1 if params.get('match') in response.text else 0
            else:
                 raise ValueError("Parâmetro 'match' ou 'regex' obrigatório para api_response")
            
            #if not result['success']: Comentei para salvar sempre
            result['raw_result'] = content

        print(f"Resultado: {'SUCESSO' if result['success'] else 'FALHA'}")

    except Exception as e:
        print(f"Erro durante execução do monitor: {str(e)}")
        result['raw_result'] = str(e)
    
    finally:
        result['response_time'] = (time.time() - start_time) * 1000
        return result
            
def hash_agent_name(agent_name, salt):
    combined = f"{agent_name}:{salt}"
    hashed = hashlib.sha256(combined.encode()).hexdigest()
    return hashed

def register_agent():
    """Registra o agente se não houver credenciais."""
    with credentials_lock:
        if agent_credentials:
            logging.info("Agente já possui credenciais, pulando registro.")
            return True # Indica que as credenciais estão prontas

    agent_name = os.environ.get('AGENT_NAME')
    agent_id = os.environ.get('AGENT_ID') 

    if not agent_name or not agent_id:
        logging.critical("AGENT_NAME e AGENT_ID devem ser definidos. Terminando o processo de registro.")
        return False

    logging.info(f"Tentando registrar o agente '{agent_name}' com ID '{agent_id}'...")
    
    for i in range(5):
        try:
            response = requests.post(
                f"{CENTRAL_SERVER_URL}/register",
                json={'agent_name': agent_name, 'agent_id': agent_id},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            with credentials_lock:
                agent_credentials['api_key'] = data['api_key']
                agent_credentials['agent_id'] = agent_id
            save_credentials()
            logging.info(f"Agente registrado com sucesso! Mensagem: {data['message']}")
            return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Falha na tentativa {i+1} de registro: {e}")
            time.sleep(10)
    
    return False # Retorna falso se não conseguir registrar

def get_auth_headers():
    """Retorna os cabeçalhos de autenticação para as requisições."""
    with credentials_lock:
        if not agent_credentials:
            return None
        return {
            'X-API-Key': agent_credentials.get('api_key'),
            'X-Agent-ID': agent_credentials.get('agent_id')
        }
            
def send_heartbeat():
    """Envia heartbeats periódicos para o servidor central."""
    while True:
        headers = get_auth_headers()
        if headers:
            try:
                requests.post(
                    f"{CENTRAL_SERVER_URL}/heartbeat",
                    headers=headers,
                    timeout=5
                )
            except requests.exceptions.RequestException as e:
                logging.error(f"Falha no heartbeat: {e}")
        time.sleep(30)

def update_targets():
    """Busca a lista de monitores (alvos) do servidor central."""
    global targets
    while True:
        headers = get_auth_headers()
        if headers:
            try:
                logging.info("Atualizando lista de alvos...")
                response = requests.get(
                    f"{CENTRAL_SERVER_URL}/targets",
                    headers=headers,
                    timeout=10
                )
                if response.ok:
                    with credentials_lock:
                        targets = response.json() or []
                    logging.info(f"{len(targets)} alvos recebidos.")
                else:
                    logging.error(f"Erro ao buscar alvos: Status {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                logging.error(f"Erro de conexão ao buscar alvos: {e}")
        time.sleep(15)
        
def monitoring_loop():
    """Loop principal que executa as verificações, enfileira e envia as métricas."""
    last_check = {}
    
    while True:
        if not agent_credentials:
            logging.info("Aguardando credenciais para iniciar o monitoramento...")
            time.sleep(10)
            continue
            
        new_metrics = []
        with credentials_lock:
            current_targets = list(targets)

        for monitor in current_targets:
            try:
                monitor_id = monitor['id']
                params = monitor.get('parameters', {})
                check_interval = int(params.get('check_time', 60))
                
                if (time.time() - last_check.get(monitor_id, 0)) >= check_interval:
                    logging.info(f"Executando monitor: {monitor.get('monitor_name', 'N/A')}")
                    result = process_monitor(monitor)
                    
                    # Adiciona o timestamp no momento da coleta
                    new_metrics.append({
                        'monitor_id': monitor_id,
                        'timestamp': datetime.now().isoformat(),
                        'success': result['success'],
                        'response_time': result['response_time'],
                        'raw_result': result.get('raw_result')
                    })
                    last_check[monitor_id] = time.time()
            except Exception as e:
                logging.error(f"Erro no loop do monitor {monitor.get('id')}: {e}")

        # Adiciona as novas métricas à fila principal
        if new_metrics:
            with queue_lock:
                metrics_queue.extend(new_metrics)
                logging.info(f"Adicionado {len(new_metrics)} novas métricas à fila. Tamanho atual: {len(metrics_queue)}")

        # Se a fila não estiver vazia, tenta enviar os dados
        if metrics_queue:
            headers = get_auth_headers()
            if headers:
                metrics_to_send = []
                with queue_lock:
                    metrics_to_send = list(metrics_queue) # Cria uma cópia para o envio

                try:
                    logging.info(f"Tentando enviar {len(metrics_to_send)} métricas da fila...")
                    response = requests.post(
                        f"{CENTRAL_SERVER_URL}/metrics",
                        headers=headers,
                        json={'metrics': metrics_to_send},
                        timeout=10
                    )
                    response.raise_for_status() # Lança exceção para respostas 4xx/5xx

                    # Se o envio foi bem-sucedido, remove os itens enviados da fila
                    with queue_lock:
                        for _ in range(len(metrics_to_send)):
                            metrics_queue.popleft()
                    logging.info(f"Envio de {len(metrics_to_send)} métricas bem-sucedido. Fila agora com {len(metrics_queue)} itens.")

                except Exception as e:
                    # Em caso de falha, os itens permanecem na fila
                    logging.error(f"Falha no envio de métricas: {e}. As métricas permanecem na fila ({len(metrics_queue)} itens).")
        
        time.sleep(1)


if __name__ == '__main__':
    if not CENTRAL_SERVER_URL:
        logging.critical("Variável de ambiente CENTRAL_SERVER_URL não definida. Encerrando.")
    else:
        # Tenta carregar credenciais. Se não conseguir, tenta registrar.
        if load_credentials() or register_agent():
            logging.info("Agente pronto para operar. Iniciando threads de background.")
            Thread(target=send_heartbeat, daemon=True).start()
            Thread(target=update_targets, daemon=True).start()
            monitoring_loop() # Inicia o loop principal
        else:
            logging.critical("Não foi possível obter credenciais após várias tentativas. O agente será encerrado.")