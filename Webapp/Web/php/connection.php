<?php
class MariaDBConnection {
    private static $connection = null;

    public static function getConnection() {
        if (!self::$connection) {
            $host = $_ENV['DB_HOST'] ?? 'mariadb';
            $dbname = $_ENV['DB_NAME'] ?? 'watchup';
            $user = $_ENV['DB_USER'] ?? 'watchuser';
            $pass = $_ENV['DB_PASSWORD'] ?? 'watchpassword';

            try {
                self::$connection = new mysqli($host, $user, $pass, $dbname);
                
                if (self::$connection->connect_errno) {
                    throw new Exception("Connection failed: " . self::$connection->connect_error);
                }
                
                if (!self::$connection->set_charset("utf8mb4")) {
                    throw new Exception("Charset error: " . self::$connection->error);
                }

            } catch (Exception $e) {
                error_log("DATABASE ERROR: " . $e->getMessage());
                http_response_code(500);
                die(json_encode([
                    "sucesso" => false,
                    "mensagem" => "Erro crítico de banco de dados"
                ]));
            }
        }
        return self::$connection;
    }
}
?>