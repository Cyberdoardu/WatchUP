php
<?php
require_once 'connection.php';

//Check connection
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// Handle agent creation request
if ($_SERVER["REQUEST_METHOD"] == "POST" && isset($_POST["action"]) && $_POST["action"] == "create_agent") {
    $agentName = $_POST["agent_name"];

    // Generate a unique ID for the agent
    $agentId = uniqid();
    $creationTimestamp = time();

    // Store the agent creation request in the database
    $sql = "INSERT INTO agents (agent_id, agent_name, creation_timestamp, status) VALUES (?, ?, ?, 'pending')";
    $stmt = $conn->prepare($sql);
    $stmt->bind_param("sss", $agentId, $agentName, $creationTimestamp);

    if ($stmt->execute()) {
        echo json_encode(["status" => "success", "agent_id" => $agentId, "message" => "Agent creation requested"]);
    } else {
        echo json_encode(["status" => "error", "message" => "Failed to create agent request"]);
     }
    $stmt->close();
}

// Handle agent connection request
if ($_SERVER["REQUEST_METHOD"] == "POST" && isset($_POST["action"]) && $_POST["action"] == "agent_connect") {
    $agentId = $_POST["agent_id"];

    // Check if the agent has a pending creation request
    $sql = "SELECT * FROM agents WHERE agent_id = ? AND status = 'pending'";
    $stmt = $conn->prepare($sql);
    $stmt->bind_param("s", $agentId);
    $stmt->execute();
    $result = $stmt->get_result();

    if ($result->num_rows > 0) {
        // Update the agent status to 'connected'
        $sql = "UPDATE agents SET status = 'connected' WHERE agent_id = ?";
        $stmt = $conn->prepare($sql);
        $stmt->bind_param("s", $agentId);
        $stmt->execute();
        echo json_encode(["status" => "success", "message" => "Agent connected"]);
    } else {
        echo json_encode(["status" => "error", "message" => "Invalid agent connection"]);
    }
    $stmt->close();
}

// Handle agent connection cancellation request
if ($_SERVER["REQUEST_METHOD"] == "POST" && isset($_POST["action"]) && $_POST["action"] == "cancel_deletion") {
    $agentId = $_POST["agent_id"];
    // Check if the agent has a pending creation request
    $sql = "SELECT * FROM agents WHERE agent_id = ? AND status = 'pending'";
    $stmt = $conn->prepare($sql);
    $stmt->bind_param("s", $agentId);
    $stmt->execute();
    $result = $stmt->get_result();

    if ($result->num_rows > 0) {
        // Update the agent status to 'connected'
        $sql = "UPDATE agents SET status = 'connected' WHERE agent_id = ?";
        $stmt = $conn->prepare($sql);
        $stmt->bind_param("s", $agentId);
        $stmt->execute();
        echo json_encode(["status" => "success", "message" => "Agent deletion canceled."]);
    } else {
       echo json_encode(["status" => "error", "message" => "Invalid agent deletion cancellation."]);
    }
     $stmt->close();
}

//Clean up pending requests
$sql = "DELETE FROM agents WHERE status = 'pending' AND creation_timestamp < (UNIX_TIMESTAMP() - 60)";
$conn->query($sql);

?>