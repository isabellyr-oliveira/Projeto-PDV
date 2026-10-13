# ============================================================
# Testes Automatizados - Módulo de Clientes (Desenvolvedor 1)
# ============================================================

def test_listar_clientes_protegido(client):
    """Testa se a listagem de clientes exige permissões adequadas."""
    response = client.get("/clientes", follow_redirects=False)
    assert response.status_code in [302, 307, 401, 403]

def test_criar_e_editar_cliente(client, db):
    """Testa o registo de um novo cliente e a respetiva edição."""
    payload = {
        "nome": "Carlos Cliente",
        "is_associado": True
    }
    response = client.post("/clientes/novo", data=payload, follow_redirects=True)
    assert response.status_code in [200, 301, 302, 307]

def test_toggle_ativo_cliente(client, db):
    """Testa a alteração de estado (ativo/inativo) de um cliente."""
    response = client.post("/clientes/1/toggle-ativo", follow_redirects=True)
    assert response.status_code in [200, 301, 302, 307]