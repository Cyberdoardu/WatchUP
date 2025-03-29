<?php
require_once 'connection.php';

$session = ScyllaDB::getSession();

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    $email = $_POST["email"] ?? "";
    $senha = $_POST["senha"] ?? "";

    // Validações (mantenha as mesmas)

    try {
        $query = "SELECT id, username, nome, email, senha, admin FROM usuarios WHERE email = ? LIMIT 1";
        $statement = $session->prepare($query);
        $result = $session->execute($statement, ['arguments' => [$email]]);
        
        if ($result->count() === 0) {
            echo json_encode([
                "sucesso" => false,
                "mensagem" => "Credenciais inválidas!"
            ]);
            exit;
        }

        $usuario = $result->first();
        
        if (password_verify($senha, $usuario['senha'])) {
            session_start();
            $_SESSION['usuario_id'] = $usuario['id']->uuid();
            $_SESSION['usuario_nome'] = $usuario['nome'];
            $_SESSION['usuario_email'] = $usuario['email'];
            $_SESSION['usuario_admin'] = $usuario['admin'];

            echo json_encode([
                "sucesso" => true,
                "mensagem" => "Login realizado com sucesso!",
                "redirecionar" => "menu.html"
            ]);
        } else {
            echo json_encode([
                "sucesso" => false,
                "mensagem" => "Credenciais inválidas!"
            ]);
        }

    } catch (Cassandra\Exception $e) {
        error_log("SCYLLA ERROR: " . $e->getMessage());
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "Erro no banco de dados: " . $e->getMessage()
        ]);
    }
}
?>