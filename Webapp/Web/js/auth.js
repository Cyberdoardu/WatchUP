// Função auto-executável assíncrona para verificar a autenticação na carga da página
(async function checkAuthentication() {
    const token = localStorage.getItem('jwt_token');

    // Se não há token, redireciona para o login (a menos que já esteja lá ou no cadastro de admin)
    if (!token) {
        if (!window.location.pathname.endsWith('login.html') && !window.location.pathname.endsWith('admin-cadastro.html')) {
            window.location.href = '/login.html';
        }
        return;
    }

    // Tenta validar o token com o backend
    try {
        // CORREÇÃO CRÍTICA: O caminho para o endpoint de verificação deve ser absoluto a partir da raiz.
        const response = await fetch('/php/auth-check.php', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error(`Falha na validação do token com status: ${response.status}`);
        }

        const result = await response.json();

        // Se o backend confirmar o sucesso, preenche a barra de navegação
        if (result.status === 'success' && result.user) {
            populateNavbar(result.user);
        } else {
            throw new Error('Resposta de verificação de autenticação inválida');
        }

    } catch (error) {
        // Se a validação falhar por qualquer motivo (token expirado, 404, etc.), limpa e redireciona
        console.error('Falha na verificação de autenticação:', error);
        localStorage.removeItem('jwt_token');
        if (!window.location.pathname.endsWith('login.html')) {
            window.location.href = '/login.html';
        }
    }
})();

// Função para popular a barra de navegação com os dados do usuário
function populateNavbar(userData) {
    const navbar = document.querySelector('.flex.flex-wrap.gap-4.border-b');
    if (navbar) {
        const placeholder = navbar.querySelector('#nav-user-placeholder');
        if(placeholder) placeholder.remove();

        const usernameDisplay = document.createElement('span');
        usernameDisplay.className = 'font-medium text-gray-700 ml-auto self-center';
        usernameDisplay.textContent = `Olá, ${userData.username}`;

        const logoutButton = document.createElement('a');
        logoutButton.href = '/php/logout.php'; // Link direto
        logoutButton.id = 'logoutBtn';
        logoutButton.className = 'font-medium text-red-500 hover:text-red-700 self-center';
        logoutButton.textContent = 'Logout';
        
        navbar.appendChild(usernameDisplay);
        navbar.appendChild(logoutButton);
    }
}

// Função auxiliar para adicionar cabeçalhos de autenticação nas chamadas de API
function getAuthHeaders() {
    const token = localStorage.getItem('jwt_token');
    const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}