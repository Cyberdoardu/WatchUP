php
<?php

header('Content-Type: application/json');

require_once 'connection.php';

$response = array();
$response['data'] = array();

$sql = "SELECT monitor_name, current_status FROM monitors";
$result = $conn->query($sql);

$today = new DateTime();
$interval = new DateInterval('P1D'); // 1 day interval

if ($result->num_rows > 0) {
    while ($row = $result->fetch_assoc()) {
        $monitor_id_sql = "SELECT monitor_id FROM monitors WHERE monitor_name = '" . $conn->real_escape_string($row['monitor_name']) . "'";
        $monitor_id_result = $conn->query($monitor_id_sql);
        $monitor_id_row = $monitor_id_result->fetch_assoc();
        $monitor_id = $monitor_id_row['monitor_id'];

        $daily_status = array();
        for ($i = 89; $i >= 0; $i--) {
            $date = clone $today;
            $date->sub(new DateInterval("P{$i}D"));
            $date_str = $date->format('Y-m-d');

            $raw_data_sql = "SELECT COUNT(*) as total_checks, SUM(success) as successful_checks FROM raw_data WHERE monitor_id = {$monitor_id} AND DATE(timestamp) = '{$date_str}'";
            $raw_data_result = $conn->query($raw_data_sql);
            $raw_data_row = $raw_data_result->fetch_assoc();

            if ($raw_data_row['total_checks'] == 0) {
                $daily_status[] = 'no_data';
            } elseif ($raw_data_row['successful_checks'] == $raw_data_row['total_checks']) {
                $daily_status[] = 'available';
            } else {
                $daily_status[] = 'unavailable';
            }
        }

        $monitor = array(
            'monitor_name' => $row['monitor_name'],
            'current_status' => $row['current_status'],
            'historical_data' => $daily_status
        );
        array_push($response['data'], $monitor);
} else {
    $response['status'] = 'error';
    $response['message'] = 'No monitors found';
}

$conn->close();

$response['status'] = 'success';

echo json_encode($response);

?>