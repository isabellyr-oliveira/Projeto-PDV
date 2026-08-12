# ============================================================================
# conftest.py
#
# Este arquivo é lido AUTOMATICAMENTE pelo pytest antes de qualquer teste
# rodar. É aqui que preparamos o "cenário" que todos os testes das pastas
# 1.4.1 até 1.4.6 vão usar: um banco de dados de TESTE (separado do banco
# de produção "banco.db") e um cliente HTTP capaz de "conversar" com a
# nossa aplicação FastAPI sem precisar rodar o uvicorn de verdade.
#
# Tudo que for definido aqui como "fixture" (uma função decorada com
# @pytest.fixture) fica disponível para qualquer teste dentro da pasta
# testes_software/, em qualquer subpasta, sem precisar importar nada.
# ============================================================================

import os
import sys

# ----------------------------------------------------------------------------
# 1. Garantir que o Python "enxerga" a pasta raiz do projeto
# ----------------------------------------------------------------------------
# Este arquivo está em .../projeto-aapm-seducb/testes_software/conftest.py
# Precisamos que a pasta .../projeto-aapm-seducb esteja no sys.path para
# que "import app.main" funcione, não importa de onde o pytest é chamado.
CAMINHO_RAIZ_PROJETO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if CAMINHO_RAIZ_PROJETO not in sys.path:
    sys.path.insert(0, CAMINHO_RAIZ_PROJETO)

# ----------------------------------------------------------------------------
# 2. Definir variáveis de ambiente ANTES de importar o app
# ----------------------------------------------------------------------------
# O app/database.py e o app/auth.py leem variáveis de ambiente (DATABASE_URL,
# SECRET_KEY, etc.) no momento em que são importados. Se não definirmos essas
# variáveis agora, o app tentaria usar o banco.db de PRODUÇÃO — e os testes
# iriam bagunçar os dados reais do sistema. Por isso apontamos para um banco
# SQLite exclusivo de teste.
#
# os.environ.setdefault só define o valor se ele AINDA não existir, então se
# você já tiver essas variáveis configuradas no ambiente, elas são respeitadas.
CAMINHO_BANCO_TESTE = os.path.join(os.path.dirname(__file__), "banco_teste.db")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{CAMINHO_BANCO_TESTE}")
os.environ.setdefault("SECRET_KEY", "chave-secreta-usada-somente-nos-testes")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTE", "60")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Só podemos importar o app DEPOIS de configurar as variáveis de ambiente
# acima, senão ele já teria lido o banco de produção.
from app.main import app
from app.database import Base, get_db
from app.models.usuarios import Usuario
from app.models.categoria import Categoria
from app.models.produto import Produto
from app.auth import hash_senha

# ----------------------------------------------------------------------------
# 3. Criar um "motor" (engine) de banco de dados exclusivo para os testes
# ----------------------------------------------------------------------------
engine_teste = create_engine(
    f"sqlite:///{CAMINHO_BANCO_TESTE}",
    connect_args={"check_same_thread": False},  # necessário para SQLite + FastAPI
)

SessionTeste = sessionmaker(autoflush=False, autocommit=False, bind=engine_teste)


def _get_db_teste():
    """
    Mesma ideia da função get_db() em app/database.py, mas usando o
    SessionTeste (banco de teste) em vez do Session de produção.
    """
    db = SessionTeste()
    try:
        yield db
    finally:
        db.close()


# ----------------------------------------------------------------------------
# 4. Substituir a dependência get_db do FastAPI pela versão de teste
# ----------------------------------------------------------------------------
# Toda rota do app usa "db: Session = Depends(get_db)". Com dependency_overrides
# nós dizemos ao FastAPI: "sempre que alguém pedir get_db, entregue
# _get_db_teste no lugar". Isso é feito uma única vez, no import deste arquivo.
app.dependency_overrides[get_db] = _get_db_teste


