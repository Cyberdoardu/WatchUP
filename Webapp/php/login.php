<?php
// Configurações do banco de dados
$host = '34.55.95.29';
$dbname = 'users';
$username = 'postgres';
$password = 's3nh@B3@!';

// Conexão com o banco de dados
try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8", $username, $password);
    // Configura o PDO para lançar exceções em caso de erros
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (PDOException $e) {
    echo json_encode([
        "sucesso" => false,
        "mensagem" => "Erro ao conectar com o banco de dados: " . $e->getMessage()
    ]);
    exit;
}

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    $email = $_POST["email"] ?? "";
    $senha = $_POST["senha"] ?? "";

    // Verifica se o email ou a senha não estão vazios
    if (empty($email) || empty($senha)) {
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "E-mail e senha são obrigatórios!"
        ]);
        exit;
    }

    try {
        // Prepara a consulta SQL
        $stmt = $pdo->prepare("SELECT * FROM usuarios WHERE email = :email");
        $stmt->bindParam(':email', $email);
        $stmt->execute();
        
        // Obtém o usuário
        $usuario = $stmt->fetch(PDO::FETCH_ASSOC);
        
        // Verifica se encontrou o usuário e se a senha está correta
        if ($usuario && password_verify($senha, $usuario['senha'])) {
            echo json_encode([
                "sucesso" => true,
                "mensagem" => "Login realizado com sucesso!",
                "redirecionar" => "admin.html"
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
            "mensagem" => "Erro ao verificar credenciais: " . $e->getMessage()
        ]);
    }
}
?>