<?php
// A ORDEM DE INCLUSÃO É IMPORTANTE AQUI!

// Interfaces e classes base primeiro
require_once __DIR__ . '/vendor/firebase/jwt/src/JWTExceptionWithPayloadInterface.php'; 

// Classes de Exceção que implementam a interface
require_once __DIR__ . '/vendor/firebase/jwt/src/ExpiredException.php';
require_once __DIR__ . '/vendor/firebase/jwt/src/BeforeValidException.php';
require_once __DIR__ . '/vendor/firebase/jwt/src/SignatureInvalidException.php';

// Classes principais da biblioteca
require_once __DIR__ . '/vendor/firebase/jwt/src/JWK.php'; 
require_once __DIR__ . '/vendor/firebase/jwt/src/Key.php';
require_once __DIR__ . '/vendor/firebase/jwt/src/JWT.php';
require_once __DIR__ . '/vendor/firebase/jwt/src/CachedKeySet.php';


use Firebase\JWT\JWT;
use Firebase\JWT\Key;

// Função para autenticar a requisição usando JWT
function authenticateRequest($headers) {
    $authHeaderKey = isset($headers['Authorization']) ? 'Authorization' : (isset($headers['authorization']) ? 'authorization' : null);

    if (!$authHeaderKey) {
        http_response_code(401);
        echo json_encode(['status' => 'error', 'message' => 'Não autorizado: Cabeçalho de autorização ausente']);
        exit;
    }
    
    $authHeader = $headers[$authHeaderKey];
    $token = str_replace('Bearer ', '', $authHeader);
    
    $secretKey = getenv('JWT_SECRET');

    if (!$secretKey) {
        http_response_code(500);
        echo json_encode(['status' => 'error', 'message' => 'Erro Interno do Servidor: Segredo JWT não configurado como variável de ambiente.']);
        exit;
    }

    try {
        $decoded = JWT::decode($token, new Key($secretKey, 'HS256'));        
        return $decoded;
    } catch (\Firebase\JWT\ExpiredException $e) { 
        http_response_code(401);
        echo json_encode(['status' => 'error', 'message' => 'Não autorizado: Token expirado']);
        exit;
    } catch (\Firebase\JWT\SignatureInvalidException $e) { 
        http_response_code(401);
        echo json_encode(['status' => 'error', 'message' => 'Não autorizado: Assinatura do token inválida']);
        exit;
    } catch (\Firebase\JWT\BeforeValidException $e) { 
        http_response_code(401);
        echo json_encode(['status' => 'error', 'message' => 'Não autorizado: Token ainda não é válido']);
        exit;
    }
     catch (Exception $e) { 
        http_response_code(401);
        echo json_encode(['status' => 'error', 'message' => 'Não autorizado: Token inválido ou erro na decodificação - ' . $e->getMessage()]);
        exit;
    }
}

// Função para encaminhar a requisição para a API
function forwardRequest($url, $method, $headersToForwardInput, $data = null) {
    $ch = curl_init();
    $curlUrl = $url;

    if (!empty($_GET)) {
        $originalGetParams = $_GET;
        unset($originalGetParams['endpoint']); 
        if (!empty($originalGetParams)){
            $queryString = http_build_query($originalGetParams);
            $curlUrl .= (strpos($curlUrl, '?') === false ? '?' : '&') . $queryString;
        }
    }
    
    curl_setopt($ch, CURLOPT_URL, $curlUrl);
    curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 30);
    
    $formattedHeaders = [];
    if (is_array($headersToForwardInput)) {
        foreach($headersToForwardInput as $key => $value) {
            if (is_string($key)) { 
                 if (strtolower($key) === 'host' || strtolower($key) === 'content-length') continue;
                 $formattedHeaders[] = "$key: $value";
            } elseif (is_string($value) && strpos($value, ':') !== false) { 
                 if (stripos($value, 'Host:') === 0 || stripos($value, 'Content-Length:') === 0) continue;
                 $formattedHeaders[] = $value;
            }
        }
    }

    if ($data !== null) {
        $jsonData = json_encode($data);
        $contentTypeSet = false;
        foreach($formattedHeaders as $hdr) {
            if (stripos($hdr, 'Content-Type:') === 0) {
                $contentTypeSet = true; break;
            }
        }
        if (!$contentTypeSet) {
             $formattedHeaders[] = 'Content-Type: application/json';
        }
        $formattedHeaders[] = 'Content-Length: ' . strlen($jsonData);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $jsonData);
    } elseif (($method === 'POST' || $method === 'PUT') && empty($data)) {
        $hasContentType = false;
        foreach($formattedHeaders as $hdr) {
            if (stripos($hdr, 'Content-Type:') === 0) {
                $hasContentType = true; break;
            }
        }
        if(!$hasContentType) $formattedHeaders[] = 'Content-Type: application/json';
        $formattedHeaders[] = 'Content-Length: 0';
    }

    curl_setopt($ch, CURLOPT_HTTPHEADER, $formattedHeaders);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $curlError = curl_error($ch);
    curl_close($ch);

    if ($curlError) {
        http_response_code(500);
        echo json_encode(['status' => 'error', 'message' => 'Falha ao encaminhar a requisição para o serviço Central', 'details' => $curlError, 'target_url' => $curlUrl]);
        exit;
    }

    http_response_code($httpCode);    
    echo $response;
}

