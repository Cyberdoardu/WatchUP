document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('monitorForm');
    const menuButton = document.getElementById('menuButton');

    form.addEventListener('submit', function(event) {
        event.preventDefault();

        const name = document.getElementById('name').value;
        const type = document.getElementById('type').value;
        const location = document.getElementById('location').value;

        const data = {
            name: name,
            type: type,
            location: location
        };

        fetch('monitor-cadastro.php', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Monitor created successfully!');
            } else {
                alert('Error creating monitor: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while processing the request.');
        });
    });

    menuButton.addEventListener('click', function() {
        window.location.href = 'index.html';
    });
});