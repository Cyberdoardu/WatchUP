# WatchUP Monitoring 

<p align="center">
  <strong>Uma solução de monitoramento distribuído, simples e eficaz para acompanhar a saúde dos seus serviços.</strong>
</p>

---

### 🛰️ Por Que Usar o WatchUP?

Em um cenário onde a disponibilidade de serviços é crucial, ter uma ferramenta de monitoramento se torna indispensável. WatchUP foi criado para ser:

* **Simples e Leve:** Fácil de implantar e com baixo consumo de recursos, ideal para ambientes de todos os tamanhos.
* **Centralizado e Intuitivo:** Oferece uma visão clara e unificada do status de todos os seus serviços, permitindo que equipes identifiquem e reajam a problemas rapidamente.
* **Flexível:** Com suporte a diferentes tipos de verificação, ele se adapta a diversas necessidades, desde um simples ping em um servidor até a validação complexa de uma resposta de API.
* **Orientado a DevOps:** Totalmente containerizado e pronto para orquestração, se integra perfeitamente a fluxos de trabalho modernos de CI/CD e infraestrutura como código.

### ✨ Principais Funcionalidades

* **Monitoramento Distribuído:** Implante agentes leves em diferentes máquinas para monitorar seus serviços de várias perspectivas.
* **Diversos Tipos de Verificação:**
    * **Ping (ICMP):** Verifica a conectividade básica de um host.
    * **Status HTTP:** Garante que uma URL está respondendo com o código de status esperado (ex: 200 OK).
    * **Resposta de API:** Valida o conteúdo de uma resposta de API, verificando a presença de uma palavra-chave ou correspondência com uma expressão regular (Regex).
* **Dashboard Centralizado:** Uma visão geral e limpa do estado atual de todos os seus monitores, incluindo um histórico de disponibilidade dos últimos 90 dias.
* **Gerenciamento de Monitores:** Crie, configure e associe monitores a agentes específicos através da interface web.
* **Gerador de Relatórios de SLA 📄:** Selecione um monitor e um período para gerar e baixar um relatório de disponibilidade em formato PDF.
* **Gestão de Incidentes:** Uma interface para criar e acompanhar o ciclo de vida de incidentes, desde a identificação até a resolução.
* **Pronto para Contêineres 🐳:** Todo o sistema é containerizado usando Docker e pode ser iniciado com um único comando.
* **Pronto para Kubernetes:** Inclui manifestos de implantação para orquestração em um ambiente K8s.

---

### Quickstart com Docker

A maneira mais rápida de colocar o WatchUP para funcionar é usando o Docker Compose.

**Pré-requisitos:**
* Docker
* Docker Compose

**Passos:**

1.  **Clone o repositório:**
    ```sh
    git clone [https://github.com/Cyberdoardu/WatchUP.git](https://github.com/Cyberdoardu/WatchUP.git)
    cd WatchUP
    ```

2.  **Inicie os serviços:**
    Execute o seguinte comando na raiz do projeto para construir as imagens e iniciar todos os contêineres em segundo plano:
    ```sh
    docker-compose up -d --build
    ```

3.  **Acesse a Aplicação Web:**
    * A interface web estará disponível em: **`http://localhost:8080`**
    * Na primeira vez que acessar, crie o usuário administrador em: `http://localhost:8080/admin-cadastro.html`
    * Após criar o admin, você pode fazer login em: `http://localhost:8080/login.html`

4.  **Próximos Passos:**
    * Após o login, navegue até a página **Criar Monitor** para configurar suas primeiras verificações.
    * O `docker-compose.yml` inicia um agente padrão chamado `agent-01` que você pode usar imediatamente.

---

### 🛠️ Arquitetura

O sistema é composto por quatro microserviços principais que trabalham em conjunto.

```text
       ┌────────────────┐      ┌────────────────────┐
       │     Usuário    │      │       Agente       │
       └────────────────┘      └────────────────────┘
               │                       │ (Métricas)
 (Navegador Web) │                       │
               ▼                       ▼
       ┌───────────────┐     ┌────────────────────┐
       │   WebApp (PHP)│◀───▶│ Servidor Central   │
       │  (Porta 8080) │     │  (Python/Flask)    │
       └───────────────┘     └────────────────────┘
               │ (Proxy API)           │ (Leitura/Escrita)
               │                       │
               │                       ▼
               │             ┌────────────────────┐
               └────────────▶│  Banco de Dados    │
                             │ (MariaDB)          │
                             └────────────────────┘
```


* **Servidor Central (`/Central`):** Uma API em Python (Flask) que gerencia os agentes, armazena os dados das métricas, processa a lógica de status e atende às solicitações da Webapp.
* **Agente de Monitoramento (`/Agent`):** Um serviço em Python que se registra no Servidor Central, recebe uma lista de alvos para monitorar e reporta os resultados das verificações.
* **WebApp (`/Webapp`):** Uma aplicação Apache/PHP com uma interface em HTML/JS/TailwindCSS que serve como o ponto de entrada para o usuário. Ela se comunica com o Servidor Central através de um gateway de API interno.
* **Banco de Dados (`/bd`):** Uma instância MariaDB que persiste todos os dados, incluindo usuários, agentes, monitores, configurações e resultados de métricas.

---

### 💻 Pilha Tecnológica

* **Backend:** Python 3, Flask
* **Frontend:** HTML5, TailwindCSS, JavaScript
* **Backend do WebApp:** PHP, Apache
* **Banco de Dados:** MariaDB
* **Containerização:** Docker, Docker Compose
* **Orquestração:** Kubernetes (k8s)




