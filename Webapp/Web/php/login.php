<?php
// REMOVIDO: require_once __DIR__ . '/vendor/autoload.php';
require_once 'connection.php';

use Firebase\JWT\JWT;
use Firebase\JWT\Key;

// As dependências do JWT serão carregadas pelo api-gateway que é o ponto de entrada
// ou por um autoloader global, se configurado.
// Para este script, assumimos que as classes JWT estão disponíveis.

session_start();

// CORREÇÃO: Ler a variável de ambiente diretamente.
$jwt_secret = getenv('JWT_SECRET');
if (!$jwt_secret) {
    http_response_code(500);
    error_log("Segredo JWT não configurado no ambiente do servidor.");
    echo json_encode(["sucesso" => false, "mensagem" => "Erro de configuração interna do servidor."]);
    exit;
}

header('Content-Type: application/json');

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    // Para clareza, vamos chamar a variável de $email.
    $email = $_POST["email"] ?? ""; // <<< MANTIVE O USO DE 'email' DO SEU CÓDIGO
    $password = $_POST["senha"] ?? "";

    if (empty($email) || empty($password)) {
        http_response_code(400);
        echo json_encode(["sucesso" => false, "mensagem" => "E-mail e senha são obrigatórios."]);
        exit;
    }

    $db = MariaDBConnection::getConnection();
    try {
        $stmt = $db->prepare("SELECT id, username, senha, role, admin FROM usuarios WHERE email = ?"); // <<< CORREÇÃO AQUI
        $stmt->bind_param("s", $email); 
        $stmt->execute();
        $result = $stmt->get_result();
        $usuario = $result->fetch_assoc();

        // O usuário será encontrado pelo e-mail.
        if ($usuario && password_verify($password, $usuario['senha'])) {
            session_regenerate_id(true);

            $_SESSION['user_id'] = $usuario['id'];
            $_SESSION['username'] = $usuario['username'];
            $_SESSION['user_role'] = $usuario['admin'] ? 'admin' : 'user';

            $issuedAt = time();
            $expirationTime = $issuedAt + 3600; // JWT válido por 1 hora
            $payload = [
                'iat'  => $issuedAt,
                'exp'  => $expirationTime,
                'data' => [
                    'userId'   => $usuario['id'],
                    'username' => $usuario['username'],
                    'role'     => $_SESSION['user_role']
                ]
            ];
            
            require_once __DIR__ . '/vendor/firebase/jwt/src/JWT.php';
            require_once __DIR__ . '/vendor/firebase/jwt/src/Key.php';

            // Carrega o segredo do ambiente
            $jwt_secret = getenv('JWT_SECRET');

            $jwt = JWT::encode($payload, $jwt_secret, 'HS256');

            echo json_encode([
                "sucesso" => true,
                "mensagem" => "Login bem-sucedido!",
                "token" => $jwt,
                "redirecionar" => "/index.html"
            ]);
        } else {
            // Se a verificação falhar, retorna "Credenciais inválidas".
            http_response_code(401);
            echo json_encode(["sucesso" => false, "mensagem" => "Credenciais inválidas!"]);
        }
    } catch (Exception $e) {
        http_response_code(500);
        error_log("Erro de Login: " . $e->getMessage());
        echo json_encode(["sucesso" => false, "mensagem" => "Erro interno do servidor."]);
    }
}
?>