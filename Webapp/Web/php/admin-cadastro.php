<?php
require_once 'connection.php';

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    $username = trim($_POST["username"] ?? "");
    $nome = trim($_POST["nome"] ?? "");
    $email = trim($_POST["email"] ?? "");
    $senha = $_POST["senha"] ?? "";
    $admin = 1; // 1 para true em MySQL

    // Validações (mantenha as mesmas)
    if (empty($username) || empty($nome) || empty($email) || empty($senha)) {
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "Todos os campos são obrigatórios!"
        ]);
        exit;
    }

    $db = MariaDBConnection::getConnection();

    try {
        // Verificar se já existe admin
        $stmt = $db->prepare("SELECT COUNT(*) AS total FROM usuarios WHERE admin = 1");
        $stmt->execute();
        $result = $stmt->get_result()->fetch_assoc();
        
        if ($result['total'] > 0) {
            echo json_encode([
                "sucesso" => false,
                "mensagem" => "Já existe um administrador cadastrado!"
            ]);
            exit;
        }

        // Verificar usuário existente
        $stmt = $db->prepare("SELECT COUNT(*) AS total FROM usuarios WHERE email = ? OR username = ?");
        $stmt->bind_param("ss", $email, $username);
        $stmt->execute();
        $result = $stmt->get_result()->fetch_assoc();
        
        if ($result['total'] > 0) {
            echo json_encode([
                "sucesso" => false,
                "mensagem" => "E-mail ou username já cadastrado!"
            ]);
            exit;
        }

        // Inserir novo usuário
        $senhaHash = password_hash($senha, PASSWORD_BCRYPT);
        $stmt = $db->prepare("INSERT INTO usuarios (username, nome, email, senha, admin) VALUES (?, ?, ?, ?, ?)");
        $stmt->bind_param("ssssi", $username, $nome, $email, $senhaHash, $admin);
        
        if ($stmt->execute()) {
            echo json_encode([
                "sucesso" => true,
                "mensagem" => "Administrador cadastrado com sucesso!",
                "redirecionar" => "config-sistema.html"
            ]);
        } else {
            throw new Exception("Erro na execução da query");
        }

    } catch (Exception $e) {
        error_log("DATABASE ERROR: " . $e->getMessage());
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "Erro no banco de dados: " . $e->getMessage()
        ]);
    }
}
?>