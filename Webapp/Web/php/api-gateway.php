<?php
// A ORDEM DE INCLUSÃO É IMPORTANTE AQUI!
require_once __DIR__ . '/vendor/firebase/jwt/src/JWTExceptionWithPayloadInterface.php';
require_once __DIR__ . '/vendor/firebase/jwt/src/ExpiredException.php';
require_once __DIR__ . '/vendor/firebase/jwt/src/BeforeValidException.php';
require_once __DIR__ . '/vendor/firebase/jwt/src/SignatureInvalidException.php';
require_once __DIR__ . '/vendor/firebase/jwt/src/JWK.php'; 
require_once __DIR__ . '/vendor/firebase/jwt/src/Key.php';
require_once __DIR__ . '/vendor/firebase/jwt/src/JWT.php';
require_once __DIR__ . '/vendor/firebase/jwt/src/CachedKeySet.php';
require_once __DIR__ . '/connection.php';

use Firebase\JWT\JWT;
use Firebase\JWT\Key;

class ReportHandler {
    private $conn;

    public function __construct() {
        $this->conn = MariaDBConnection::getConnection();
    }

    public function handleGetMonitors() {
        $query = "SELECT id, monitor_name FROM monitors ORDER BY monitor_name ASC";
        $result = $this->conn->query($query);
        if ($result) {
            header('Content-Type: application/json');
            $monitors = $result->fetch_all(MYSQLI_ASSOC);
            echo json_encode($monitors);
        } else {
            http_response_code(500);
            echo json_encode(['status' => 'error', 'message' => 'Erro ao buscar monitores: ' . $this->conn->error]);
        }
    }

    public function handleGetReportData() {
        if (!isset($_GET['monitor_id']) || !isset($_GET['start_date']) || !isset($_GET['end_date'])) {
            http_response_code(400);
            echo json_encode(['status' => 'error', 'message' => 'Parâmetros ausentes: monitor_id, start_date e end_date são obrigatórios.']);
            return;
        }

        $monitor_id = intval($_GET['monitor_id']);
        $start_date = $_GET['start_date'] . ' 00:00:00';
        $end_date = $_GET['end_date'] . ' 23:59:59';
        
        $query = "
            SELECT 
                rd.timestamp, 
                rd.success,
                COALESCE(JSON_UNQUOTE(JSON_EXTRACT(m.parameters, '$.check_time')), 60) AS request_interval
            FROM raw_data AS rd
            JOIN monitors AS m ON rd.monitor_id = m.id
            WHERE rd.monitor_id = ? 
            AND rd.timestamp BETWEEN ? AND ?
            ORDER BY rd.timestamp ASC
        ";

        $stmt = $this->conn->prepare($query);
        if (!$stmt) {
            http_response_code(500);
            echo json_encode(['status' => 'error', 'message' => 'Erro na preparação da consulta: ' . $this->conn->error]);
            return;
        }

        $stmt->bind_param("iss", $monitor_id, $start_date, $end_date);
        $stmt->execute();
        $result = $stmt->get_result();
        
        if ($result) {
            header('Content-Type: application/json');
            $data = $result->fetch_all(MYSQLI_ASSOC);
            echo json_encode($data);
        } else {
            http_response_code(500);
            echo json_encode(['status' => 'error', 'message' => 'Erro ao buscar dados do relatório: ' . $stmt->error]);
        }
        
        $stmt->close();
    }
}

function authenticateRequest() {
    $authHeader = null;
    if (isset($_SERVER['HTTP_AUTHORIZATION'])) {
        $authHeader = $_SERVER['HTTP_AUTHORIZATION'];
    } elseif (isset($_SERVER['REDIRECT_HTTP_AUTHORIZATION'])) {
        $authHeader = $_SERVER['REDIRECT_HTTP_AUTHORIZATION'];
    } elseif (function_exists('getallheaders')) {
        $headers = getallheaders();
        $authHeader = $headers['Authorization'] ?? $headers['authorization'] ?? null;
    }

    if (!$authHeader) {
        http_response_code(401);
        header('Content-Type: application/json');
        echo json_encode(['status' => 'error', 'message' => 'Não autorizado: Cabeçalho de autorização ausente']);
        exit;
    }
    
    list($jwt) = sscanf($authHeader, 'Bearer %s');

    if (!$jwt) {
        http_response_code(401);
        header('Content-Type: application/json');
        echo json_encode(['status' => 'error', 'message' => 'Não autorizado: Formato do token inválido']);
        exit;
    }
    
    $secretKey = getenv('JWT_SECRET');
    if (!$secretKey) {
        http_response_code(500);
        header('Content-Type: application/json');
        echo json_encode(['status' => 'error', 'message' => 'Erro Interno do Servidor: Segredo JWT não configurado.']);
        exit;
    }

    try {
        $decoded = JWT::decode($jwt, new Key($secretKey, 'HS256'));        
        return (array) $decoded->data;
    } catch (Exception $e) { 
        http_response_code(401);
        header('Content-Type: application/json');
        echo json_encode(['status' => 'error', 'message' => 'Não autorizado: Token inválido ou expirado.']);
        exit;
    }
}

