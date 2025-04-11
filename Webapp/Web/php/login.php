<?php
require_once 'connection.php';

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    $email = $_POST["email"] ?? "";
    $senha = $_POST["senha"] ?? "";

    $db = MariaDBConnection::getConnection();

    try {
        $stmt = $db->prepare("SELECT id, username, nome, email, senha, admin FROM usuarios WHERE email = ?");
        $stmt->bind_param("s", $email);
        $stmt->execute();
        
        $result = $stmt->get_result();
        $usuario = $result->fetch_assoc();

        if (!$usuario || !password_verify($senha, $usuario['senha'])) {
            echo json_encode([
                "sucesso" => false,
                "mensagem" => "Credenciais inválidas!"
            ]);
            exit;
        }
/*
        session_start();
        $_SESSION['usuario_id'] = $usuario['id'];
        $_SESSION['usuario_nome'] = $usuario['nome'];
        $_SESSION['usuario_email'] = $usuario['email'];
        $_SESSION['usuario_admin'] = $usuario['admin'];
*/
        echo json_encode([
            "sucesso" => true,
            "mensagem" => "Login realizado com sucesso!",
            "redirecionar" => "menu.html"
        ]);

    } catch (Exception $e) {
        error_log("DATABASE ERROR: " . $e->getMessage());
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "Erro no banco de dados"
        ]);
    }
}
?>