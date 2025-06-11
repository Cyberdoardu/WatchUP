<?php
header('Content-Type: application/json');
require_once 'connection.php';

$conn = MariaDBConnection::getConnection();

$response = ['data' => []];
$sql = "SELECT id as monitor_id, monitor_name, current_status FROM monitors";
$result = $conn->query($sql);
$today = new DateTime();

if ($result->num_rows > 0) {
    while ($row = $result->fetch_assoc()) {
        $monitor_id = $row['monitor_id'];
        $daily_history = [];

        // Loop para os últimos 90 dias
        for ($i = 89; $i >= 0; $i--) {
            $date = clone $today;
            $date->sub(new DateInterval("P{$i}D"));
            $date_str = $date->format('Y-m-d');

            // Query para obter o total de checagens e as bem-sucedidas
            $query = "SELECT COUNT(*) as total, SUM(success) as successes 
                      FROM raw_data 
                      WHERE monitor_id = {$monitor_id} AND DATE(timestamp) = '{$date_str}'";
            
            $result_data = $conn->query($query);
            $row_data = $result_data->fetch_assoc();

            $status = 'no_data';
            $sla = 'N/A';

            if ($row_data['total'] > 0) {
                // Calcula o SLA
                $sla = number_format(($row_data['successes'] / $row_data['total']) * 100, 2);
                $status = $sla == 100.00 ? 'available' : 'unavailable';
            }
            
            $daily_history[] = ['status' => $status, 'sla' => $sla];
        }

        $response['data'][] = [
            'monitor_name' => $row['monitor_name'],
            'current_status' => $row['current_status'],
            'history_90_days' => $daily_history
        ];
    }
    $response['status'] = 'success';
} else {
    $response['status'] = 'error';
    $response['message'] = 'No monitors found';
}

$conn->close();
echo json_encode($response);
?>