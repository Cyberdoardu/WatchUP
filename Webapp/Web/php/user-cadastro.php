<?php
require_once 'connection.php';

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    $username = trim($_POST["username"] ?? "");
    $nome = trim($_POST["nome"] ?? "");
    $email = trim($_POST["email"] ?? "");
    $senha = $_POST["senha"] ?? "";
    $admin = 0; // 0 para false em MySQL (usuário comum)

    // Validações básicas
    if (empty($username) || empty($nome) || empty($email) || empty($senha)) {
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "Todos os campos são obrigatórios!"
        ]);
        exit;
    }

    // Validação de e-mail
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "Formato de e-mail inválido!"
        ]);
        exit;
    }

    $db = MariaDBConnection::getConnection();

    try {
        // Verificar usuário ou e-mail existente
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
                "mensagem" => "Usuário cadastrado com sucesso!",
                "redirecionar" => "config-sistema.html" // ou outra página de destino
            ]);
        } else {
            throw new Exception("Erro na execução da query");
        }

    } catch (Exception $e) {
        error_log("DATABASE ERROR: " . $e->getMessage());
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "Erro no cadastro do usuário. Por favor, tente novamente."
        ]);
    }
}
?>