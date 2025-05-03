document.addEventListener('DOMContentLoaded', () => {
    const agentNameInput = document.querySelector('input[name="agent-name"]'); // Change the query selector
    const centralServerIpInput = document.querySelector('input[name="central-server-ip"]'); // Change the query selector
    const dockerCommandDiv = document.querySelector('div#docker-command'); // Change the query selector
    const createButton = document.querySelector('button#create-button'); // Change the query selector
    
    console.log("agentNameInput found: " + (agentNameInput !== null)); // Add log
    console.log("centralServerIpInput found: " + (centralServerIpInput !== null)); // Add log
    console.log("dockerCommandDiv found: " + (dockerCommandDiv !== null)); // Add log
    console.log("createButton found: " + (createButton !== null)); // Add log

    function updateDockerCommand() {
        if (!agentNameInput || !centralServerIpInput || !dockerCommandDiv) return;
        const agentName = agentNameInput.value;
        const centralServerIp = centralServerIpInput.value;
        const dockerCommand = `docker run --name ${agentName} -e AGENT_NAME=${agentName} -e CENTRAL_SERVER_URL=http://${centralServerIp}:5000 --network host -d devsecops-monitoring-agent:latest`;
        dockerCommandDiv.textContent = dockerCommand;
    }

    updateDockerCommand();

    agentNameInput.addEventListener('input', updateDockerCommand);
    centralServerIpInput.addEventListener('input', updateDockerCommand);

    createButton.addEventListener('click', () => {
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
});