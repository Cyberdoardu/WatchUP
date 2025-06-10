document.getElementById('loginForm').addEventListener('submit', (event) => {
    event.preventDefault();

    fetch('php/login.php', {
        method: 'POST',
        body: new FormData(event.target)
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso && data.token) {
            localStorage.setItem('jwt_token', data.token);
            if (data.redirecionar) {
                window.location.href = data.redirecionar;
            }
        } else {
            alert(data.mensagem || 'Ocorreu um erro durante o login.');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        alert('Falha na comunicação com o servidor.');
    });
});