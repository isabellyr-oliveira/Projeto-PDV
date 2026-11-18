# Teste 1: Testar se a tela de formulário de novo cliente carrega
def test_tela_novo_cliente_carrega_com_sucesso(cliente):
    # Executar a requisição GET para abrir a página de cadastro de cliente
    resposta = cliente.get("/clientes/novo")

    # Validar se o status retornado é 200 (Sucesso)
    assert resposta.status_code == 200


# Teste 2: Testar o cadastro de um novo cliente com sucesso
def test_criar_cliente_com_sucesso(cliente):
    # Preparar os dados do novo cliente
    dados = {
        "nome": "João Silva",
        "is_associado": "true"
    }

    # Executar o POST para cadastrar (sem seguir o redirecionamento automático)
    resposta = cliente.post("/clientes/novo", data=dados, follow_redirects=False)

    # Validar se redirecionou para a listagem (Status 302) com parâmetro criado=ok
    assert resposta.status_code == 302
    assert "/clientes?criado=ok" in resposta.headers["location"]


# Teste 3: Testar a listagem de clientes
def test_listar_clientes_carrega_com_sucesso(cliente):
    # Executar a requisição GET na página principal de clientes
    resposta = cliente.get("/clientes/")

    # Validar se o status retornado é 200 (Sucesso)
    assert resposta.status_code == 200


# Teste 4: Testar a edição dos dados de um cliente
def test_editar_cliente_com_sucesso(cliente):
    # 1. Cadastrar um cliente primeiro
    cliente.post("/clientes/novo", data={"nome": "Maria Souza", "is_associado": "false"})

    # 2. Atualizar o nome do cliente ID 1
    dados_atualizados = {
        "nome": "Maria Souza Santos",
        "is_associado": "true"
    }
    resposta = cliente.post("/clientes/1/editar", data=dados_atualizados, follow_redirects=False)

    # Validar se redirecionou para a listagem confirmando editado=ok
    assert resposta.status_code == 302
    assert "/clientes?editado=ok" in resposta.headers["location"]


# Teste 5: Testar a alternância do status ativo/inativo (toggle-ativo)
def test_toggle_ativo_cliente_redireciona_com_sucesso(cliente):
    # 1. Cadastrar um cliente para alternar o status
    cliente.post("/clientes/novo", data={"nome": "Carlos Oliveira", "is_associado": "false"})

    # 2. Executar o POST para inativar/ativar o cliente ID 1
    resposta = cliente.post("/clientes/1/toggle-ativo", follow_redirects=False)

    # Validar se redirecionou com sucesso de volta para /clientes (Status 302)
    assert resposta.status_code == 302
    assert "/clientes" in resposta.headers["location"]