<?php
require_once 'api-gateway.php'; 
require_once 'vendor/firebase/jwt/src/JWT.php';
require_once 'vendor/firebase/jwt/src/Key.php';

use Firebase\JWT\JWT;
use Firebase\JWT\Key;

// Allow from any origin
if (isset($_SERVER['HTTP_ORIGIN'])) {
    header("Access-Control-Allow-Origin: {$_SERVER['HTTP_ORIGIN']}");
    header('Access-Control-Allow-Credentials: true');
    header('Access-Control-Max-Age: 86400');    // cache for 1 day
}

// Access-Control headers are received during OPTIONS requests
if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') {
    if (isset($_SERVER['HTTP_ACCESS_CONTROL_REQUEST_METHOD'])) {
        header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
    }
    if (isset($_SERVER['HTTP_ACCESS_CONTROL_REQUEST_HEADERS'])) {
        header("Access-Control-Allow-Headers: {$_SERVER['HTTP_ACCESS_CONTROL_REQUEST_HEADERS']}");
    }
    exit(0);
}

header('Content-Type: application/json');

$jwt_secret_key = 'e7e115e095ff092fdb391e9c88e10407b46288584904947f2a91f598605ac9e5'; // Hard coded for debugging, not a "real" JWT

// Get the JWT from the Authorization header
$authHeader = null;
if (isset($_SERVER['HTTP_AUTHORIZATION'])) {
    $authHeader = $_SERVER['HTTP_AUTHORIZATION'];
} elseif (isset($_SERVER['REDIRECT_HTTP_AUTHORIZATION'])) { 
    $authHeader = $_SERVER['REDIRECT_HTTP_AUTHORIZATION'];
} elseif (function_exists('apache_request_headers')) {
    $requestHeaders = apache_request_headers();
    $requestHeaders = array_combine(array_map('ucwords', array_keys($requestHeaders)), array_values($requestHeaders));
    if (isset($requestHeaders['Authorization'])) {
        $authHeader = $requestHeaders['Authorization'];
    }
}

if (!$authHeader) {
    http_response_code(401);
    echo json_encode(['status' => 'error', 'message' => 'Authorization header not found']);
    exit;
}

list($jwt) = sscanf($authHeader, 'Bearer %s');

if (!$jwt) {
    http_response_code(401);
    echo json_encode(['status' => 'error', 'message' => 'JWT not found in Authorization header']);
    exit;
}

try {
    $decoded = JWT::decode($jwt, new Key($jwt_secret_key, 'HS256'));
} catch (Exception $e) {
    http_response_code(401);
    echo json_encode(['status' => 'error', 'message' => 'Invalid token: ' . $e->getMessage()]);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = json_decode(file_get_contents('php://input'), true);

    if (json_last_error() !== JSON_ERROR_NONE) {
        http_response_code(400);
        echo json_encode(['status' => 'error', 'message' => 'Invalid JSON input']);
        exit;
    }

    $required_fields = ['name', 'request_interval', 'retention_time', 'agent_id', 'type', 'config'];
    foreach ($required_fields as $field) {
        if (empty($input[$field]) && $field !== 'config' && !is_numeric($input[$field])) { 
            http_response_code(400);
            echo json_encode(['status' => 'error', 'message' => "Missing required field: {$field}"]);
            exit;
        }
    }
    
    $api_gateway_internal_url = 'api-gateway.php?endpoint=monitors'; 
    $gateway_response = forward_request_to_gateway($api_gateway_internal_url, 'POST', $input, $jwt);

    $response_data = json_decode($gateway_response['body'], true);
    http_response_code($gateway_response['http_code']);
    echo json_encode($response_data);

} else {
    http_response_code(405); 
    echo json_encode(['status' => 'error', 'message' => 'Invalid request method.']);
}

?>
