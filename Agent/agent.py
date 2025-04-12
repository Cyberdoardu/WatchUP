# = == = = = == = LEMBRETE: = = = = = == = = = =
#
#
#
# Adicionar o tempo entre requisições no banco e monitor
#
#
#
#= = = = = = == = = = = = = == = = = = = = = ===

import os
import time
import subprocess
import requests
import re  # Adicionando o import do módulo re
from threading import Thread
from flask import Flask, request, jsonify
import logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
targets = []
registered = False

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
            print(f"\n=== ATUALIZANDO TARGETS ===")
            response = requests.get(
                f"{os.environ['CENTRAL_SERVER_URL']}/targets",
                params={'agent': os.environ['AGENT_NAME']},
                timeout=5
            )
            print(f"Status Code: {response.status_code}")
            
            if response.ok:
                global targets
                targets = response.json() or []
                print(f"Targets recebidos ({len(targets)}):")
                for t in targets:
                    print(f" - {t['monitor_name']} ({t['check_type']})")
                    print(f"   Parâmetros: {t['parameters']}")  # Debug detalhado
            else:
                print(f"Erro HTTP: {response.status_code}")
                print(f"Resposta: {response.text}")
                
        except Exception as e:
            print(f"Erro geral: {str(e)}")
        
        time.sleep(10)
        
def monitoring_loop():
    while True:
        try:
            print("\n=== INÍCIO DO CICLO DE MONITORAMENTO ===")
            
            if not registered:
                print("Agente não registrado, tentando novamente...")
                register_agent()
                time.sleep(5)
                continue
                
            if not targets:
                print("Nenhum monitor definido, aguardando...")
                time.sleep(10)
                continue
                
            print(f"Monitores ativos: {len(targets)}")
            for idx, monitor in enumerate(targets, 1):
                print(f"Monitor {idx}: {monitor['monitor_name']} ({monitor['check_type']})")
                
            metrics = []
            
            for monitor in targets:
                try:
                    print(f"\nProcessando monitor: {monitor['monitor_name']}")
                    print(f"Tipo: {monitor['check_type']}")
                    print(f"Parâmetros: {monitor['parameters']}")
                    
                    start_time = time.time()
                    
                    if monitor['check_type'] == 'ping':
                        print("Iniciando check de ping...")
                        result = ping_check(
                            monitor['parameters']['target'],
                            timeout=monitor['parameters'].get('timeout', 5),
                            count=monitor['parameters'].get('count', 4)
                        )
                        print(f"Resultado do ping: {result}")
                        
                        metrics.append({
                            'monitor_id': monitor['id'],
                            'response_time': (time.time() - start_time) * 1000,
                            'success': result['success'],
                            'raw_output': result['output']
                        })
                        
                    elif monitor['check_type'] == 'http_status':
                        # Processar HTTP
                        url = monitor['parameters']['url']
                        expected_status = monitor['parameters'].get('expected_status', 200)
                        timeout = monitor['parameters'].get('timeout', 5)
                        
                        try:
                            response = requests.get(url, timeout=timeout)
                            success = 1 if response.status_code == expected_status else 0
                            raw_result = {
                                'url': url,
                                'status_code': response.status_code,
                                'response_time': response.elapsed.total_seconds()
                            }
                        except Exception as e:
                            raw_result = {'error': str(e)}
                            success = 0
                    
                    elif monitor['check_type'] == 'api_response':
                        # Processar API
                        url = monitor['parameters']['url']
                        regex_pattern = monitor['parameters'].get('regex', '')
                        expected_match = monitor['parameters'].get('expected_match', '')
                        timeout = monitor['parameters'].get('timeout', 5)
                        
                        try:
                            response = requests.get(url, timeout=timeout)
                            
                            if regex_pattern:
                                match = re.search(regex_pattern, response.text)
                                success = 1 if match else 0
                            elif expected_match:
                                success = 1 if expected_match in response.text else 0
                            else:
                                success = 1  # Se não tiver critérios, considera sucesso
                                
                            raw_result = {
                                'url': url,
                                'status_code': response.status_code,
                                'match_found': bool(match) if 'match' in locals() else None
                            }
                        except Exception as e:
                            raw_result = {'error': str(e)}
                            success = 0
                    
                    # Construir métrica padronizada
                    metrics.append({
                        'monitor_id': monitor['id'],
                        'response_time': (time.time() - start_time) * 1000,  # ms
                        'success': success,  # Alterando de 'result_code' para 'success'
                        'raw_result': raw_result
                    })
                    
                except Exception as e:
                    print(f"Erro no monitor {monitor['id']}: {str(e)}")
                    metrics.append({
                        'monitor_id': monitor['id'],
                        'response_time': 0,
                        'success': 0,  # Alterando para uso de 'success'
                        'raw_result': {'error': str(e)}
                    })

            # Enviar métricas processadas
            if metrics:
                try:
                    response = requests.post(
                        f"{os.environ['CENTRAL_SERVER_URL']}/metrics",
                        json={
                            'agent_id': os.environ['AGENT_NAME'],
                            'metrics': metrics
                        },
                        timeout=10
                    )
                    response.raise_for_status()
                except Exception as e:
                    print(f"Erro ao enviar métricas: {str(e)}")
            
        except Exception as e:
            print(f"Erro crítico no loop de monitoramento: {str(e)}")
        
        time.sleep(int(os.environ.get('CHECK_INTERVAL', 30)))

if __name__ == '__main__':
    register_agent()
    Thread(target=send_heartbeat, daemon=True).start()
    Thread(target=update_targets, daemon=True).start()
    Thread(target=monitoring_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5001)