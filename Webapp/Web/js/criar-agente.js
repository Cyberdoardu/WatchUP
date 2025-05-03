document.addEventListener('DOMContentLoaded', () => {
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
        if (!agentNameInput) return;
        const agentName = agentNameInput.value;
         fetch('/create-agent', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ agent_name: agentName }),
        })
        .then(response => response.json())
        .then(data => {
            alert(JSON.stringify(data));
        });
    });
    updateDockerCommand();
});