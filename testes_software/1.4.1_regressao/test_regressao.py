# ============================================================================
# 1.4.1 TESTE DE REGRESSÃO
# ============================================================================
#
# O QUE É?
# Teste de regressão é reexecutar testes já existentes depois de QUALQUER
# alteração no código (uma correção de bug, uma nova funcionalidade, uma
# refatoração...) para garantir que o que já funcionava continua
# funcionando. O nome vem justamente de "regredir" (voltar a ter um
# problema que já tinha sido resolvido).
#
# COMO USAR ESTE ARQUIVO NA PRÁTICA COM A TURMA:
#   1. Rode a suíte agora e confira que tudo passa (baseline / "foto" do
#      sistema funcionando).
#   2. Peça para um aluno alterar uma regra de negócio, por exemplo trocar
#      a linha "estoque_atual <= 10" em app/models/produto.py para
#      "estoque_atual < 10".
#   3. Rode a suíte de novo. O teste test_estoque_baixo_property vai
#      quebrar — isso é uma regressão sendo PEGA pelo teste automatizado
#      antes de chegar em produção.
#
# COMO RODAR (a partir da raiz do projeto):
#   pytest testes_software/1.4.1_regressao -v
# ============================================================================


# ------------------------------------------------------------------
# TESTES DE CATEGORIA
# ------------------------------------------------------------------

def test_criar_categoria_com_sucesso(client, criar_admin, login_como):
    # Arrange (preparar o cenário): precisamos de um admin logado, pois
    # a rota POST /categorias/nova exige Depends(get_admin).
    criar_admin(email="admin1@teste.com")
    login_como("admin1@teste.com", "senha123")

    # Act (executar a ação testada): envia o formulário de nova categoria.
    resposta = client.post(
        "/categorias/nova",
        data={"nome": "Bebidas"},
        follow_redirects=False,  # queremos inspecionar o redirect, não segui-lo
    )

    # Assert (verificar o resultado esperado):
    # A rota redireciona com 302 para /categorias?criado=ok quando dá certo.
    assert resposta.status_code == 302
    assert resposta.headers["location"] == "/categorias?criado=ok"


def test_nao_permite_categoria_duplicada(client, criar_admin, login_como):
    criar_admin(email="admin2@teste.com")
    login_como("admin2@teste.com", "senha123")

    # Cria a categoria "Bebidas" uma primeira vez.
    client.post("/categorias/nova", data={"nome": "Bebidas"})

    # Tenta criar de novo com o mesmo nome (o controller usa .ilike(), então
    # nem precisa ser exatamente igual — testamos com letras diferentes).
    resposta = client.post("/categorias/nova", data={"nome": "bebidas"})

    # O controller não redireciona nesse caso: ele re-renderiza o formulário
    # com status 400 e a mensagem de erro.
    assert resposta.status_code == 400
    assert "Já existe uma categoria com este nome." in resposta.text


# ------------------------------------------------------------------
# TESTES DE PRODUTO (CRUD principal do controle de estoque)
# ------------------------------------------------------------------

def test_criar_produto_com_sucesso(client, criar_admin, login_como):
    criar_admin(email="admin3@teste.com")
    login_como("admin3@teste.com", "senha123")

    resposta = client.post(
        "/produtos/novo",
        data={
            "nome": "Caneta Azul",
            "preco": "2.50",
            "estoque_atual": "100",
            "categoria_id": "0",  # 0 = sem categoria, conforme o controller
        },
        # Sem isso, o TestClient seguiria o redirect sozinho e a resposta
        # final seria 200 (a página de listagem), escondendo o 302 real.
        follow_redirects=False,
    )

    assert resposta.status_code == 302
    assert resposta.headers["location"] == "/produtos?criado=ok"


def test_nao_permite_produto_duplicado(client, criar_admin, login_como):
    criar_admin(email="admin4@teste.com")
    login_como("admin4@teste.com", "senha123")

    dados_produto = {
        "nome": "Caderno 100 Folhas",
        "preco": "15.90",
        "estoque_atual": "20",
        "categoria_id": "0",
    }

    client.post("/produtos/novo", data=dados_produto)          # 1ª criação: ok
    resposta = client.post("/produtos/novo", data=dados_produto)  # 2ª: deve falhar

    assert resposta.status_code == 400
    assert "Já existe um produto com este nome." in resposta.text


