document.getElementById('adminCadastroForm').addEventListener('submit', function(event) {
  event.preventDefault();
  fetch('php/admin-cadastro.php', {
    method: 'POST',
    body: new FormData(event.target)
  })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            alert(data.mensagem);
            if (data.redirecionar) {window.location.href = data.redirecionar;
        }
        } else {
            alert(data.mensagem);
        }})
    .catch(error => {
      console.error('Error:', error);
      alert('Ocorreu um erro durante o cadastro');
    });
});