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

/**
 * Verifica se já existe um administrador cadastrado no banco de dados
 * @param PDO $pdo Objeto de conexão PDO
 * @return bool Retorna true se já existir um admin, false caso contrário
 */
function existeAdmin($pdo) {
    try {
        $sql = "SELECT COUNT(*) FROM usuarios WHERE admin = 1";
        $stmt = $pdo->prepare($sql);
        $stmt->execute();
        return $stmt->fetchColumn() > 0;
    } catch (PDOException $e) {
        error_log("Erro ao verificar admin existente: " . $e->getMessage());
        return true; // Por segurança, assume que existe admin se houver erro
    }
}

/**
 * Verifica se já existe um usuário com o mesmo email ou username
 * @param PDO $pdo Objeto de conexão PDO
 * @param string $email Email a verificar
 * @param string $username Username a verificar
 * @return bool Retorna true se já existir, false caso contrário
 */
function usuarioExistente($pdo, $email, $username) {
    try {
        $sql = "SELECT COUNT(*) FROM usuarios WHERE email = :email OR username = :username";
        $stmt = $pdo->prepare($sql);
        $stmt->execute(['email' => $email, 'username' => $username]);
        return $stmt->fetchColumn() > 0;
    } catch (PDOException $e) {
        error_log("Erro ao verificar usuário existente: " . $e->getMessage());
        return true; // Por segurança, assume que existe usuário se houver erro
    }
}

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    // Ativar exibição de erros para debug
    ini_set('display_errors', 1);
    ini_set('display_startup_errors', 1);
    error_reporting(E_ALL);

    // Recebendo dados do formulário
    $username = trim($_POST["username"] ?? "");
    $nome = trim($_POST["nome"] ?? "");
    $email = trim($_POST["email"] ?? "");
    $senha = $_POST["senha"] ?? "";
    $admin = 1; // Como é o cadastro de admin, forçamos para 1

    // Validação básica dos campos
    if (empty($username) || empty($nome) || empty($email) || empty($senha)) {
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "Todos os campos são obrigatórios!"
        ]);
        exit;
    }

    // Validação de email
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "Formato de e-mail inválido!"
        ]);
        exit;
    }

    // Verifica se já existe um administrador
    if (existeAdmin($pdo)) {
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "Já existe um administrador cadastrado no sistema!"
        ]);
        exit;
    }

    // Verifica se já existe usuário com mesmo email ou username
    if (usuarioExistente($pdo, $email, $username)) {
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "Já existe um usuário com esse e-mail ou username!"
        ]);
        exit;
    }

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
            "redirecionar" => "config-sistema.html"
        ]);
    } catch (PDOException $e) {
        error_log("Erro ao cadastrar admin: " . $e->getMessage());
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "Erro ao cadastrar administrador: " . $e->getMessage()
        ]);
    }
}