function forwardRequest($url, $method, $data = null) {
    $ch = curl_init();
    $curlUrl = $url;

    if (!empty($_GET)) {
        $originalGetParams = $_GET;
        unset($originalGetParams['endpoint']);
        if (!empty($originalGetParams)) {
            $queryString = http_build_query($originalGetParams);
            $curlUrl .= (strpos($curlUrl, '?') === false ? '?' : '&') . $queryString;
        }
    }
    
    curl_setopt($ch, CURLOPT_URL, $curlUrl);
    curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 30);
    
    $headersToForward = [];
    $allHeaders = getallheaders();
    if ($allHeaders) {
        foreach($allHeaders as $key => $value) {
            if (strtolower($key) === 'host' || strtolower($key) === 'content-length') {
                continue;
            }
            $headersToForward[] = "$key: $value";
        }
    }

    if ($data !== null && ($method === 'POST' || $method === 'PUT')) {
        $jsonData = json_encode($data);
        $headersToForward[] = 'Content-Type: application/json';
        $headersToForward[] = 'Content-Length: ' . strlen($jsonData);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $jsonData);
    }
    
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headersToForward);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $curlError = curl_error($ch);
    curl_close($ch);

    if ($curlError) {
        http_response_code(500);
        echo json_encode(['status' => 'error', 'message' => 'Falha ao encaminhar a requisição.', 'details' => $curlError]);
        exit;
    }

    http_response_code($httpCode);
    echo $response;
}

// --- INÍCIO DA LÓGICA DE ROTEAMENTO ---

// 1. DETERMINAR A ROTA
$effectivePath = '/' . trim($_GET['endpoint'] ?? '', '/');
$method = $_SERVER['REQUEST_METHOD'];

// 2. DEFINIR QUAIS ROTAS SÃO PROTEGIDAS E QUAIS SÃO ENCAMINHADAS
$jwtProtectedUserRoutes = [
    '/monitors',    
    '/agents',
    '/report_data'
];

$centralServerForwardRoutes = [
    '/monitors', // POST para criar é encaminhado
    '/agents'    // GET para listar é encaminhado
];

// 3. VERIFICAR AUTENTICAÇÃO PRIMEIRO
if (in_array($effectivePath, $jwtProtectedUserRoutes)) {
    $user_payload = authenticateRequest();
}

// 4. PROCESSAR A ROTA
$requestData = null;
if (in_array($method, ['POST', 'PUT', 'PATCH'])) {
    $input = file_get_contents('php://input');
    if ($input) {
        $requestData = json_decode($input, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            http_response_code(400);
            echo json_encode(['status' => 'error', 'message' => 'JSON malformado na requisição.']);
            exit;
        }
    }
}

// Roteamento local para o ReportHandler (apenas GET)
if ($method === 'GET' && $effectivePath === '/monitors') {
    $handler = new ReportHandler();
    $handler->handleGetMonitors();
    exit;
}
if ($method === 'GET' && $effectivePath === '/report_data') {
    $handler = new ReportHandler();
    $handler->handleGetReportData();
    exit;
}

// Encaminhamento para o Central Server
if (in_array($effectivePath, $centralServerForwardRoutes)) {
    $centralApiUrl = getenv('CENTRAL_API_URL') ?: 'http://central-server:5000';
    $urlForForwarding = $centralApiUrl . $effectivePath;
    forwardRequest($urlForForwarding, $method, $requestData);
    exit;
}

// 5. SE NENHUMA ROTA CORRESPONDER
http_response_code(404);    
echo json_encode(['status' => 'error', 'message' => 'Endpoint não encontrado no gateway.', 'requested_path' => $effectivePath]);
?>