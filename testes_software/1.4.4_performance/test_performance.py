# ============================================================================
# 1.4.4 TESTE DE PERFORMANCE
# ============================================================================
#
# O QUE É?
# Teste de performance mede o TEMPO que o sistema leva para responder em
# condições de uso NORMAL/esperado (diferente do teste de estresse, que
# leva o sistema além do limite). Perguntas típicas: "a página carrega
# em menos de 1 segundo?", "o login demora muito por causa do hash de
# senha?", "a listagem fica lenta conforme o número de produtos cresce?".
#
# NESTE ARQUIVO
# Usamos apenas a biblioteca padrão do Python: "time.perf_counter()" para
# cronometrar e "statistics" para calcular média/percentis de várias
# medições (uma única medição pode enganar por causa de uma variação
# pontual do computador).
#
# COMO RODAR (a partir da raiz do projeto):
#   pytest testes_software/1.4.4_performance -v -s
# ============================================================================

import statistics
import time


def medir_tempo_ms(funcao, *args, **kwargs):
    """
    Função auxiliar: executa "funcao(*args, **kwargs)", mede quanto tempo
    levou em milissegundos e devolve (resultado, tempo_em_ms).

    perf_counter() é recomendado para medir performance porque tem alta
    precisão e não é afetado por mudanças no relógio do sistema
    operacional (diferente de time.time()).
    """
    inicio = time.perf_counter()
    resultado = funcao(*args, **kwargs)
    fim = time.perf_counter()
    tempo_ms = (fim - inicio) * 1000
    return resultado, tempo_ms


# ------------------------------------------------------------------
# PERFORMANCE DE PÁGINAS SIMPLES
# ------------------------------------------------------------------

def test_pagina_inicial_responde_rapido(client):
    """
    A página inicial ("/") não consulta produtos nem faz nada pesado —
    deve responder quase instantaneamente. Um limite de 500ms é bem
    generoso (numa aplicação real em produção o ideal seria bem menos),
    mas evita que o teste falhe só por lentidão do computador/CI.
    """
    LIMITE_MS = 500

    resposta, tempo_ms = medir_tempo_ms(client.get, "/")

    print(f"\n[PERFORMANCE] GET / levou {tempo_ms:.1f} ms (limite: {LIMITE_MS} ms)")

    assert resposta.status_code == 200
    assert tempo_ms < LIMITE_MS, f"Página inicial demorou {tempo_ms:.1f} ms (limite {LIMITE_MS} ms)"


# ------------------------------------------------------------------
# PERFORMANCE DA LISTAGEM DE PRODUTOS COM VOLUME DE DADOS
# ------------------------------------------------------------------

def test_listagem_de_produtos_com_muitos_registros(client, criar_admin, login_como, sessao_db):
    """
    Cadastra um volume razoável de produtos (200) diretamente no banco
    (mais rápido que passar pela rota HTTP de cadastro) e mede o tempo
    médio de várias chamadas à listagem — que faz uma consulta com
    JOIN implícito de categoria e ORDER BY nome.
    """
    criar_admin(email="admin_performance@teste.com")
    login_como("admin_performance@teste.com", "senha123")

    from app.models.produto import Produto

    QUANTIDADE_DE_PRODUTOS = 200
    for i in range(QUANTIDADE_DE_PRODUTOS):
        sessao_db.add(Produto(nome=f"Produto Performance {i:04d}", preco=9.9, estoque_atual=5))
    sessao_db.commit()

    REPETICOES = 20
    LIMITE_MEDIO_MS = 300

    tempos = []
    for _ in range(REPETICOES):
        resposta, tempo_ms = medir_tempo_ms(client.get, "/produtos/")
        assert resposta.status_code == 200
        tempos.append(tempo_ms)

    media = statistics.mean(tempos)
    # quantiles(tempos, n=100)[94] ~= percentil 95: 95% das respostas
    # foram mais rápidas que esse valor. É uma métrica mais realista que
    # a média, pois mostra o "pior caso comum" (não o pior caso absoluto).
    percentil_95 = statistics.quantiles(tempos, n=100)[94]

    print(
        f"\n[PERFORMANCE] GET /produtos/ com {QUANTIDADE_DE_PRODUTOS} produtos "
        f"({REPETICOES} repetições): média={media:.1f} ms | p95={percentil_95:.1f} ms"
    )

    assert media < LIMITE_MEDIO_MS, (
        f"Tempo médio de listagem ({media:.1f} ms) acima do limite ({LIMITE_MEDIO_MS} ms)"
    )


# ------------------------------------------------------------------
# PERFORMANCE DO LOGIN (custo do hash de senha com bcrypt)
# ------------------------------------------------------------------

def test_login_tem_tempo_de_resposta_aceitavel(client, criar_admin):
    """
    O login usa bcrypt para conferir a senha, que é PROPOSITALMENTE lento
    (isso é uma característica de segurança: dificulta ataques de força
    bruta — veja o arquivo de teste de segurança, pasta 1.4.5). Ainda
    assim, o tempo de resposta para o usuário precisa ficar dentro de um
    limite aceitável de UX (experiência do usuário).
    """
    criar_admin(email="admin_login_performance@teste.com", senha="senha123")

    LIMITE_MS = 1000  # 1 segundo é um limite bem confortável para bcrypt

    resposta, tempo_ms = medir_tempo_ms(
        client.post,
        "/auth/login",
        data={"email": "admin_login_performance@teste.com", "senha": "senha123"},
        follow_redirects=False,
    )

    print(f"\n[PERFORMANCE] POST /auth/login levou {tempo_ms:.1f} ms (limite: {LIMITE_MS} ms)")

    assert resposta.status_code == 302
    assert tempo_ms < LIMITE_MS, f"Login demorou {tempo_ms:.1f} ms (limite {LIMITE_MS} ms)"
