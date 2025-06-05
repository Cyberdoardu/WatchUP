// Jenkinsfile para build e deploy do projeto WatchUP no MicroK8s

pipeline {
    agent any // Ou um agente específico com as ferramentas necessárias (docker, microk8s, git)

    environment {
        // Definindo os nomes das imagens para consistência
        CENTRAL_SERVER_IMAGE = 'central-server:latest'
        MONITORING_AGENT_IMAGE = 'monitoring-agent:latest'
        WEBAPP_IMAGE = 'webapp:latest'
        K8S_DEPLOY_FILE = 'k8s-deploy.yaml' // Nome do arquivo de manifesto Kubernetes
        MARIADB_INIT_SCRIPT_PATH = './bd/schema/init.sql'
        CONFIGMAP_NAME = 'mariadb-init-scripts'
    }

    stages {
        stage('Checkout SCM') {
            steps {
                echo '>>> Clonando o repositório...'
                // Substitua pela URL do seu repositório e branch, se necessário
                git url: 'https://github.com/Cyberdoardu/WatchUP.git', branch: 'main'

                // Verifica se o arquivo k8s-deploy.yaml existe
                script {
                    if (!fileExists(env.K8S_DEPLOY_FILE)) {
                        error "Arquivo ${env.K8S_DEPLOY_FILE} não encontrado na raiz do repositório!"
                    }
                    if (!fileExists(env.MARIADB_INIT_SCRIPT_PATH)) {
                        error "Arquivo de inicialização do BD ${env.MARIADB_INIT_SCRIPT_PATH} não encontrado!"
                    }
                }
            }
        }

        stage('Build Docker Images') {
            steps {
                script {
                    echo ">>> Construindo imagem ${env.CENTRAL_SERVER_IMAGE}..."
                    // O contexto é o diretório ./Central
                    sh "docker build -t ${env.CENTRAL_SERVER_IMAGE} ./Central"

                    echo ">>> Construindo imagem ${env.MONITORING_AGENT_IMAGE}..."
                    // O contexto é o diretório ./Agent
                    sh "docker build -t ${env.MONITORING_AGENT_IMAGE} ./Agent"

                    echo ">>> Construindo imagem ${env.WEBAPP_IMAGE}..."
                    // O contexto é ./Webapp e o Dockerfile está em ./Webapp/setup_files/Dockerfile
                    sh "docker build -t ${env.WEBAPP_IMAGE} -f ./Webapp/setup_files/Dockerfile ./Webapp"
                }
                echo '>>> Verificando imagens Docker construídas...'
                sh 'docker images'
            }
        }

        stage('Load Images to MicroK8s') {
            steps {
                script {
                    echo ">>> Carregando imagem ${env.CENTRAL_SERVER_IMAGE} para o MicroK8s..."
                    sh "docker save ${env.CENTRAL_SERVER_IMAGE} | microk8s ctr image import -"

                    echo ">>> Carregando imagem ${env.MONITORING_AGENT_IMAGE} para o MicroK8s..."
                    sh "docker save ${env.MONITORING_AGENT_IMAGE} | microk8s ctr image import -"

                    echo ">>> Carregando imagem ${env.WEBAPP_IMAGE} para o MicroK8s..."
                    sh "docker save ${env.WEBAPP_IMAGE} | microk8s ctr image import -"
                }
            }
        }

        stage('Prepare Kubernetes Resources') {
            steps {
                echo ">>> Preparando recursos Kubernetes..."
                // Apaga o ConfigMap antigo, se existir, para evitar conflitos
                // O '|| true' é para não falhar o pipeline se o configmap não existir na primeira vez
                sh "microk8s kubectl delete configmap ${env.CONFIGMAP_NAME} --ignore-not-found=true"

                echo ">>> Criando ConfigMap ${env.CONFIGMAP_NAME} para o schema do BD..."
                sh "microk8s kubectl create configmap ${env.CONFIGMAP_NAME} --from-file=${env.MARIADB_INIT_SCRIPT_PATH}"
            }
        }

        stage('Deploy to MicroK8s') {
            steps {
                echo ">>> Aplicando manifestos Kubernetes do arquivo ${env.K8S_DEPLOY_FILE}..."
                // Aplica o arquivo k8s-deploy.yaml que deve estar na raiz do workspace
                sh "microk8s kubectl apply -f ${env.K8S_DEPLOY_FILE}"

                echo ">>> Aguardando alguns segundos para os pods estabilizarem..."
                sleep 30 // Pausa para dar tempo aos pods de subirem

                echo ">>> Verificando status dos pods..."
                sh "microk8s kubectl get pods -o wide"

                echo ">>> Verificando status dos services..."
                sh "microk8s kubectl get services -o wide"
            }
        }
    }

    post {
        always {
            echo 'Pipeline finalizado.'
            // Adicione aqui passos de limpeza, se necessário
            // Ex: sh 'docker image prune -af' // CUIDADO: remove todas as imagens não utilizadas
        }
        success {
            echo 'Deploy realizado com sucesso!'
            // Adicionar notificações de sucesso (email, Slack, etc.)
        }
        failure {
            echo 'Deploy falhou.'
            // Adicionar notificações de falha
        }
    }
}
