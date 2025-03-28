<?php
if ($_SERVER["REQUEST_METHOD"] === "POST") {
    $email = $_POST["email"] ?? "";
    $senha = $_POST["senha"] ?? "";

    // Verifica se os campos estão vazios
    if (empty($email) || empty($senha)) {
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "E-mail e senha são obrigatórios!"
        ]);
        exit;
    }

    // Verifica se já existe um admin cadastrado (hardcoded)
    $adminExistente = file_exists('admin.txt'); // Verifica se o arquivo de admin existe

    if ($adminExistente) {
        echo json_encode([
            "sucesso" => false,
            "mensagem" => "Já existe um administrador cadastrado no sistema!"
        ]);
    } else {
        // Simula o cadastro do admin criando um arquivo com os dados
        $dadosAdmin = [
            'email' => $email,
            'senha' => $senha
        ];
        
        file_put_contents('admin.txt', json_encode($dadosAdmin));
        
        echo json_encode([
            "sucesso" => true,
            "mensagem" => "Administrador cadastrado com sucesso!",
            "redirecionar" => "login.html"
        ]);
    }
}
?>