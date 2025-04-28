php
<?php
require_once __DIR__ . '/vendor/firebase/jwt/src/JWT.php';

use Firebase\JWT\JWT;
use Firebase\JWT\Key;

// Load environment variables
$dotenv = Dotenv\Dotenv::createImmutable(__DIR__);
$dotenv->safeLoad();

// Function to authenticate the request using JWT
function authenticateRequest($headers) {
    if (!isset($headers['Authorization'])) {
        http_response_code(401);
        echo json_encode(['error' => 'Unauthorized: Token missing']);
        exit;
    }
    
    $authHeader = $headers['Authorization'];
    $token = str_replace('Bearer ', '', $authHeader);
    $secretKey = getenv('JWT_SECRET');

    try {
        $decoded = JWT::decode($token, new Key($secretKey, 'HS256'));        
        return $decoded;
    } catch (\Firebase\JWT\ExpiredException $e) {
        http_response_code(401);
        echo json_encode(['error' => 'Unauthorized: Token expired']);
    }catch (Exception $e) {
        http_response_code(401);
        echo json_encode(['error' => 'Unauthorized: Invalid token']);
        exit;
    }
}

// Function to forward request to API
function forwardRequest($url, $method, $headers, $data = null) {
    $ch = curl_init($url);
    
    curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);

    if ($data) {
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
    }
    
    if(count($_GET)>0){
        $query = http_build_query($_GET);
        $url .= '?'.$query;
        curl_setopt($ch, CURLOPT_URL, $url);

    }

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    http_response_code($httpCode);    
    echo $response;
}


// Get requested URI
$uri = $_SERVER['REQUEST_URI'];
$method = $_SERVER['REQUEST_METHOD'];
$headers = getallheaders();

// Check if authentication is required
$publicRoutes = [
    '/login'
];

$privateRoutes = [
    '/metrics',
    '/monitors',
    '/targets'
];

$authRequired = in_array($uri, $privateRoutes);

// Authenticate if required
if ($authRequired) {
    authenticateRequest($headers);
}

$requestData = null;
if (in_array($method, ['POST', 'PUT'])) {
    $requestData = json_decode(file_get_contents('php://input'), true);
}

$centralApiUrl = 'http://central:5000';

if(in_array($uri, $privateRoutes)){
    $forwardHeaders = array_map(function($key, $value) {
        return "$key: $value";
        }, array_keys($headers), $headers);
    $forwardUrl = $centralApiUrl . $uri;    


    forwardRequest($forwardUrl, $method, $forwardHeaders, $requestData);


} else if (in_array($uri, $publicRoutes)){
    require_once 'login.php';
} else {
    $response = ['error' => 'Not Found'];
    http_response_code(404);    
    echo json_encode($response);
}
?>