def test_editar_produto_atualiza_dados(client, criar_admin, login_como, sessao_db):
    criar_admin(email="admin5@teste.com")
    login_como("admin5@teste.com", "senha123")

    # Cria o produto original.
    client.post("/produtos/novo", data={
        "nome": "Lapis Preto",
        "preco": "1.00",
        "estoque_atual": "50",
        "categoria_id": "0",
    })

    # Descobre o id do produto criado consultando a listagem em JSON seria
    # o ideal, mas essa aplicação usa HTML. Para o teste, buscamos o produto
    # direto no banco através da fixture "sessao_db" (mais simples e mais
    # rápido do que fazer parsing de HTML).
    from app.models.produto import Produto

    produto = sessao_db.query(Produto).filter_by(nome="Lapis Preto").first()
    produto_id = produto.id

    # Edita o preço e o estoque do produto.
    resposta = client.post(
        f"/produtos/{produto_id}/editar",
        data={
            "nome": "Lapis Preto",
            "preco": "1.50",           # preço alterado
            "estoque_atual": "5",      # estoque alterado (fica "baixo")
            "categoria_id": "0",
        },
        follow_redirects=False,
    )

    assert resposta.status_code == 302

    # Confere no banco que os valores realmente mudaram. Como a sessão
    # "sessao_db" já leu esse registro antes, pedimos um refresh para
    # buscar os dados mais recentes do banco (senão ela devolveria os
    # dados "em cache" da primeira consulta).
    sessao_db.refresh(produto)
    assert produto.preco == 1.50
    assert produto.estoque_atual == 5


def test_desativar_produto_oculta_da_listagem(client, criar_admin, login_como, sessao_db):
    criar_admin(email="admin6@teste.com")
    login_como("admin6@teste.com", "senha123")

    client.post("/produtos/novo", data={
        "nome": "Borracha Branca",
        "preco": "1.20",
        "estoque_atual": "30",
        "categoria_id": "0",
    })

    from app.models.produto import Produto

    produto_id = sessao_db.query(Produto).filter_by(nome="Borracha Branca").first().id

    # Desativa o produto (a aplicação nunca deleta produtos, só marca
    # ativo=False, para preservar histórico).
    client.post(f"/produtos/{produto_id}/desativar")

    # A listagem só mostra produtos com ativo == True, então o produto
    # desativado não deve aparecer no HTML retornado.
    resposta_listagem = client.get("/produtos")
    assert "Borracha Branca" not in resposta_listagem.text


def test_buscar_produto_por_nome(client, criar_admin, login_como):
    criar_admin(email="admin7@teste.com")
    login_como("admin7@teste.com", "senha123")

    client.post("/produtos/novo", data={
        "nome": "Mochila Escolar", "preco": "80", "estoque_atual": "10", "categoria_id": "0"
    })
    client.post("/produtos/novo", data={
        "nome": "Estojo Simples", "preco": "12", "estoque_atual": "40", "categoria_id": "0"
    })

    # Busca só por "mochi" (case-insensitive, igual o filtro ilike do controller).
    resposta = client.get("/produtos", params={"busca": "mochi"})

    assert "Mochila Escolar" in resposta.text
    assert "Estojo Simples" not in resposta.text


# ------------------------------------------------------------------
# TESTES DE CONTROLE DE ACESSO (operador x admin)
# ------------------------------------------------------------------
# Esses testes são especialmente importantes numa suíte de regressão:
# regras de permissão costumam ser "quebradas" sem querer quando alguém
# mexe nas rotas.

def test_operador_nao_pode_cadastrar_produto(client, criar_operador, login_como):
    criar_operador(email="operador1@teste.com")
    login_como("operador1@teste.com", "senha123")

    # A rota GET /produtos/novo exige Depends(get_admin); um operador comum
    # deve ser barrado com 403 Forbidden.
    resposta = client.get("/produtos/novo")
    assert resposta.status_code == 403


def test_operador_consegue_ver_listagem_de_produtos(client, criar_operador, login_como):
    criar_operador(email="operador2@teste.com")
    login_como("operador2@teste.com", "senha123")

    # Já a listagem (GET /produtos) só exige estar logado, não ser admin.
    resposta = client.get("/produtos")
    assert resposta.status_code == 200


# ------------------------------------------------------------------
# TESTES DE LOGIN / LOGOUT
# ------------------------------------------------------------------

def test_login_com_senha_errada_nao_autentica(client, criar_admin, login_como):
    criar_admin(email="admin8@teste.com", senha="senhaCorreta")

    resposta = login_como("admin8@teste.com", "senhaErrada")

    # Login errado não redireciona (fica na própria página com erro) e
    # não deve gerar cookie de sessão.
    assert resposta.status_code == 200
    assert "access_token" not in resposta.cookies


def test_login_com_sucesso_gera_cookie(client, criar_admin, login_como):
    criar_admin(email="admin9@teste.com", senha="senhaCorreta")

    resposta = login_como("admin9@teste.com", "senhaCorreta")

    assert resposta.status_code == 302
    assert "access_token" in resposta.cookies


# ------------------------------------------------------------------
# TESTE DE REGRA DE NEGÓCIO (propriedade calculada do model)
# ------------------------------------------------------------------

def test_estoque_baixo_property():
    # Esse teste nem precisa do banco de dados: testa diretamente a regra
    # de negócio "estoque_atual <= 10" definida em app/models/produto.py.
    from app.models.produto import Produto

    produto_estoque_baixo = Produto(nome="X", preco=1, estoque_atual=10)
    produto_estoque_ok = Produto(nome="Y", preco=1, estoque_atual=11)

    assert produto_estoque_baixo.estoque_baixo is True
    assert produto_estoque_ok.estoque_baixo is False
