# ============================================================================
# 1.4.2 TESTE DE ESTRESSE
# ============================================================================
#
# O QUE É?
# Teste de estresse joga o sistema além do uso normal (muitas requisições
# ao mesmo tempo, muitos dados, pouco tempo de espera) para descobrir COMO
# ele se comporta quando é sobrecarregado: ele fica lento? Devolve erro
# para o usuário de forma educada? Ou trava/derruba o servidor inteiro?
#
# Diferença para o teste de performance (pasta 1.4.4): performance mede
# "quão rápido" o sistema responde em uso normal/esperado; estresse mede
# "o que acontece" quando o sistema é levado ao limite (ou além dele).
#
# NESTE ARQUIVO
# Usamos a biblioteca padrão "concurrent.futures.ThreadPoolExecutor" para
# disparar várias requisições HTTP ao mesmo tempo contra a aplicação
# (em memória, via TestClient) e observamos quantas tiveram sucesso e
# quantas falharam.
#
# COMO RODAR (a partir da raiz do projeto):
#   pytest testes_software/1.4.2_estresse -v -s
#   (o "-s" mostra os prints com o resumo do teste de estresse)
# ============================================================================

from concurrent.futures import ThreadPoolExecutor, as_completed


def test_estresse_leitura_simultanea_de_produtos(client, criar_admin, login_como, sessao_db):
    """
    Simula várias "pessoas" acessando a listagem de produtos ao mesmo
    tempo (ex.: vários caixas do PDV consultando o estoque simultaneamente).
    """
    criar_admin(email="admin_estresse1@teste.com")
    login_como("admin_estresse1@teste.com", "senha123")

    # Cadastra alguns produtos para a listagem não ficar vazia.
    from app.models.produto import Produto
    for i in range(20):
        sessao_db.add(Produto(nome=f"Produto Estresse {i}", preco=1.0, estoque_atual=10))
    sessao_db.commit()

    QUANTIDADE_DE_REQUISICOES = 100  # simula 100 acessos "ao mesmo tempo"

    def fazer_uma_requisicao(_):
        """Cada thread executa esta função: faz 1 requisição e devolve o status."""
        try:
            resposta = client.get("/produtos")
            return resposta.status_code
        except Exception as erro:
            # Se o servidor "explodir" sob estresse, capturamos o erro em
            # vez de deixar a thread simplesmente sumir sem explicação.
            return f"ERRO: {erro}"

    resultados = []
    # ThreadPoolExecutor(max_workers=20) => até 20 requisições rodando
    # de verdade em paralelo (threads), mesmo pedindo 100 no total.
    with ThreadPoolExecutor(max_workers=20) as executor:
        tarefas = [executor.submit(fazer_uma_requisicao, i) for i in range(QUANTIDADE_DE_REQUISICOES)]
        for tarefa in as_completed(tarefas):
            resultados.append(tarefa.result())

    sucesso = sum(1 for r in resultados if r == 200)
    falha = len(resultados) - sucesso

    print(f"\n[ESTRESSE - LEITURA] {sucesso}/{QUANTIDADE_DE_REQUISICOES} OK | {falha} falharam")

    # Critério de aceite do teste de estresse: não exigimos 100% de sucesso
    # (sob estresse real, algumas falhas são esperadas), mas pelo menos
    # 90% das leituras devem funcionar. Esse número é um "critério de
    # qualidade" definido pela equipe — ajuste conforme a necessidade.
    taxa_de_sucesso = sucesso / QUANTIDADE_DE_REQUISICOES
    assert taxa_de_sucesso >= 0.90, (
        f"Taxa de sucesso muito baixa sob estresse: {taxa_de_sucesso:.0%}"
    )


def test_estresse_cadastros_simultaneos_de_categoria(client, criar_admin, login_como):
    """
    Simula vários administradores tentando cadastrar categorias DIFERENTES
    ao mesmo tempo. Esse cenário costuma revelar problemas de concorrência
    em bancos de dados simples como SQLite, que trava (lock) quando duas
    escritas tentam acontecer ao mesmo tempo — por isso este projeto, que
    usa SQLite, não é recomendado para produção com muitos usuários
    simultâneos (um banco como PostgreSQL lida melhor com isso).
    """
    criar_admin(email="admin_estresse2@teste.com")
    login_como("admin_estresse2@teste.com", "senha123")

    QUANTIDADE_DE_CATEGORIAS = 30

    def criar_categoria_numero(numero):
        try:
            resposta = client.post(
                "/categorias/nova",
                data={"nome": f"Categoria Estresse {numero}"},
                follow_redirects=False,
            )
            return resposta.status_code
        except Exception as erro:
            return f"ERRO: {erro}"

    resultados = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        tarefas = [executor.submit(criar_categoria_numero, n) for n in range(QUANTIDADE_DE_CATEGORIAS)]
        for tarefa in as_completed(tarefas):
            resultados.append(tarefa.result())

    sucesso = sum(1 for r in resultados if r == 302)
    erros_de_lock = sum(1 for r in resultados if isinstance(r, str) and "lock" in r.lower())

    print(
        f"\n[ESTRESSE - ESCRITA] {sucesso}/{QUANTIDADE_DE_CATEGORIAS} criadas | "
        f"{erros_de_lock} falharam por lock do banco (SQLite)"
    )

    # Aqui o objetivo pedagógico é DISCUTIR o resultado com a turma, não
    # necessariamente exigir 100%. Por isso o teste só falha em um cenário
    # bem ruim (menos da metade das categorias foi criada).
    assert sucesso >= QUANTIDADE_DE_CATEGORIAS * 0.5, (
        "Menos da metade das categorias foi criada sob concorrência — "
        "investigue possíveis problemas de lock no banco."
    )
