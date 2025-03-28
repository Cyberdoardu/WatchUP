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
    $username = $_POST["username"] ?? "";
    $nome = $_POST["nome"] ?? "";
    $email = $_POST["email"] ?? "";
    $senha = $_POST["senha"] ?? "";
    $admin = 1; // Como é o cadastro de admin, forçamos para 1

    // Verifica se os campos estão vazios
    if (empty($username) || empty($nome) || empty($email) || empty($senha)) {
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "Todos os campos são obrigatórios!"
        ]);
        exit;
    }

    // Verifica se já existe um administrador no banco de dados
    $sql = "SELECT COUNT(*) FROM usuarios WHERE admin = 1";
    $stmt = $pdo->prepare($sql);
    $stmt->execute();
    $adminExistente = $stmt->fetchColumn();

    if ($adminExistente > 0) {
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "Já existe um administrador cadastrado no sistema!"
        ]);
        exit;
    }

    // Verifica se já existe um usuário com o mesmo e-mail ou username
    $sql = "SELECT COUNT(*) FROM usuarios WHERE email = :email OR username = :username";
    $stmt = $pdo->prepare($sql);
    $stmt->execute(['email' => $email, 'username' => $username]);
    $usuarioExistente = $stmt->fetchColumn();

    if ($usuarioExistente > 0) {
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "Já existe um usuário com esse e-mail ou username!"
        ]);
    } else {
        try {
            // Insere os dados no banco de dados
            $sql = "INSERT INTO usuarios (username, nome, email, senha, admin) VALUES (:username, :nome, :email, :senha, :admin)";
            $stmt = $pdo->prepare($sql);

            // Usando hash para senha
            $senhaHash = password_hash($senha, PASSWORD_BCRYPT);

            $stmt->execute([
                'username' => $username,
                'nome' => $nome,
                'email' => $email,
                'senha' => $senhaHash,
                'admin' => $admin
            ]);

            echo json_encode([
                "sucesso" => true,
                "mensagem" => "Administrador cadastrado com sucesso!",
                "redirecionar" => "login.html"
            ]);
        } catch (PDOException $e) {
            echo json_encode([
                "sucesso" => false,
                "mensagem" => "Erro ao cadastrar usuário: " . $e->getMessage()
            ]);
        }
    }
}