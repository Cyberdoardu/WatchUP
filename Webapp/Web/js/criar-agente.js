document.addEventListener('DOMContentLoaded', () => {
    const agentNameInput = document.querySelector('input[name="agent-name"]');
    const centralServerIpInput = document.querySelector('input[name="central-server-ip"]');
    const dockerCommandDiv = document.querySelector('#docker-command');
    const createButton = document.querySelector('#create-button');

    function updateDockerCommand() {
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