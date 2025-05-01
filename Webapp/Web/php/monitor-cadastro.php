php
<?php
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    // Receber os dados do monitor enviados pelo JavaScript
    $monitorData = $_POST;
    
    // Converter para JSON
    $jsonData = json_encode($monitorData);

    // URL do api-gateway.php com a rota /monitors
    $url = "http://localhost/php/api-gateway.php/monitors"; 

    // Inicializar cURL
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $jsonData);
    curl_setopt($ch, CURLOPT_HTTPHEADER, array(
        'Content-Type: application/json'
    ));
    
    // Executar a requisição e obter a resposta
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    
    curl_close($ch);
    
    // Enviar a resposta para o JavaScript
    header('Content-Type: application/json');
    echo $response;
    
}else {
        echo json_encode(["success" => false, "message" => "Invalid request method"]);
    }
?>
    );

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($httpCode == 200) {
        echo json_encode(["success" => true, "message" => "Monitor created successfully"]);
    } else {
        echo json_encode(["success" => false, "message" => "Failed to create monitor", "response" => $response]);
    }
} else {
    echo json_encode(["success" => false, "message" => "Invalid request method"]);
}
?>