document.addEventListener('DOMContentLoaded', function () {
    const agentSelect = document.getElementById('agentId');
    const verificationTypeSelect = document.getElementById('verificationType');
    const httpOptions = document.getElementById('httpOptions');
    const apiOptions = document.getElementById('apiOptions');
    const pingOptions = document.getElementById('pingOptions');
    const createMonitorForm = document.getElementById('createMonitorForm');
    const menuButton = document.getElementById('menuButton');

    menuButton.addEventListener('click', function() {
        window.location.href = 'menu.html';
    });

    fetch('php/api-gateway.php?endpoint=agents', {
        method: 'GET',
        headers: {
            'Accept': 'application/json' 
        }
    })
    .then(response => {
        console.log('Response Status (Agents):', response.status);
        console.log('Response Content-Type Header (Agents):', response.headers.get('Content-Type'));
        if (!response.ok) {
            return response.text().then(text => {
                throw new Error('Network response was not ok (Agents). Status: ' + response.status + '. Body: ' + text);
            });
        }
        return response.text(); 
    })
    .then(textData => {
        console.log('Raw text data received (Agents):', textData);
        try {
            const jsonData = JSON.parse(textData); 
            console.log('Parsed JSON data (Agents):', jsonData);

            if (Array.isArray(jsonData) && jsonData.length > 0) {
                agentSelect.innerHTML = '<option value="">Selecione o Agente</option>'; 
                jsonData.forEach(agent => {
                    const option = document.createElement('option');
                    option.value = agent.agent_id; 
                    option.textContent = agent.name + ' (' + agent.agent_id.substring(0,8) + ')';
                    agentSelect.appendChild(option);
                });
            } else if (Array.isArray(jsonData) && jsonData.length === 0) {
                 agentSelect.innerHTML = '<option value="">Nenhum agente encontrado</option>';
            } else {
                agentSelect.innerHTML = '<option value="">Erro ao carregar agentes (formato inesperado)</option>';
                console.error('Error fetching agents: Unexpected data format after parsing.', jsonData);
            }
        } catch (e) {
            agentSelect.innerHTML = '<option value="">Erro ao carregar agentes (falha no parse)</option>';
            console.error('Error parsing JSON response (Agents):', e);
            console.error('Raw text that failed to parse (Agents):', textData);
        }
    })
    .catch(error => {
        agentSelect.innerHTML = '<option value="">Erro crítico ao carregar agentes</option>';
        console.error('Critical error fetching agents:', error);
    });

    verificationTypeSelect.addEventListener('change', function () {
        httpOptions.style.display = 'none';
        apiOptions.style.display = 'none';
        pingOptions.style.display = 'none';

        const selectedType = this.value;
        if (selectedType === 'http_status') {
            httpOptions.style.display = 'block';
        } else if (selectedType === 'api') {
            apiOptions.style.display = 'block';
        } else if (selectedType === 'ping') {
            pingOptions.style.display = 'block';
        }
    });

    createMonitorForm.addEventListener('submit', function (event) {
        event.preventDefault();

        const formData = new FormData(this);
        let parameters = {};
        const checkType = formData.get('verificationType');

        if (checkType === 'http_status') {
            parameters.url = formData.get('targetUrl');
            parameters.match = formData.get('httpMatch') || '200'; 
        } else if (checkType === 'api') {
            parameters.url = formData.get('apiUrl');
            parameters.method = formData.get('apiMethod');
            parameters.match = formData.get('apiMatch');
            try {
                parameters.headers = formData.get('apiHeaders') ? JSON.parse(formData.get('apiHeaders')) : {};
            } catch (e) {
                alert('JSON inválido nos Cabeçalhos da API');
                return;
            }
            try {
                 parameters.body = formData.get('apiBody') ? JSON.parse(formData.get('apiBody')) : {};
            } catch (e) {
                alert('JSON inválido no Corpo da API');
                return;
            }
        } else if (checkType === 'ping') {
            parameters.host = formData.get('pingHost');
        }

        const monitorData = {
            monitor_name: formData.get('monitorName'),
            request_interval: parseInt(formData.get('requestInterval')),
            retention_days: parseInt(formData.get('retentionTime')), // Ajustado para retention_days
            agent: formData.get('agentId'),           // Ajustado para agent (usa agent_id do select)
            check_type: checkType,                    // Ajustado para check_type
            parameters: parameters,                   // Ajustado para parameters (era config)
            // is_primary é opcional, o Python já tem um default data.get('is_primary', True)
        };

        console.log("Dados enviados para criar monitor:", JSON.stringify(monitorData));

        fetch('php/api-gateway.php?endpoint=monitors', { 
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(monitorData)
        })
        .then(response => {
            console.log('Response Status (Create Monitor):', response.status);
            console.log('Response Content-Type Header (Create Monitor):', response.headers.get('Content-Type'));
            return response.json().catch(err => {
                console.error("Failed to parse JSON from create monitor response:", err);
                return response.text().then(text => { 
                    console.error("Non-JSON response from create monitor:", text);
                    return { status: 'error', message: 'Resposta inválida do servidor: ' + text.substring(0, 100) }; 
                });
            });
        })
        .then(data => {
            console.log("Parsed JSON data (Create Monitor):", data);
            // O python retorna diretamente os dados do monitor criado ou um erro.
            // Assumindo que o python, em sucesso, retorna os dados do monitor (com 'id')
            // e em erro, retorna um objeto com uma chave 'error'.
            if (data.id && !data.error) { // Sucesso se tiver um 'id' e não tiver 'error'
                alert('Monitor criado com sucesso! ID: ' + data.id);
                window.location.href = 'menu.html'; 
            } else if (data.error) { // Erro explícito do backend
                alert('Erro ao criar monitor: ' + (data.error || 'Erro desconhecido do servidor.'));
            } else {
                 alert('Erro ao criar monitor: Resposta inesperada do servidor.');
                 console.error("Unexpected response data (Create Monitor):", data);
            }
        })
        .catch(error => {
            console.error('Critical error creating monitor:', error);
            alert('Ocorreu um erro crítico ao criar o monitor.');
        });
    });
});
