<?php

header('Content-Type: application/json');
require_once 'connection.php';

$response = array();
$response['data'] = array();

$sql = "SELECT id as monitor_id, monitor_name, current_status FROM monitors";
$result = $conn->query($sql);

$today = new DateTime();

if ($result->num_rows > 0) {
    while ($row = $result->fetch_assoc()) {
        $monitor_id = $row['monitor_id'];
        $daily_status = array();

        for ($i = 89; $i >= 0; $i--) {
            $date = clone $today;
            $date->sub(new DateInterval("P{$i}D"));
            $date_str = $date->format('Y-m-d');

            $query = "SELECT COUNT(*) as total, SUM(success) as success 
                      FROM raw_data 
                      WHERE monitor_id = {$monitor_id} AND DATE(timestamp) = '{$date_str}'";
            $result_data = $conn->query($query);
            $row_data = $result_data->fetch_assoc();

            if ($row_data['total'] == 0) {
                $daily_status[] = 'no_data';
            } elseif ($row_data['success'] == $row_data['total']) {
                $daily_status[] = 'available';
            } else {
                $daily_status[] = 'unavailable';
            }
        }

        $response['data'][] = array(
            'monitor_name' => $row['monitor_name'],
            'current_status' => $row['current_status'],
            'history_90_days' => $daily_status
        );
    }

    $response['status'] = 'success';
} else {
    $response['status'] = 'error';
    $response['message'] = 'No monitors found';
}

$conn->close();

echo json_encode($response);
