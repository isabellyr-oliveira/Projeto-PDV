# Teste 1: Testar se a tela de listagem de usuários carrega com sucesso
def test_listar_usuarios_carrega_com_sucesso(cliente):
    # Executar a requisição GET para listar os usuários
    resposta = cliente.get("/usuarios/")

    # Validar se o status retornado é 200 (Sucesso)
    assert resposta.status_code == 200


# Teste 2: Testar se a tela do formulário de novo usuário carrega
def test_tela_novo_usuario_carrega_com_sucesso(cliente):
    # Executar a requisição GET para abrir a página de formulário
    resposta = cliente.get("/usuarios/novo")

    # Validar se o status retornado é 200 (Sucesso)
    assert resposta.status_code == 200


# Teste 3: Testar o cadastro de um novo usuário com sucesso
def test_criar_usuario_com_sucesso(cliente):
    # Preparar os dados do novo usuário
    dados = {
        "nome": "Carlos Silva",
        "email": "carlos@email.com",
        "senha": "senha123",
        "role": "operador"
    }

    # Executar o POST para cadastrar (sem seguir o redirecionamento)
    resposta = cliente.post("/usuarios/novo", data=dados, follow_redirects=False)

    # Validar se redirecionou para a listagem (Status 302) com criado=ok
    assert resposta.status_code == 302
    assert "/usuarios?criado=ok" in resposta.headers["location"]


# Teste 4: Testar a validação de erro ao tentar cadastrar usuário com perfil (role) inválido
def test_criar_usuario_com_role_invalido_retorna_erro(cliente):
    # Preparar dados com um perfil não permitido (ex: "gerente")
    dados = {
        "nome": "Ana Lima",
        "email": "ana@email.com",
        "senha": "senha123",
        "role": "gerente"
    }

    # Executar o POST para cadastrar
    resposta = cliente.post("/usuarios/novo", data=dados)

    # Validar se retornou status 400 e a mensagem de erro esperada
    assert resposta.status_code == 400
    assert "Perfil de acesso inválido." in resposta.text


# Teste 5: Testar a alternância do status ativo/inativo (toggle-ativo)
def test_toggle_ativo_usuario_redireciona_com_sucesso(cliente):
    # 1. Cadastrar um novo usuário
    dados = {
        "nome": "Pedro Souza",
        "email": "pedro@email.com",
        "senha": "senha123",
        "role": "operador"
    }
    cliente.post("/usuarios/novo", data=dados)

    # 2. Executar o POST para inativar/ativar o usuário criado
    resposta = cliente.post("/usuarios/1/toggle-ativo", follow_redirects=False)

    # Validar se redirecionou com sucesso para /usuarios
    assert resposta.status_code == 302
    assert "/usuarios" in resposta.headers["location"]