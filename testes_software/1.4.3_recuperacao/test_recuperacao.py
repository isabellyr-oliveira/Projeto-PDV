# ============================================================================
# 1.4.3 TESTE DE RECUPERAÇÃO
# ============================================================================
#
# O QUE É?
# Teste de recuperação verifica se o sistema consegue voltar a funcionar
# corretamente depois de uma falha: uma queda de conexão com o banco, um
# erro inesperado no meio de uma operação, o processo do servidor sendo
# reiniciado, etc. Duas perguntas centrais:
#   1. O sistema volta a responder depois da falha (ou trava para sempre)?
#   2. Os dados continuam íntegros/consistentes depois da falha (ou ficam
#      corrompidos/pela metade)?
#
# IMPORTANTE PARA A TURMA:
# Nem toda falha pode ser simulada de forma automatizada com Python puro
# (por exemplo: "o quê acontece se a energia cair no meio de uma escrita
# no disco?"). Este arquivo cobre o que É possível simular via código:
# token corrompido, erro inesperado durante um commit no banco, e se os
# dados sobrevivem a um "reinício" do processo (a aplicação sendo criada
# de novo, como aconteceria depois de um `systemctl restart` real).
#
# O passo a passo das simulações que precisam ser feitas manualmente
# (matar o processo do servidor, restaurar um backup do banco) está no
# README.md desta pasta.
#
# COMO RODAR (a partir da raiz do projeto):
#   pytest testes_software/1.4.3_recuperacao -v
# ============================================================================

import os

import pytest


# ------------------------------------------------------------------
# RECUPERAÇÃO DE UMA SESSÃO INVÁLIDA (token corrompido/adulterado)
# ------------------------------------------------------------------

def test_sistema_recusa_token_corrompido_sem_travar(client):
    """
    Simula um usuário cujo cookie de sessão foi corrompido (ex.: o
    navegador travou no meio da gravação do cookie, ou alguém tentou
    adulterar o valor manualmente).

    O comportamento "saudável" de recuperação aqui é: o sistema detecta
    que o token é inválido e responde com 401 (ou redireciona para o
    login) — sem quebrar (erro 500) e sem travar o servidor.
    """
    client.cookies.set("access_token", "isto-nao-e-um-jwt-valido")

    # Usamos "/produtos/" (com barra no final) para bater direto na rota
    # de listagem. Sem a barra, o FastAPI faz um redirect 307 automático
    # para "/produtos/" ANTES de verificar o login, o que atrapalharia
    # a checagem de status_code == 401 feita logo abaixo.
    resposta = client.get("/produtos/", follow_redirects=False)

    # Não pode ser 500 (erro interno) nem travar — tem que ser um erro
    # tratado (401 Unauthorized), pois get_usuario_logado() captura
    # JWTError e converte em HTTPException 401.
    assert resposta.status_code == 401


def test_sistema_recusa_token_expirado_sem_travar(client, criar_admin):
    """
    Simula um token JWT que já expirou (ex.: o usuário deixou a aba aberta
    por mais tempo do que o ACCESS_TOKEN_EXPIRE_MINUTE configurado).
    """
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    from app.auth import SECRET_KEY, ALGORITHM

    admin = criar_admin(email="admin_recuperacao@teste.com")

    # Cria manualmente um token com data de expiração NO PASSADO.
    payload = {
        "sub": admin.email,
        "nome": admin.nome,
        "role": admin.role,
        "id": admin.id,
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5),  # expirou há 5 min
    }
    token_expirado = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    client.cookies.set("access_token", token_expirado)

    # Usamos "/produtos/" (com barra no final) para bater direto na rota
    # de listagem. Sem a barra, o FastAPI faz um redirect 307 automático
    # para "/produtos/" ANTES de verificar o login, o que atrapalharia
    # a checagem de status_code == 401 feita logo abaixo.
    resposta = client.get("/produtos/", follow_redirects=False)

    # jose.jwt.decode() valida a expiração automaticamente e levanta
    # JWTError, que a aplicação converte em 401 — recuperação correta.
    assert resposta.status_code == 401


# ------------------------------------------------------------------
# RECUPERAÇÃO APÓS FALHA NO MEIO DE UMA ESCRITA NO BANCO
# ------------------------------------------------------------------

