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
        // CORRIGIDO: A chamada agora é um endpoint do gateway
        const response = await fetch('/php/api-gateway.php?endpoint=auth-check', {
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
        // Se a validação falhar por qualquer motivo (token expirado, 401, etc.), limpa e redireciona
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
        // Adicionado um placeholder no HTML para ser substituído, ou cria os elementos se não existir
        const userContainer = navbar.querySelector('#nav-user-container') || document.createElement('div');
        userContainer.id = 'nav-user-container';
        userContainer.className = 'ml-auto flex items-center gap-4';
        
        userContainer.innerHTML = `
            <span class="font-medium text-gray-700 self-center">Olá, ${userData.username}</span>
            <a href="/php/logout.php" id="logoutBtn" class="font-medium text-red-500 hover:text-red-700 self-center">Logout</a>
        `;
        
        // Garante que o container é filho da navbar
        if (!navbar.contains(userContainer)) {
             navbar.appendChild(userContainer);
        }
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