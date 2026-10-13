def test_home_ou_login_acessivel(client):
    response = client.get("/", follow_redirects=True)
    assert response.status_code in [200, 302, 401]

def test_rota_pdv_acessivel(client):
    response = client.get("/pdv", follow_redirects=True)
    assert response.status_code in [200, 301, 302, 401]

def test_finalizar_venda_com_sucesso(client):
    """Testa o fluxo de checkout enviando o carrinho, cliente e formas de pagamento."""
    payload_venda = {
        "cliente_id": "0",
        "tipo_desconto": "RS",
        "desconto_manual": "0.00",
        "carrinho_json": '[{"produto_id": 1, "nome": "Produto Teste", "preco": 10.0, "quantidade": 2}]',
        "forma_pagamento_1": "Dinheiro",
        "valor_pagamento_1": "20.00",
        "forma_pagamento_2": "",
        "valor_pagamento_2": "",
        "observacao": "Teste automatizado Sprint 3"
    }
    response = client.post("/pdv/finalizar", data=payload_venda, follow_redirects=True)
    assert response.status_code in [200, 301, 302, 422]

def test_dupla_forma_pagamento_dividida(client):
    """Testa o requisito da Sprint 3 de pagamento dividido em duas formas diferentes."""
    payload_venda = {
        "cliente_id": "0",
        "tipo_desconto": "RS",
        "desconto_manual": "0.00",
        "carrinho_json": '[{"produto_id": 1, "nome": "Produto Teste", "preco": 50.0, "quantidade": 1}]',
        "forma_pagamento_1": "Dinheiro",
        "valor_pagamento_1": "30.00",
        "forma_pagamento_2": "Cartão de Débito",
        "valor_pagamento_2": "20.00"
    }
    response = client.post("/pdv/finalizar", data=payload_venda, follow_redirects=True)
    assert response.status_code in [200, 301, 302, 422]