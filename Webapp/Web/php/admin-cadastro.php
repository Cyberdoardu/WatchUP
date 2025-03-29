<?php
require_once 'connection.php';

$session = ScyllaDB::getSession();

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    $username = trim($_POST["username"] ?? "");
    $nome = trim($_POST["nome"] ?? "");
    $email = trim($_POST["email"] ?? "");
    $senha = $_POST["senha"] ?? "";
    $admin = true;

    // Validações (mantenha as mesmas)

    try {
        // Verificar se já existe admin
        $query = "SELECT COUNT(*) FROM usuarios WHERE admin = ? ALLOW FILTERING";
        $statement = $session->prepare($query);
        $result = $session->execute($statement, ['arguments' => [true]]);
        
        if ($result->first()['count'] > 0) {
            echo json_encode([
                "sucesso" => false,
                "mensagem" => "Já existe um administrador cadastrado!"
            ]);
            exit;
        }

        // Verificar usuário existente
        $query = "SELECT COUNT(*) FROM usuarios WHERE email = ? OR username = ? ALLOW FILTERING";
        $statement = $session->prepare($query);
        $result = $session->execute($statement, ['arguments' => [$email, $username]]);
        
        if ($result->first()['count'] > 0) {
            echo json_encode([
                "sucesso" => false,
                "mensagem" => "E-mail ou username já cadastrado!"
            ]);
            exit;
        }

        // Inserir novo usuário
        $id = new Cassandra\Uuid();
        $senhaHash = password_hash($senha, PASSWORD_BCRYPT);
        
        $query = "INSERT INTO usuarios (id, username, nome, email, senha, admin) VALUES (?, ?, ?, ?, ?, ?)";
        $statement = $session->prepare($query);
        
        $session->execute($statement, ['arguments' => [
            $id,
            $username,
            $nome,
            $email,
            $senhaHash,
            $admin
        ]]);

        echo json_encode([
            "sucesso" => true,
            "mensagem" => "Administrador cadastrado com sucesso!",
            "redirecionar" => "config-sistema.html"
        ]);

    } catch (Cassandra\Exception $e) {
        error_log("SCYLLA ERROR: " . $e->getMessage());
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "Erro no banco de dados: " . $e->getMessage()
        ]);
    }
}
?>