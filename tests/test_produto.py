# Teste 1: Testar se a tela de listagem de produtos carrega com sucesso
def test_listar_produtos_carrega_com_sucesso(cliente):
    # Executar a requisição GET na página principal de produtos
    resposta = cliente.get("/produtos/")

    # Validar se o status retornado é 200 (Sucesso)
    assert resposta.status_code == 200


# Teste 2: Testar se a tela do formulário de novo produto carrega
def test_tela_novo_produto_carrega_com_sucesso(cliente):
    # Executar a requisição GET para abrir a página de cadastro
    resposta = cliente.get("/produtos/novo")

    # Validar se o status retornado é 200 (Sucesso)
    assert resposta.status_code == 200


# Teste 3: Testar o cadastro de um novo produto com sucesso
def test_criar_produto_com_sucesso(cliente):
    # Preparar os dados do formulário do produto
    dados = {
        "nome": "Caderno Universitário",
        "preco": 15.90,
        "estoque_atual": 50,
        "categoria_id": 0
    }

    # Executar o POST para cadastrar (sem seguir o redirecionamento automático)
    resposta = cliente.post("/produtos/novo", data=dados, follow_redirects=False)

    # Validar se redirecionou para a listagem (Status 302) com parâmetro criado=ok
    assert resposta.status_code == 302
    assert "/produtos?criado=ok" in resposta.headers["location"]


# Teste 4: Testar o bloqueio de cadastro para produto com nome duplicado
def test_criar_produto_duplicado_retorna_erro(cliente):
    # 1. Cadastrar o primeiro produto
    dados = {
        "nome": "Caneta Azul",
        "preco": 2.50,
        "estoque_atual": 100,
        "categoria_id": 0
    }
    cliente.post("/produtos/novo", data=dados)

    # 2. Tentar cadastrar um segundo produto com o mesmo nome
    resposta = cliente.post("/produtos/novo", data=dados)

    # Validar se retornou status 400 e a mensagem de erro no HTML
    assert resposta.status_code == 400
    assert "Já existe um produto com este nome." in resposta.text


# Teste 5: Testar a exclusão física de um produto
def test_deletar_produto_redireciona_com_sucesso(cliente):
    # 1. Cadastrar um produto para ser deletado
    dados = {
        "nome": "Borracha Escolar",
        "preco": 1.00,
        "estoque_atual": 20,
        "categoria_id": 0
    }
    cliente.post("/produtos/novo", data=dados)

    # 2. Executar a rota de exclusão para o produto ID 1
    resposta = cliente.get("/produtos/1/deletar", follow_redirects=False)

    # Validar se redirecionou para a listagem confirmando deletado=ok
    assert resposta.status_code == 302
    assert "/produtos?deletado=ok" in resposta.headers["location"]