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
        MICROK8S_CMD = 'sudo /snap/bin/microk8s'
    }

    stages {
        stage('Checkout SCM') {
            steps {
                echo '>>> Clonando o repositório...'
                git url: 'https://github.com/Cyberdoardu/WatchUP.git', branch: 'main'
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
                    sh "docker build -t ${env.CENTRAL_SERVER_IMAGE} ./Central"

                    echo ">>> Construindo imagem ${env.MONITORING_AGENT_IMAGE}..."
                    sh "docker build -t ${env.MONITORING_AGENT_IMAGE} ./Agent"

                    echo ">>> Construindo imagem ${env.WEBAPP_IMAGE}..."
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
                    sh "docker save ${env.CENTRAL_SERVER_IMAGE} | ${env.MICROK8S_CMD} ctr image import -"

                    echo ">>> Carregando imagem ${env.MONITORING_AGENT_IMAGE} para o MicroK8s..."
                    sh "docker save ${env.MONITORING_AGENT_IMAGE} | ${env.MICROK8S_CMD} ctr image import -"

                    echo ">>> Carregando imagem ${env.WEBAPP_IMAGE} para o MicroK8s..."
                    sh "docker save ${env.WEBAPP_IMAGE} | ${env.MICROK8S_CMD} ctr image import -"
                }
            }
        }

        stage('Prepare Kubernetes Resources') {
            steps {
                echo ">>> Preparando recursos Kubernetes..."
                sh "${env.MICROK8S_CMD} kubectl delete configmap ${env.CONFIGMAP_NAME} --ignore-not-found=true"
                echo ">>> Criando ConfigMap ${env.CONFIGMAP_NAME} para o schema do BD..."
                sh "${env.MICROK8S_CMD} kubectl create configmap ${env.CONFIGMAP_NAME} --from-file=${env.MARIADB_INIT_SCRIPT_PATH}"
            }
        }

        stage('Deploy to MicroK8s') {
            steps {
                echo ">>> Aplicando manifestos Kubernetes do arquivo ${env.K8S_DEPLOY_FILE}..."
                sh "${env.MICROK8S_CMD} kubectl apply -f ${env.K8S_DEPLOY_FILE}"

                // <<< INÍCIO DA CORREÇÃO >>>
                echo ">>> Forçando a atualização dos pods para usar as novas imagens..."
                sh "${env.MICROK8S_CMD} kubectl rollout restart deployment/webapp"
                sh "${env.MICROK8S_CMD} kubectl rollout restart deployment/central-server"
                sh "${env.MICROK8S_CMD} kubectl rollout restart deployment/monitoring-agent"
                // <<< FIM DA CORREÇÃO >>>

                echo ">>> Aguardando alguns segundos para os pods estabilizarem..."
                sleep 30 

                echo ">>> Verificando status dos pods..."
                sh "${env.MICROK8S_CMD} kubectl get pods -o wide"

                echo ">>> Verificando status dos services..."
                sh "${env.MICROK8S_CMD} kubectl get services -o wide"
            }
        }
    }

    post {
        always {
            echo 'Pipeline finalizado.'
        }
        success {
            echo 'Deploy realizado com sucesso!'
        }
        failure {
            echo 'Deploy falhou.'
        }
    }
}
