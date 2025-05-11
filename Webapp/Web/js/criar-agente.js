document.addEventListener('DOMContentLoaded', function() {
    function updateDockerCommand() {
        const agentNameInput = document.querySelector('input[name="agent-name"]');
        const centralServerIpInput = document.querySelector('input[name="central-server-ip"]');
        const dockerCommandDiv = document.querySelector('div#docker-command');
        if (!agentNameInput || !centralServerIpInput || !dockerCommandDiv) return;
        const agentName = agentNameInput.value;
        const centralServerIp = centralServerIpInput.value;
        const dockerCommand = `docker run --name ${agentName} -e AGENT_NAME=${agentName} -e CENTRAL_SERVER_URL=http://${centralServerIp}:5000 --network host -d devsecops-monitoring-agent:latest`;
        dockerCommandDiv.textContent = dockerCommand;
    }
    const agentNameInput = document.querySelector('input[name="agent-name"]');
    const centralServerIpInput = document.querySelector('input[name="central-server-ip"]');
    const dockerCommandDiv = document.querySelector('div#docker-command');
    const createButton = document.querySelector('button#create-button');
    
    console.log("agentNameInput found: " + (agentNameInput !== null));
    console.log("centralServerIpInput found: " + (centralServerIpInput !== null));
    console.log("dockerCommandDiv found: " + (dockerCommandDiv !== null));
    console.log("createButton found: " + (createButton !== null));

    
    agentNameInput.addEventListener('input', updateDockerCommand);
    centralServerIpInput.addEventListener('input', updateDockerCommand);

    

    createButton.addEventListener('click', () => {
        if (!agentNameInput || !createButton) return;
        const agentName = agentNameInput.value;
        
        let timerDiv = document.getElementById('timer');
        if (!timerDiv) {
          timerDiv = document.createElement('div');
          timerDiv.id = 'timer';
          createButton.parentNode.insertBefore(timerDiv, createButton.nextSibling);
        }
        
        createButton.disabled = true;
        timerDiv.textContent = "Aguardando criação de agente..."
        
        
        let timerInterval;
        let remainingTime = 60;
        
        const updateTimerDisplay = () => {
            timerDiv.textContent = `Tempo restante: ${remainingTime} segundos`;
        }

        fetch('php/criar-agente.php', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: `action=create_agent&agent_name=${agentName}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                 timerInterval = setInterval(() => {
                    updateTimerDisplay();
                    remainingTime--;
                    if (remainingTime < 0) {
                        clearInterval(timerInterval);
                        timerDiv.textContent = 'Falha na criação do agente.';
                        createButton.disabled = false;
                    }else if (data.status == "connected"){
                        clearInterval(timerInterval);
                        timerDiv.textContent = 'Agente criado com sucesso.';
                        setTimeout(() => {
                            location.reload(); 
                        }, 2000);
                    }
                }, 1000);               
            }else{
                alert(response);
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('Erro ao se comunicar com o servidor.');
        });
    });
        updateDockerCommand();
});