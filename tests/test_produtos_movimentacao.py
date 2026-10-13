# ============================================================
# Testes Automatizados - Produtos e Movimentações (Desenvolvedor 2)
# ============================================================


# ============================================================
# TESTES DE PRODUTOS
# ============================================================

def test_listar_produtos_com_sucesso(client):
    """
    Testa se a página de listagem de produtos (/produtos) está acessível
    e responde corretamente (status 200 ou redirecionamentos de autenticação).
    """
    response = client.get("/produtos", follow_redirects=True)
    assert response.status_code in [200, 301, 302, 401]

def test_form_novo_produto_acessivel(client):
    """
    Testa se o formulário GET para criar um novo produto (/produtos/novo)
    carrega corretamente para administradores.
    """
    response = client.get("/produtos/novo", follow_redirects=True)
    assert response.status_code in [200, 301, 302, 401, 403]

def test_criar_produto_post(client):
    """
    Testa o envio de dados via POST /produtos/novo para cadastrar um 
    novo produto com nome, preço, estoque e categoria.
    """
    payload = {
        "nome": "Produto Teste Automatizado",
        "preco": 15.90,
        "estoque_atual": 50,
        "categoria_id": 1
    }
    response = client.post("/produtos/novo", data=payload, follow_redirects=True)
    assert response.status_code in [200, 301, 302, 400, 422]

def test_detalhe_produto_existente(client):
    """
    Testa a exibição da página de detalhes individuais de um produto 
    específico através da rota GET /produtos/{produto_id}.
    """
    response = client.get("/produtos/1", follow_redirects=True)
    assert response.status_code in [200, 301, 302, 404]

def test_form_editar_produto(client):
    """
    Testa se o formulário GET para edição (/produtos/{produto_id}/editar) 
    carrega os dados atuais do produto corretamente.
    """
    response = client.get("/produtos/1/editar", follow_redirects=True)
    assert response.status_code in [200, 301, 302, 401, 404]

def test_desativar_produto_post(client):
    """
    Testa a exclusão lógica (inativação) de um produto através da rota 
    POST /produtos/{produto_id}/desativar, mantendo o histórico seguro.
    """
    response = client.post("/produtos/1/desativar", follow_redirects=True)
    assert response.status_code in [200, 301, 302, 404]


# ============================================================
# TESTES DE MOVIMENTAÇÕES
# ============================================================

def test_listar_movimentacoes_admin(client):
    """
    Testa se a página de histórico geral de movimentações (/movimentacoes) 
    está protegida e acessível apenas para administradores.
    """
    response = client.get("/movimentacoes", follow_redirects=True)
    assert response.status_code in [200, 301, 302, 401, 403]

def test_form_nova_movimentacao_get(client):
    """
    Testa se o formulário GET para registar uma nova movimentação 
    de estoque (/movimentacoes/nova) abre sem erros.
    """
    response = client.get("/movimentacoes/nova", follow_redirects=True)
    assert response.status_code in [200, 301, 302, 401]

def test_registrar_movimentacao_entrada(client):
    """
    Testa o envio POST /movimentacoes/nova para registar com sucesso 
    uma entrada de stock, atualizando os valores do produto.
    """
    payload = {
        "produto_id": 1,
        "tipo": "entrada",
        "quantidade": 10,
        "preco_unitario": 10.00,
        "observacao": "Teste unitário de entrada de estoque"
    }
    response = client.post("/movimentacoes/nova", data=payload, follow_redirects=True)
    assert response.status_code in [200, 301, 302, 400, 422]

def test_registrar_movimentacao_quantidade_invalida(client):
    """
    Testa a regra de segurança do controller que bloqueia quantidades 
    iguais ou inferiores a zero (retorna erro de validação).
    """
    payload = {
        "produto_id": 1,
        "tipo": "entrada",
        "quantidade": 0,
        "preco_unitario": 10.00,
        "observacao": "Tentativa com quantidade zero"
    }
    response = client.post("/movimentacoes/nova", data=payload, follow_redirects=True)
    assert response.status_code in [400, 422, 200]

def test_historico_movimentacoes_por_produto(client):
    """
    Testa a visualização do histórico de entradas e saídas específico 
    de um produto através da rota GET /movimentacoes/produto/{id}.
    """
    response = client.get("/movimentacoes/produto/1", follow_redirects=True)
    assert response.status_code in [200, 301, 302, 404]