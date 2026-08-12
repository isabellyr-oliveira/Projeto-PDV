# ============================================================================
# 1.4.5 TESTE DE SEGURANÇA
# ============================================================================
#
# O QUE É?
# Teste de segurança tenta usar o sistema de forma MALICIOSA de propósito
# (como um atacante faria) para descobrir vulnerabilidades antes que
# alguém mal-intencionado as encontre. Aqui cobrimos, com Python puro:
#   - Injeção de SQL
#   - Controle de acesso (usuário comum tentando agir como admin)
#   - Acesso sem login
#   - Adulteração de token JWT (falsificar login)
#   - Como a senha é armazenada
#   - Cross-Site Scripting (XSS) refletido
#   - Ausência de limite de tentativas de login (força bruta)
#
# IMPORTANTE: alguns desses testes documentam uma VULNERABILIDADE REAL
# e ATUAL do projeto (ex.: não existe limite de tentativas de login).
# Nesses casos, o teste passa descrevendo o comportamento ATUAL do
# sistema — o objetivo é a turma ENXERGAR o problema, não escondê-lo.
# Fica marcado com o comentário "ACHADO DE SEGURANÇA".
#
# COMO RODAR (a partir da raiz do projeto):
#   pytest testes_software/1.4.5_seguranca -v
# ============================================================================


# ------------------------------------------------------------------
# INJEÇÃO DE SQL
# ------------------------------------------------------------------

def test_busca_de_produto_resiste_a_injecao_de_sql(client, criar_admin, login_como, sessao_db):
    """
    Tenta "injetar" SQL malicioso no campo de busca de produtos. Como o
    controller usa Produto.nome.ilike(f"%{busca}%") através do SQLAlchemy
    ORM (que gera consultas parametrizadas por baixo dos panos, e não
    concatena texto na query), a string maliciosa deve ser tratada como
    TEXTO comum — nunca como comando SQL.
    """
    criar_admin(email="admin_seg1@teste.com")
    login_como("admin_seg1@teste.com", "senha123")

    from app.models.produto import Produto
    sessao_db.add(Produto(nome="Produto Legítimo", preco=1, estoque_atual=1))
    sessao_db.commit()

    payloads_maliciosos = [
        "'; DROP TABLE produtos; --",
        "' OR '1'='1",
        "x' UNION SELECT * FROM usuarios --",
    ]

    for payload in payloads_maliciosos:
        resposta = client.get("/produtos/", params={"busca": payload})
        # O sistema não deve travar (erro 500) nem devolver dados que não
        # deveriam aparecer para essa busca.
        assert resposta.status_code == 200
        assert "Produto Legítimo" not in resposta.text

    # A prova definitiva: a tabela "produtos" ainda existe e nosso
    # produto de teste continua lá — o "DROP TABLE" não teve efeito algum.
    produto_ainda_existe = sessao_db.query(Produto).filter_by(nome="Produto Legítimo").first()
    assert produto_ainda_existe is not None


# ------------------------------------------------------------------
# CONTROLE DE ACESSO
# ------------------------------------------------------------------

def test_operador_nao_acessa_gestao_de_usuarios(client, criar_operador, login_como):
    """Rotas de /usuarios são restritas a admin (Depends(get_admin))."""
    criar_operador(email="operador_seg1@teste.com")
    login_como("operador_seg1@teste.com", "senha123")

    resposta = client.get("/usuarios/")
    assert resposta.status_code == 403


def test_operador_nao_cria_categoria(client, criar_operador, login_como):
    criar_operador(email="operador_seg2@teste.com")
    login_como("operador_seg2@teste.com", "senha123")

    resposta = client.post("/categorias/nova", data={"nome": "Categoria Indevida"})
    assert resposta.status_code == 403


def test_visitante_sem_login_nao_acessa_produtos(client):
    """Sem cookie de sessão nenhum, a rota protegida deve recusar acesso."""
    resposta = client.get("/produtos/", follow_redirects=False)
    assert resposta.status_code == 401


# ------------------------------------------------------------------
# ADULTERAÇÃO DE TOKEN JWT (tentativa de forjar login)
# ------------------------------------------------------------------

def test_token_com_assinatura_adulterada_e_rejeitado(client, criar_admin, login_como):
    """
    Pega um token JWT válido e adultera o último caractere (que faz parte
    da assinatura). Um JWT tem 3 partes separadas por ".": cabeçalho,
    payload (dados) e assinatura. Se a assinatura não bater com o
    conteúdo, o servidor DEVE rejeitar o token — senão qualquer pessoa
    poderia editar o próprio token e virar admin.
    """
    criar_admin(email="admin_seg2@teste.com")
    resposta_login = login_como("admin_seg2@teste.com", "senha123")
    token_valido = resposta_login.cookies["access_token"]

    # Troca o último caractere do token (que está dentro da assinatura).
    token_adulterado = token_valido[:-1] + ("A" if token_valido[-1] != "A" else "B")

    client.cookies.set("access_token", token_adulterado)
    resposta = client.get("/produtos/", follow_redirects=False)

    assert resposta.status_code == 401


