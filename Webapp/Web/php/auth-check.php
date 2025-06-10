<?php
/**
 * Endpoint de verificação de autenticação.
 * Valida o token JWT e retorna os dados do usuário se for válido.
 * Utilizado pelo auth.js para verificar a sessão do usuário a cada carregamento de página.
 */

// Define que a saída será JSON para todas as respostas.
header('Content-Type: application/json');

// Reutiliza a lógica de autenticação já definida no api-gateway.
// Isso evita duplicação de código.
require_once __DIR__ . '/api-gateway.php';

// A função authenticateRequest() faz todo o trabalho pesado:
// 1. Encontra o cabeçalho 'Authorization'.
// 2. Valida o JWT (assinatura, expiração).
// 3. Em caso de qualquer falha, ela já encerra o script com um erro 401 e uma mensagem JSON.
$user_payload = authenticateRequest();

// Se o script chegou até esta linha, significa que a autenticação foi bem-sucedida.
// Agora, retornamos um status de sucesso com os dados do usuário decodificados do token.
echo json_encode([
    'status' => 'success',
    'user' => $user_payload
]);

?>