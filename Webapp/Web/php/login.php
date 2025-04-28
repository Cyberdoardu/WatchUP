<?php
require_once 'connection.php';
use Firebase\JWT\JWT;
use Firebase\JWT\Key;




// Carrega as variáveis de ambiente
$dotenv = Dotenv\Dotenv::createImmutable(__DIR__);
$dotenv->load();

// Define o fuso horário para evitar avisos
date_default_timezone_set('UTC');

// Verifica se o método da requisição é POST
if ($_SERVER["REQUEST_METHOD"] === "POST") {
    $username = $_POST["username"] ?? "";
    $password = $_POST["password"] ?? "";

    // Obtém a conexão com o banco de dados
    $db = MariaDBConnection::getConnection();

    try {
        // Prepara a consulta SQL para buscar o usuário pelo nome de usuário
        $stmt = $db->prepare("SELECT id, username, senha FROM usuarios WHERE username = ?");
        $stmt->bind_param("s", $username);
        $stmt->execute();

        // Obtém o resultado da consulta
        $result = $stmt->get_result();
        $usuario = $result->fetch_assoc();

        // Verifica se o usuário foi encontrado e se a senha está correta
        if (!$usuario || !password_verify($password, $usuario['senha'])) {
            // Retorna um erro de credenciais inválidas
            echo json_encode([
                "sucesso" => false,
                "mensagem" => "Credenciais inválidas!"
            ]);
            exit;
        }
        
        // Define o payload para o token JWT
        $payload = [
            "username" => $usuario['username']
        ];
        $secret = getenv('JWT_SECRET');
        $jwt = JWT::encode($payload, $secret, 'HS256');

        // Retorna o token JWT em caso de sucesso
        echo json_encode([
            "sucesso" => true,
            "token" => $jwt
        ]);
    } catch (Exception $e) {
        error_log("DATABASE ERROR: " . $e->getMessage());
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "Erro no banco de dados"
        ]);
    }
} else {
    header("HTTP/1.1 405 Method Not Allowed");
}