# Teste 1: Testar se a tela do formulário de nova categoria carrega
def test_tela_nova_categoria_carrega_com_sucesso(cliente):
    # Executar a requisição GET para abrir a página
    resposta = cliente.get("/categorias/nova")

    # Validar se o status retornado é 200 (Sucesso)
    assert resposta.status_code == 200


# Teste 2: Testar o cadastro de uma nova categoria com sucesso
def test_criar_nova_categoria_com_sucesso(cliente):
    # Preparar os dados da nova categoria
    dados = {"nome": "Bebidas"}

    # Executar o POST para cadastrar (sem seguir redirecionamento automático)
    resposta = cliente.post("/categorias/nova", data=dados, follow_redirects=False)

    # Validar se redirecionou para a listagem (Status 302) com parâmetro de sucesso
    assert resposta.status_code == 302
    assert "/categorias?criado=ok" in resposta.headers["location"]


# Teste 3: Testar o bloqueio de cadastro para categoria duplicada
def test_criar_categoria_duplicada_retorna_erro(cliente):
    # Cadastrar a primeira vez
    cliente.post("/categorias/nova", data={"nome": "Limpeza"})

    # Tentar cadastrar a mesma categoria novamente
    resposta = cliente.post("/categorias/nova", data={"nome": "Limpeza"})

    # Validar se retornou erro 400 e a mensagem de alerta no HTML
    assert resposta.status_code == 400
    assert "Já existe uma categoria com este nome." in resposta.text


# Teste 4: Testar a alteração do nome de uma categoria existente
def test_editar_categoria_com_sucesso(cliente):
    # 1. Criar uma categoria para poder editar
    cliente.post("/categorias/nova", data={"nome": "Snacks"})

    # 2. Executar a alteração do nome na categoria ID 1
    dados_atualizados = {"nome": "Snacks e Petiscos"}
    resposta = cliente.post("/categorias/1/editar", data=dados_atualizados, follow_redirects=False)

    # Validar se redirecionou com aviso de editado=ok
    assert resposta.status_code == 302
    assert "/categorias?editado=ok" in resposta.headers["location"]


# Teste 5: Testar a exclusão de uma categoria
def test_deletar_categoria_redireciona_com_sucesso(cliente):
    # 1. Criar uma categoria para deletar
    cliente.post("/categorias/nova", data={"nome": "Hortifruti"})

    # 2. Executar a rota de exclusão na categoria ID 1
    resposta = cliente.get("/categorias/1/deletar", follow_redirects=False)

    # Validar se redirecionou com confirmação de deletado=ok
    assert resposta.status_code == 302
    assert "/categorias?deletado=ok" in resposta.headers["location"]