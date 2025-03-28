<?php

// Configuração do banco de dados
$host = 'localhost';
$dbname = 'meu_banco';
$username = 'lemb';
$password = 'lemb';

// Conectar ao banco de dados
try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->exec("SET NAMES 'utf8mb4'"); // Definir charset para utf8mb4
} catch (PDOException $e) {
    echo json_encode([
        "sucesso" => false,
        "mensagem" => "Erro ao conectar ao banco de dados: " . $e->getMessage()
    ]);
    exit;
}

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    // Recebendo dados do formulário
    $email = $_POST["email"] ?? "";
    $senha = $_POST["senha"] ?? ""; // Note que no HTML o name é "senha" mas no PHP está como "senha"

    // Verifica se os campos estão vazios
    if (empty($email) || empty($senha)) {
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "E-mail e senha são obrigatórios!"
        ]);
        exit;
    }

    try {
        // Busca o usuário no banco de dados pelo e-mail
        $sql = "SELECT id, username, nome, email, senha, admin FROM usuarios WHERE email = :email";
        $stmt = $pdo->prepare($sql);
        $stmt->execute(['email' => $email]);
        $usuario = $stmt->fetch(PDO::FETCH_ASSOC);

        // Verifica se o usuário existe e a senha está correta
        if ($usuario && password_verify($senha, $usuario['senha'])) {
            // Inicia a sessão (se necessário)
            session_start();
            $_SESSION['usuario_id'] = $usuario['id'];
            $_SESSION['usuario_nome'] = $usuario['nome'];
            $_SESSION['usuario_email'] = $usuario['email'];
            $_SESSION['usuario_admin'] = $usuario['admin'];

            // Determina para onde redirecionar baseado no tipo de usuário
            $redirecionar = $usuario['admin'] ? 'admin-dashboard.html' : 'user-dashboard.html';

            echo json_encode([
                "sucesso" => true,
                "mensagem" => "Login realizado com sucesso!",
                "redirecionar" => $redirecionar
            ]);
        } else {
            echo json_encode([
                "sucesso" => false,
                "mensagem" => "E-mail ou senha incorretos!"
            ]);
        }
    } catch (PDOException $e) {
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "Erro ao realizar login: " . $e->getMessage()
        ]);
    }
}