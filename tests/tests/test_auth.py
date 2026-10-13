# ============================================================
# Testes Automatizados - Módulo de Autenticação (Desenvolvedor 1)
# ============================================================

def test_tela_cadastro_acessivel(client):
    """Testa se a página de cadastro abre corretamente."""
    response = client.get("/auth/cadastro")
    assert response.status_code == 200

def test_tela_login_acessivel(client):
    """Testa se a página de login abre corretamente."""
    response = client.get("/auth/login")
    assert response.status_code == 200

def test_fluxo_cadastro_e_login_usuario(client, db):
    """Testa o registo de um novo utilizador e o respetivo login com geração de cookie JWT."""
    payload_cadastro = {
        "nome": "Utilizador Teste",
        "email": "teste@senai.com",
        "senha": "password123"
    }
    response_cad = client.post("/auth/cadastro", data=payload_cadastro, follow_redirects=False)
    assert response_cad.status_code in [301, 302]

    payload_login = {
        "email": "teste@senai.com",
        "senha": "password123"
    }
    response_login = client.post("/auth/login", data=payload_login, follow_redirects=False)
    assert response_login.status_code in [301, 302]
    assert "access_token" in response_login.cookies

    # Testar logout
    response_logout = client.get("/auth/logout", follow_redirects=False)
    assert response_logout.status_code in [301, 302]

def test_login_credenciais_invalidas(client):
    """Testa se o sistema rejeita credenciais incorretas."""
    payload = {
        "email": "inexistente@senai.com",
        "senha": "errada"
    }
    response = client.post("/auth/login", data=payload)
    assert response.status_code in [200, 400]