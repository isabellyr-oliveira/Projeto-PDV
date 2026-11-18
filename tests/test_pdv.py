# Teste 1: Testar se a tela principal do PDV carrega com sucesso
def test_tela_pdv_carrega_com_sucesso(cliente):
    # Executar a requisição GET para abrir a tela de vendas do PDV
    resposta = cliente.get("/pdv/")

    # Validar se o status retornado é 200 (Sucesso)
    assert resposta.status_code == 200


# Teste 2: Testar o tratamento de erro ao enviar um JSON de carrinho inválido
def test_finalizar_venda_com_json_invalido_redireciona(cliente):
    # Preparar dados com um formato de JSON corrompido/inválido
    dados = {
        "carrinho_json": "texto_invalido_nao_json",
        "forma_pagamento_1": "dinheiro",
        "valor_pagamento_1": 50.0
    }

    # Executar o POST para tentar finalizar a venda (sem seguir redirecionamento)
    resposta = cliente.post("/pdv/finalizar", data=dados, follow_redirects=False)

    # Validar se redirecionou para o PDV com mensagem de erro de JSON (Status 302)
    assert resposta.status_code == 302
    assert "/pdv?erro=json" in resposta.headers["location"]


# Teste 3: Testar o tratamento de erro ao tentar finalizar com carrinho vazio
def test_finalizar_venda_com_carrinho_vazio_redireciona(cliente):
    # Preparar dados com lista de itens vazia em formato JSON
    dados = {
        "carrinho_json": "[]",
        "forma_pagamento_1": "dinheiro",
        "valor_pagamento_1": 0.0
    }

    # Executar o POST para tentar finalizar a venda
    resposta = cliente.post("/pdv/finalizar", data=dados, follow_redirects=False)

    # Validar se redirecionou com aviso de carrinho vazio (Status 302)
    assert resposta.status_code == 302
    assert "/pdv?erro=vazio" in resposta.headers["location"]


# Teste 4: Testar se a tela de histórico de vendas do PDV carrega
def test_historico_vendas_carrega_com_sucesso(cliente):
    # Executar a requisição GET para abrir o histórico de vendas
    resposta = cliente.get("/pdv/historico")

    # Validar se o status retornado é 200 (Sucesso)
    assert resposta.status_code == 200


# Teste 5: Testar o redirecionamento ao buscar comprovante de uma venda inexistente
def test_detalhe_venda_inexistente_redireciona(cliente):
    # Tentar acessar o comprovante da venda ID 9999 (inexistente)
    resposta = cliente.get("/pdv/venda/9999", follow_redirects=False)

    # Validar se redirecionou de volta para a tela do PDV (Status 302)
    assert resposta.status_code == 302
    assert resposta.headers["location"] == "/pdv"