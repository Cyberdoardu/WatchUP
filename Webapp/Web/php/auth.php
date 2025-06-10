<?php
session_start();

require_once __DIR__ . '/vendor/autoload.php';
require_once __DIR__ . '/connection.php';

use Firebase\JWT\JWT;
use Firebase\JWT\Key;

// Carrega o segredo JWT da variável de ambiente
$jwt_secret = getenv('JWT_SECRET');
if (!$jwt_secret) {
    die("Erro crítico: Segredo JWT não configurado no servidor.");
}

function check_admin_role() {
    if (!isset($_SESSION['user_role']) || $_SESSION['user_role'] !== 'admin') {
        header('Location: forbidden.html');
        exit;
    }
}

function check_authentication($redirect_on_fail = true) {
    if (!isset($_SESSION['user_id'])) {
        if ($redirect_on_fail) {
            header('Location: login.html');
            exit;
        }
        return false;
    }
    return true;
}

function get_jwt_from_header() {
    $authHeader = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
    if (preg_match('/Bearer\s(\S+)/', $authHeader, $matches)) {
        return $matches[1];
    }
    return null;
}

function validate_jwt_and_get_payload($jwt) {
    global $jwt_secret;
    if (!$jwt) return null;
    try {
        $decoded = JWT::decode($jwt, new Key($jwt_secret, 'HS256'));
        return (array) $decoded->data;
    } catch (Exception $e) {
        return null;
    }
}