$effectivePath = '';
if (isset($_GET['endpoint'])) {
    $effectivePath = '/' . trim($_GET['endpoint'], '/');
} else {
    $uriParts = explode('?', $_SERVER['REQUEST_URI']);
    $baseUri = $uriParts[0];
    $scriptDir = dirname($_SERVER['SCRIPT_NAME']);
    if ($scriptDir !== '/' && strpos($baseUri, $scriptDir) === 0) {
        $effectivePath = substr($baseUri, strlen($scriptDir));
    } else {
        $effectivePath = $baseUri;
    }
    if (empty($effectivePath)) $effectivePath = '/';
}

$method = $_SERVER['REQUEST_METHOD'];
$headers = getallheaders();

$userLoginRoutes = [
    '/login'
];

$jwtProtectedUserRoutes = [
    '/monitors',    
    '/agents',      
    '/create-agent' 
];

$allCentralForwardRoutes = [
    '/register',
    '/heartbeat',
    '/targets',
    '/metrics',
    '/monitors',
    '/agents',
    '/create-agent',
    '/health'
];
$allCentralForwardRoutes = array_unique($allCentralForwardRoutes);

// --- Verificação de Autenticação JWT MODIFICADA ---
$authRequired = false;
if (in_array($effectivePath, $jwtProtectedUserRoutes)) {
    // Se a rota está na lista de protegidas por JWT
    if ($effectivePath === '/agents' || $effectivePath === '/monitors') { // ADICIONADO /monitors AQUI
        // Especificamente para /agents e /monitors, não requer autenticação POR AGORA
        $authRequired = false;
        // error_log("Autenticação JWT pulada para {$effectivePath} em ambiente de teste."); 
    } else {
        $authRequired = true;
    }
} else {
    // Lógica original para outras rotas como /metrics GET
    if ($effectivePath === '/metrics' && $method === 'GET') {
        $authRequired = true;
    }
}
// FIM DA MODIFICAÇÃO

if ($authRequired) {
    authenticateRequest($headers);
}

$requestData = null;
if (in_array($method, ['POST', 'PUT', 'PATCH'])) {
    $input = file_get_contents('php://input');
    if ($input) {
        $contentTypeHeader = '';
        foreach($headers as $key => $value) {
            if (strtolower($key) === 'content-type') {
                $contentTypeHeader = strtolower($value);
                break;
            }
        }
        if (strpos($contentTypeHeader, 'application/json') !== false) {
            $decodedInput = json_decode($input, true);
            if (json_last_error() === JSON_ERROR_NONE) {
                $requestData = $decodedInput;
            } else {
                http_response_code(400);
                echo json_encode(['status' => 'error', 'message' => 'JSON malformado na requisição.']);
                exit;
            }
        } else {
            $requestData = $input;
        }
    }
}

$centralApiUrl = getenv('CENTRAL_API_URL') ?: 'http://central-server:5000';

if ($effectivePath === '/login' && $method === 'POST') {
    $loginUrl = $centralApiUrl . '/login'; 
    forwardRequest($loginUrl, $method, $headers, $requestData);
    exit;
} elseif (in_array($effectivePath, $allCentralForwardRoutes)) {
    $headersToForward = [];
    foreach($headers as $key => $value) {
        if (strtolower($key) === 'host' || strtolower($key) === 'content-length') {
            continue;
        }
        $headersToForward[$key] = $value;
    }
    
    $urlForForwarding = $centralApiUrl . $effectivePath; 
    forwardRequest($urlForForwarding, $method, $headersToForward, $requestData);
} else {
    http_response_code(404);    
    echo json_encode(['status' => 'error', 'message' => 'Endpoint não encontrado no gateway.', 'requested_path' => $effectivePath]);
}
?>