def test_dados_nao_ficam_corrompidos_se_commit_falhar(client, criar_admin, login_como, sessao_db, monkeypatch):
    """
    Simula uma falha "no pior momento possível": o banco de dados cai
    (ou a conexão é perdida) bem na hora do db.commit(), depois que o
    objeto Categoria já foi adicionado à sessão (db.add()).

    O que queremos verificar: mesmo com a falha, a categoria NÃO deve
    aparecer como criada com sucesso (ou seja, sem dado "pela metade").
    Isso confirma que a aplicação depende do commit para persistir --
    sem commit bem-sucedido, nada fica salvo, o que é o comportamento
    correto de recuperação de uma transação de banco de dados.
    """
    criar_admin(email="admin_recuperacao2@teste.com")
    login_como("admin_recuperacao2@teste.com", "senha123")

    from sqlalchemy.orm import Session as SessionSQLAlchemy

    commit_original = SessionSQLAlchemy.commit
    chamadas = {"total": 0}

    def commit_que_falha_uma_vez(self):
        # Na primeira chamada de commit, simula a "queda" do banco.
        chamadas["total"] += 1
        if chamadas["total"] == 1:
            raise Exception("Falha simulada de conexão com o banco de dados")
        return commit_original(self)

    monkeypatch.setattr(SessionSQLAlchemy, "commit", commit_que_falha_uma_vez)

    # A rota não trata esse erro (não existe try/except no controller),
    # então o FastAPI propaga a exceção. Com TestClient, isso aparece
    # como uma exceção Python na hora do request — representando bem o
    # "erro 500" que o usuário veria em produção.
    with pytest.raises(Exception, match="Falha simulada"):
        client.post("/categorias/nova", data={"nome": "Categoria Que Deveria Falhar"})

    # Remove o monkeypatch manualmente antes de consultar o banco, para
    # a verificação abaixo usar um commit "de verdade".
    monkeypatch.undo()

    from app.models.categoria import Categoria
    categoria = sessao_db.query(Categoria).filter_by(nome="Categoria Que Deveria Falhar").first()

    # Ponto central do teste de recuperação: a falha não deixou "lixo"
    # no banco. Os dados continuam consistentes.
    assert categoria is None


# ------------------------------------------------------------------
# RECUPERAÇÃO APÓS "REINÍCIO" DO SISTEMA (os dados sobrevivem?)
# ------------------------------------------------------------------

def test_dados_persistem_apos_reiniciar_conexao_com_banco(tmp_path):
    """
    Simula o cenário: o servidor é reiniciado (ex.: `systemctl restart`,
    o processo travou e o supervisor subiu ele de novo, houve deploy de
    uma nova versão). A pergunta de um teste de recuperação aqui é:
    os dados gravados ANTES do reinício continuam lá DEPOIS dele?

    Como o banco é um arquivo SQLite em disco (não está em memória),
    "reiniciar o servidor" não deveria apagar nada — simulamos isso
    criando duas conexões (engines) totalmente independentes para o
    MESMO arquivo, uma representando o "antes" e outra o "depois".
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.database import Base
    from app.models.categoria import Categoria

    caminho_arquivo = tmp_path / "banco_recuperacao.db"
    url = f"sqlite:///{caminho_arquivo}"

    # --- "Antes de reiniciar": cria a categoria e desliga a conexão ---
    engine_antes = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine_antes)
    SessionAntes = sessionmaker(bind=engine_antes)

    db = SessionAntes()
    db.add(Categoria(nome="Sobrevive ao Reinício"))
    db.commit()
    db.close()
    engine_antes.dispose()  # simula o processo do servidor sendo encerrado

    # --- "Depois de reiniciar": abre uma conexão NOVA e independente ---
    engine_depois = create_engine(url, connect_args={"check_same_thread": False})
    SessionDepois = sessionmaker(bind=engine_depois)

    db2 = SessionDepois()
    categoria = db2.query(Categoria).filter_by(nome="Sobrevive ao Reinício").first()
    db2.close()
    engine_depois.dispose()

    assert categoria is not None
    assert categoria.nome == "Sobrevive ao Reinício"