# ----------------------------------------------------------------------------
# 5. Fixture que cria/derruba as tabelas do banco de teste
# ----------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def preparar_banco_de_teste():
    """
    scope="session"  -> roda 1 vez só, no início de toda a execução do pytest.
    autouse=True     -> roda automaticamente, nenhum teste precisa "pedir" ela.

    Cria todas as tabelas (usuarios, categorias, produtos) no banco de teste
    antes do primeiro teste rodar, e apaga tudo no final para não deixar
    lixo no repositório.
    """
    Base.metadata.create_all(bind=engine_teste)  # cria as tabelas
    yield                                        # -> aqui os testes rodam
    Base.metadata.drop_all(bind=engine_teste)    # limpa as tabelas
    engine_teste.dispose()                       # fecha as conexões
    if os.path.exists(CAMINHO_BANCO_TESTE):
        os.remove(CAMINHO_BANCO_TESTE)           # apaga o arquivo banco_teste.db


@pytest.fixture(autouse=True)
def limpar_tabelas_entre_testes():
    """
    Roda ANTES de cada função de teste (autouse=True = automático).

    Sem isso, um teste que cria o produto "Caneta" deixaria esse registro
    para o próximo teste, e o segundo teste poderia falhar por achar que
    "Caneta" já existe (erro de duplicidade) mesmo sem ter criado nada.
    Apagar as tabelas a cada teste garante que cada teste começa "do zero",
    o que é uma boa prática de testes automatizados (testes independentes).
    """
    yield  # o teste roda primeiro...
    db = SessionTeste()
    try:
        # Apaga na ordem certa por causa da chave estrangeira produto -> categoria
        db.query(Produto).delete()
        db.query(Categoria).delete()
        db.query(Usuario).delete()
        db.commit()
    finally:
        db.close()


# ----------------------------------------------------------------------------
# 6. Fixture do cliente HTTP de testes
# ----------------------------------------------------------------------------
@pytest.fixture
def client():
    """
    TestClient simula um navegador conversando com o FastAPI, mas tudo
    acontece em memória (não sobe um servidor de verdade na porta 8000).
    Cada teste que usar o parâmetro "client" recebe um cliente novo.
    """
    with TestClient(app) as c:
        yield c


# ----------------------------------------------------------------------------
# 7. Fixtures auxiliares para criar usuários e fazer login
# ----------------------------------------------------------------------------
def _criar_usuario_no_banco(nome, email, senha, role):
    """Função interna: insere um usuário direto no banco (sem passar pela rota)."""
    db = SessionTeste()
    try:
        usuario = Usuario(
            nome=nome,
            email=email,
            senha_hash=hash_senha(senha),
            role=role,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario
    finally:
        db.close()


@pytest.fixture
def criar_admin():
    """
    Fixture "fábrica": em vez de devolver um valor pronto, devolve uma
    FUNÇÃO. Assim cada teste pode chamar criar_admin() e escolher o
    e-mail/senha se quiser, sem duplicar código.
    """
    def _fabrica(nome="Admin Teste", email="admin@teste.com", senha="senha123"):
        return _criar_usuario_no_banco(nome, email, senha, role="admin")
    return _fabrica


@pytest.fixture
def criar_operador():
    def _fabrica(nome="Operador Teste", email="operador@teste.com", senha="senha123"):
        return _criar_usuario_no_banco(nome, email, senha, role="operador")
    return _fabrica


@pytest.fixture
def sessao_db():
    """
    Dá acesso direto a uma sessão do banco de TESTE dentro do próprio teste.
    Útil quando o teste precisa "espiar" o banco (ex.: pegar o id de um
    produto recém-criado) sem precisar interpretar o HTML da resposta.
    """
    db = SessionTeste()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def login_como(client):
    """
    Fixture fábrica que faz o POST /auth/login de verdade (passando pela
    rota real, igual um usuário faria no navegador) e devolve o mesmo
    "client" já autenticado — o cookie "access_token" fica guardado
    automaticamente dentro do TestClient para as próximas requisições.
    """
    def _fazer_login(email, senha):
        resposta = client.post(
            "/auth/login",
            data={"email": email, "senha": senha},
            follow_redirects=False,
        )
        return resposta
    return _fazer_login
