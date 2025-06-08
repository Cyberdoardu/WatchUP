import os
import time
import subprocess
import requests
import re
import hashlib
from threading import Thread
from flask import Flask, request, jsonify
import logging
from datetime import datetime
logging.basicConfig(level=logging.INFO)

targets = []
registered = False

SALT = "salzinho_pra_dar_g0st0"


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
    global registered
    max_retries = 10
    retry_count = 0
    
    while not registered and retry_count < max_retries:
        try:
            hashed_agent_id = hash_agent_name(os.environ['AGENT_NAME'], SALT)
            response = requests.post(
                f"{os.environ['CENTRAL_SERVER_URL']}/register",
                json={'agent_name': os.environ['AGENT_NAME'], 'agent_id': hashed_agent_id},
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
    hashed_agent_id = hash_agent_name(os.environ['AGENT_NAME'], SALT)
    while True:
        try:
            requests.post(
                f"{os.environ['CENTRAL_SERVER_URL']}/heartbeat",
                json={'agent_id': hashed_agent_id},
                timeout=3
            )
        except Exception as e:
            print(f"Falha no heartbeat: {str(e)}")
        time.sleep(30)

def update_targets():
    hashed_agent_id = hash_agent_name(os.environ['AGENT_NAME'], SALT)
    while True:
        try:
            print(f"\n=== ATUALIZANDO TARGETS ===")
            response = requests.get(
                f"{os.environ['CENTRAL_SERVER_URL']}/targets?agent_id={hashed_agent_id}",
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
                    print(f"   Parâmetros: {t['parameters']}")
            else:
                print(f"Erro HTTP: {response.status_code}")
                print(f"Resposta: {response.text}")
                
        except Exception as e:
            print(f"Erro geral: {str(e)}")
        
        time.sleep(10)
        
def monitoring_loop():
    """Loop principal de monitoramento com controle de intervalos"""
    last_check = {}
    
    while True:
        try:
            print("\n" + "="*50)
            print(f"Ciclo iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Verificar registro do agente
            if not registered:
                print("Agente não registrado, tentando novamente...")
                register_agent()
                time.sleep(5)
                continue
                
            # Verificar existência de monitores
            if not targets:
                print("Nenhum monitor definido, aguardando...")
                time.sleep(10)
                continue
                
            print(f"Monitores cadastrados: {len(targets)}")
            metrics = []
            
            # Processar cada monitor
            for monitor in targets:
                monitor_id = monitor['id']
                try:
                    # Calcular intervalo
                    check_interval = monitor['parameters'].get('check_time', 60)
                    last_time = last_check.get(monitor_id, 0)
                    
                    if (time.time() - last_time) < check_interval:
                        print(f"Monitor {monitor['monitor_name']} ({monitor_id}) aguardando próximo ciclo ({check_interval}s)")
                        continue
                        
                    print(f"\n=== INICIANDO VERIFICAÇÃO [{monitor['monitor_name']}] ===")
                    
                    # Executar verificação
                    result = process_monitor(monitor)
                    
                    # Coletar métricas
                    metrics.append({
                        'monitor_id': monitor_id,
                        'success': result['success'],
                        'response_time': result['response_time'],
                        'raw_result': result.get('raw_result')
                    })
                    
                    # Atualizar último check
                    last_check[monitor_id] = time.time()
                    print(f"Verificação completa. Próximo check em {check_interval}s")
                    
                except Exception as e:
                    print(f"Erro crítico no monitor {monitor_id}: {str(e)}")
                    metrics.append({
                        'monitor_id': monitor_id,
                        'success': 0,
                        'response_time': 0,
                        'raw_result': f"Erro de processamento: {str(e)}"
                    })

            # Enviar métricas coletadas
            if metrics:
                print("\nEnviando métricas para o servidor central...")
                try:
                    hashed_agent_id = hash_agent_name(os.environ['AGENT_NAME'], SALT)
                    response = requests.post(
                        f"{os.environ['CENTRAL_SERVER_URL']}/metrics",
                        json={'agent_id': hashed_agent_id, 'metrics': metrics},
                        timeout=10
                    )
                    response.raise_for_status()
                    
                    print(f"Status do envio: {response.status_code}")
                except Exception as e:
                    print(f"Falha no envio de métricas: {str(e)}")
            
        except Exception as e:
            print(f"ERRO GLOBAL NO LOOP: {str(e)}")
        
        # Intervalo entre ciclos completos
        time.sleep(1)

if __name__ == '__main__':
    register_agent()
    Thread(target=send_heartbeat, daemon=True).start()
    Thread(target=update_targets, daemon=True).start()
    Thread(target=monitoring_loop, daemon=True).start()
    while True:
        time.sleep(15)