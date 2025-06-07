<?php
// php/report_handler.php

// Requer o arquivo de conexão com o banco de dados
require_once __DIR__ . '/connection.php';

class ReportHandler {

    private $conn;

    public function __construct() {
        // Obtém a instância da conexão do banco de dados
        $this->conn = MariaDBConnection::getConnection();
    }

    /**
     * Busca no banco e retorna todos os monitores cadastrados em formato JSON.
     */
    public function handleGetMonitors() {
        // A consulta SQL para buscar os monitores
        $query = "SELECT id, monitor_name FROM monitors ORDER BY monitor_name ASC";
        
        $result = $this->conn->query($query);

        if ($result) {
            $monitors = $result->fetch_all(MYSQLI_ASSOC);
            echo json_encode($monitors);
        } else {
            http_response_code(500);
            echo json_encode(['status' => 'error', 'message' => 'Erro ao buscar monitores: ' . $this->conn->error]);
        }
    }

    /**
     * Busca os dados brutos para um relatório com base nos parâmetros GET.
     */
    public function handleGetReportData() {
        // Valida se os parâmetros necessários foram enviados na URL
        if (!isset($_GET['monitor_id']) || !isset($_GET['start_date']) || !isset($_GET['end_date'])) {
            http_response_code(400);
            echo json_encode(['status' => 'error', 'message' => 'Parâmetros ausentes: monitor_id, start_date e end_date são obrigatórios.']);
            return;
        }

        $monitor_id = intval($_GET['monitor_id']);
        // Garante que o período inclua o dia inteiro
        $start_date = $_GET['start_date'] . ' 00:00:00';
        $end_date = $_GET['end_date'] . ' 23:59:59';
        
        // Consulta SQL que busca os dados e também extrai o 'request_interval' do campo JSON 'parameters'
        $query = "
            SELECT 
                rd.timestamp, 
                rd.success,
                JSON_UNQUOTE(JSON_EXTRACT(m.parameters, '$.request_interval')) AS request_interval
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

        // Usa prepared statements para prevenir SQL Injection
        $stmt->bind_param("iss", $monitor_id, $start_date, $end_date);
        $stmt->execute();
        $result = $stmt->get_result();
        
        if ($result) {
            $data = $result->fetch_all(MYSQLI_ASSOC);
            echo json_encode($data);
        } else {
            http_response_code(500);
            echo json_encode(['status' => 'error', 'message' => 'Erro ao buscar dados do relatório: ' . $stmt->error]);
        }
        
        $stmt->close();
    }
}
?>