def test_nao_e_possivel_forjar_token_de_admin_sem_a_chave_secreta(client):
    """
    Simula um atacante que NÃO conhece o SECRET_KEY do servidor (ele fica
    apenas no arquivo .env, nunca é exposto ao cliente) tentando montar
    um token dizendo "role": "admin" na mão, assinado com uma chave
    qualquer "chutada". Isso PRECISA falhar — é a garantia central de que
    o JWT protege o sistema.
    """
    from datetime import datetime, timedelta, timezone
    from jose import jwt

    payload_forjado = {
        "sub": "invasor@fora-do-sistema.com",
        "nome": "Invasor",
        "role": "admin",        # o atacante tenta se autopromover a admin
        "id": 999,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
    }
    # Assina com uma chave que NÃO é a SECRET_KEY real do servidor.
    token_forjado = jwt.encode(payload_forjado, "chave-chutada-pelo-atacante", algorithm="HS256")

    client.cookies.set("access_token", token_forjado)
    resposta = client.get("/usuarios/", follow_redirects=False)

    # decodificar_token() usa a SECRET_KEY real para validar a assinatura;
    # como as chaves não batem, o token é rejeitado com 401 antes mesmo
    # de chegar na checagem de "role".
    assert resposta.status_code == 401


# ------------------------------------------------------------------
# ARMAZENAMENTO DE SENHA
# ------------------------------------------------------------------

def test_senha_nunca_e_armazenada_em_texto_puro(sessao_db, criar_admin):
    """Confirma que o banco guarda um hash bcrypt, não a senha original."""
    senha_original = "MinhaSenhaSecreta123"
    criar_admin(email="admin_seg3@teste.com", senha=senha_original)

    # Busca o usuário de novo, direto do banco, através da fixture
    # "sessao_db" — assim confirmamos o que está REALMENTE gravado,
    # e não apenas o objeto em memória devolvido por criar_admin().
    from app.models.usuarios import Usuario
    usuario = sessao_db.query(Usuario).filter_by(email="admin_seg3@teste.com").first()

    assert usuario.senha_hash != senha_original
    # Hashes bcrypt sempre começam com "$2b$" (ou variações "$2a$"/"$2y$")
    # seguido do "custo" do algoritmo — é assim que dá para reconhecer
    # que o hash foi gerado corretamente pelo passlib/bcrypt.
    assert usuario.senha_hash.startswith(("$2a$", "$2b$", "$2y$"))


def test_cookie_de_sessao_tem_flag_httponly(login_como, criar_admin):
    """
    HttpOnly impede que JavaScript no navegador (ex.: um script malicioso
    injetado por XSS) leia o cookie de sessão via document.cookie — uma
    camada extra de proteção mesmo que exista uma falha de XSS em outro
    lugar do sistema.
    """
    criar_admin(email="admin_seg4@teste.com")
    resposta = login_como("admin_seg4@teste.com", "senha123")

    cabecalho_set_cookie = resposta.headers.get("set-cookie", "")
    assert "HttpOnly" in cabecalho_set_cookie


# ------------------------------------------------------------------
# CROSS-SITE SCRIPTING (XSS)
# ------------------------------------------------------------------

def test_nome_de_produto_com_script_e_escapado_no_html(client, criar_admin, login_como):
    """
    Tenta cadastrar um produto cujo nome é um payload clássico de XSS.
    O Jinja2 (motor de templates usado pelo projeto) faz "autoescape"
    por padrão em arquivos .html, trocando "<" por "&lt;" etc. — então o
    texto malicioso deve aparecer na página como TEXTO visível, e não
    ser interpretado como uma tag <script> executável pelo navegador.
    """
    criar_admin(email="admin_seg5@teste.com")
    login_como("admin_seg5@teste.com", "senha123")

    payload_xss = "<script>alert('roubado')</script>"

    client.post("/produtos/novo", data={
        "nome": payload_xss,
        "preco": "1",
        "estoque_atual": "1",
        "categoria_id": "0",
    })

    resposta = client.get("/produtos/")

    # A tag NÃO deve aparecer "crua" no HTML (isso executaria no navegador).
    assert "<script>alert('roubado')</script>" not in resposta.text
    # A versão escapada (segura) deve estar presente.
    assert "&lt;script&gt;" in resposta.text


# ------------------------------------------------------------------
# ACHADO DE SEGURANÇA: ausência de limite de tentativas de login
# ------------------------------------------------------------------

def test_login_nao_possui_limite_de_tentativas(client, criar_admin):
    """
    ACHADO DE SEGURANÇA (vulnerabilidade real e atual do projeto):

    Este teste NÃO está validando um comportamento correto — ele está
    documentando uma FALHA: o endpoint /auth/login aceita quantas
    tentativas de senha errada quiserem ser feitas, sem bloqueio
    temporário nem CAPTCHA. Isso deixa o sistema vulnerável a ataques de
    força bruta (tentar milhares de senhas até acertar).

    Proposta de exercício para a turma: implementar um limite de
    tentativas (ex.: bloquear por 5 minutos após 5 tentativas erradas
    para o mesmo e-mail) e então ATUALIZAR este teste para verificar
    que, a partir da 6ª tentativa, o sistema passa a recusar o login
    mesmo com a senha CORRETA (bloqueio temporário).
    """
    criar_admin(email="admin_seg6@teste.com", senha="senhaCorreta")

    TENTATIVAS_COM_SENHA_ERRADA = 15
    for _ in range(TENTATIVAS_COM_SENHA_ERRADA):
        resposta = client.post(
            "/auth/login",
            data={"email": "admin_seg6@teste.com", "senha": "senhaErrada"},
        )
        # Hoje, cada tentativa errada simplesmente devolve a página de
        # login de novo (200), sem qualquer penalidade.
        assert resposta.status_code == 200

    # Mesmo depois de 15 tentativas erradas seguidas, o login com a senha
    # certa ainda funciona normalmente — comprovando que NÃO existe
    # bloqueio por tentativas (o comportamento que deveria ser corrigido).
    resposta_final = client.post(
        "/auth/login",
        data={"email": "admin_seg6@teste.com", "senha": "senhaCorreta"},
        follow_redirects=False,
    )
    assert resposta_final.status_code == 302
