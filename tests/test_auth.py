from fastapi.testclient import TestClient
from app.main import app
from app.auth import hash_senha, verificar_senha, criar_token

# Cliente para simular as chamadas na API
client = TestClient(app)


# Teste 1: Testar se o hash gera uma string diferente da senha original
def test_hash_senha_gera_string_diferente_original():
    senha = "minhasenha"
    hash_gerado = hash_senha(senha)

    # Testar a função
    assert senha != hash_gerado


# Teste 2: Testar se a verificação aceita a senha correta
def test_verificar_senha_com_sucesso():
    senha = "minhasenha123"
    hash_gerado = hash_senha(senha)

    # Executar a verificação
    resultado = verificar_senha(senha, hash_gerado)

    # Testar a função (deve retornar True)
    assert resultado is True


# Teste 3: Testar se a verificação rejeita uma senha incorreta
def test_verificar_senha_com_senha_errada():
    senha_correta = "minhasenha123"
    senha_errada = "senha_incorreta"
    hash_gerado = hash_senha(senha_correta)

    # Executar a verificação com senha errada
    resultado = verificar_senha(senha_errada, hash_gerado)

    # Testar a função (deve retornar False)
    assert resultado is False


# Teste 4: Testar a geração do token JWT de acesso
def test_criar_token_retorna_string_valida():
    dados = {"sub": "usuario@email.com", "id": 1}

    # Gerar o token JWT
    token = criar_token(dados)

    # Testar se o token foi gerado como texto não vazio
    assert isinstance(token, str)
    assert len(token) > 0


# Teste 5: Testar se a rota/tela de login está carregando
def test_tela_login_responde_com_sucesso():
    # Fazer a requisição GET na tela de login
    resposta = client.get("/auth/login")

    # Testar se a página abre sem erros (Status 200)
    assert resposta.status_code == 200