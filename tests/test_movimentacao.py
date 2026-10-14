# Teste 1: Testar se a tela do histórico geral de movimentações carrega com sucesso
def test_tela_listar_movimentacoes_carrega_com_sucesso(cliente):
    # Executar a requisição GET para abrir a listagem geral
    resposta = cliente.get("/movimentacoes/")

    # Validar se o status retornado é 200 (Sucesso)
    assert resposta.status_code == 200


# Teste 2: Testar se a tela de formulário para nova movimentação carrega
def test_tela_nova_movimentacao_carrega_com_sucesso(cliente):
    # Executar a requisição GET para abrir a página de registro
    resposta = cliente.get("/movimentacoes/nova")

    # Validar se o status retornado é 200 (Sucesso)
    assert resposta.status_code == 200


# Teste 3: Testar a validação de erro para tipo de movimentação inválido
def test_registrar_movimentacao_com_tipo_invalido_retorna_erro(cliente):
    # Preparar dados com um tipo não existente (ex: "invalido")
    dados = {
        "produto_id": 1,
        "tipo": "invalido",
        "quantidade": 10,
        "preco_unitario": 5.0,
        "observacao": "Teste tipo inválido"
    }

    # Executar o POST para registrar
    resposta = cliente.post("/movimentacoes/nova", data=dados)

    # Validar se retornou status 400 e a mensagem de erro esperada
    assert resposta.status_code == 400
    assert "Tipo de movimentação inválido." in resposta.text


# Teste 4: Testar a validação de erro para quantidade menor ou igual a zero
def test_registrar_movimentacao_com_quantidade_invalida_retorna_erro(cliente):
    # Preparar dados com quantidade zero
    dados = {
        "produto_id": 1,
        "tipo": "entrada",
        "quantidade": 0,
        "preco_unitario": 10.0,
        "observacao": "Sem quantidade"
    }

    # Executar o POST para registrar
    resposta = cliente.post("/movimentacoes/nova", data=dados)

    # Validar se retornou status 400 e a mensagem de erro esperada
    assert resposta.status_code == 400
    assert "A quantidade deve ser maior que zero." in resposta.text


# Teste 5: Testar o redirecionamento ao buscar histórico de produto inexistente
def test_historico_produto_inexistente_redireciona(cliente):
    # Tentar acessar o histórico de um produto ID 999 (inexistente)
    resposta = cliente.get("/movimentacoes/produto/999", follow_redirects=False)

    # Validar se redirecionou (Status 302) para a lista de produtos
    assert resposta.status_code == 302
    assert resposta.headers["location"] == "/produtos"