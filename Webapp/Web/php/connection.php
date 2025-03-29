<?php
require_once 'vendor/autoload.php'; // Carregar dependências

class ScyllaDB {
    private static $cluster;
    private static $session;

    public static function getSession() {
        if (!self::$session) {
            try {
                self::$cluster = Cassandra::cluster()
                    ->withContactPoints('scylladb') // Nome do serviço no Docker
                    ->build();
                
                self::$session = self::$cluster->connect("watchup");

            } catch (Cassandra\Exception $e) {
                error_log("SCYLLA CONNECTION ERROR: " . $e->getMessage());
                die(json_encode([
                    "sucesso" => false,
                    "mensagem" => "Erro de conexão com o banco de dados"
                ]));
            }
        }
        return self::$session;
    }
}
?>