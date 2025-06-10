<?php
// Inicia a sessão para poder destruí-la.
session_start();

// Remove todas as variáveis da sessão.
$_SESSION = array();

// Apagar também o cookie de sessão TO-DO
if (ini_get("session.use_cookies")) {
    $params = session_get_cookie_params();
    setcookie(session_name(), '', time() - 42000,
        $params["path"], $params["domain"],
        $params["secure"], $params["httponly"]
    );
}

// Finalmente, destrói a sessão.
session_destroy();

// Redireciona o usuário para a página de login.
header("Location: /login.html");
exit;
?>