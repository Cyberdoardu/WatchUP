<?php
require_once 'connection.php';
header('Content-Type: application/json');

$db     = MariaDBConnection::getConnection();
$method = $_SERVER['REQUEST_METHOD'];
$action = $_GET['action'] ?? '';

function getInput() {
    return json_decode(file_get_contents('php://input'), true);
}

// GET: listar
if ($method === 'GET') {
    $res = $db->query("SELECT * FROM incidentes ORDER BY criado_em DESC");
    $out = [];
    while ($r = $res->fetch_assoc()) $out[] = $r;
    echo json_encode(["sucesso"=>true,"incidentes"=>$out]);
    exit;
}

// POST sem action: criar
if ($method === 'POST' && $action === '') {
    $d = getInput();
    foreach (['titulo','descricao','impacto','tipo','servico'] as $f) {
      if (empty($d[$f])) {
        http_response_code(400);
        echo json_encode(["sucesso"=>false,"mensagem"=>"Campo $f obrigatório"]);
        exit;
      }
    }
    $stmt = $db->prepare(
      "INSERT INTO incidentes (titulo, descricao, impacto, tipo, servico)
       VALUES (?,?,?,?,?)"
    );
    $stmt->bind_param("sssss",
      $d['titulo'],$d['descricao'],$d['impacto'],$d['tipo'],$d['servico']
    );
    if($stmt->execute()){
      echo json_encode(["sucesso"=>true]);
    } else {
      http_response_code(500);
      echo json_encode(["sucesso"=>false,"mensagem"=>"Erro ao criar incidente"]);
    }
    exit;
}

// POST?action=delete: remover
if ($method === 'POST' && $action === 'delete') {
    $d = getInput();
    $id = intval($d['id'] ?? 0);
    if ($id<=0) {
      http_response_code(400);
      echo json_encode(["sucesso"=>false,"mensagem"=>"ID inválido"]);
      exit;
    }
    $stmt = $db->prepare("DELETE FROM incidentes WHERE id=?");
    $stmt->bind_param("i",$id);
    if($stmt->execute()){
      echo json_encode(["sucesso"=>true]);
    } else {
      http_response_code(500);
      echo json_encode(["sucesso"=>false,"mensagem"=>"Erro ao remover"]);
    }
    exit;
}

// POST?action=updateState: atualizar estado
if ($method === 'POST' && $action === 'updateState') {
  $d = getInput();
  $id  = intval($d['id'] ?? 0);
  $est = $db->real_escape_string($d['estado'] ?? '');
  if ($id<=0 || !$est) {
    http_response_code(400);
    echo json_encode(["sucesso"=>false,"mensagem"=>"Dados inválidos"]);
    exit;
  }

  $stmt = null;
  // Se o estado for 'Resolvido', atualiza também a data de resolução.
  if ($est === 'Resolvido') {
      $stmt = $db->prepare("UPDATE incidentes SET estado_atual=?, resolvido_em=NOW() WHERE id=?");
      $stmt->bind_param("si", $est, $id);
  } else {
      // Caso contrário, apenas atualiza o estado e garante que a data de resolução fique nula.
      $stmt = $db->prepare("UPDATE incidentes SET estado_atual=?, resolvido_em=NULL WHERE id=?");
      $stmt->bind_param("si", $est, $id);
  }

  if($stmt->execute()){
    echo json_encode(["sucesso"=>true]);
  } else {
    http_response_code(500);
    echo json_encode(["sucesso"=>false,"mensagem"=>"Erro ao atualizar estado"]);
  }
  exit;
}

http_response_code(405);
echo json_encode(["sucesso"=>false,"mensagem"=>"Método não permitido"]);
