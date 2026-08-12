# ============================================================================
# ESTRESSE CONTRA UM SERVIDOR DE VERDADE (fora do pytest)
# ============================================================================
#
# O test_estresse.py desta pasta roda tudo "em memória" (TestClient), o que
# é ótimo para automatizar em CI, mas não passa por rede de verdade nem
# testa o servidor uvicorn real.
#
# Este script complementa o teste automatizado: ele dispara requisições
# HTTP reais contra o servidor rodando em http://127.0.0.1:8000. É a forma
# mais próxima de um teste de estresse "de verdade" que dá para fazer só
# com Python puro (sem instalar ferramentas externas como Locust ou k6).
#
# COMO USAR:
#   1. Em um terminal, suba o servidor de verdade:
#        python -m uvicorn app.main:app --reload
#   2. Em OUTRO terminal, rode este script:
#        python testes_software/1.4.2_estresse/estresse_servidor_real.py
#
# ATENÇÃO: isso vai gerar carga real no banco.db de desenvolvimento. Não
# rode isso apontando para um servidor de produção.
# ============================================================================

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests  # pip install requests (não vem com o requirements-teste.txt)

URL_BASE = "http://127.0.0.1:8000"
QUANTIDADE_DE_REQUISICOES = 200
REQUISICOES_SIMULTANEAS = 25  # "usuários" batendo na API ao mesmo tempo


def fazer_requisicao(numero):
    inicio = time.perf_counter()
    try:
        resposta = requests.get(f"{URL_BASE}/", timeout=5)
        duracao_ms = (time.perf_counter() - inicio) * 1000
        return resposta.status_code, duracao_ms
    except requests.exceptions.RequestException as erro:
        duracao_ms = (time.perf_counter() - inicio) * 1000
        return f"ERRO: {erro}", duracao_ms


def main():
    print(f"Disparando {QUANTIDADE_DE_REQUISICOES} requisições "
          f"({REQUISICOES_SIMULTANEAS} simultâneas) contra {URL_BASE} ...")

    resultados = []
    with ThreadPoolExecutor(max_workers=REQUISICOES_SIMULTANEAS) as executor:
        tarefas = [executor.submit(fazer_requisicao, n) for n in range(QUANTIDADE_DE_REQUISICOES)]
        for tarefa in as_completed(tarefas):
            resultados.append(tarefa.result())

    sucesso = [r for r in resultados if r[0] == 200]
    falha = [r for r in resultados if r[0] != 200]
    tempos = [r[1] for r in sucesso]

    print("\n===== RESUMO DO TESTE DE ESTRESSE =====")
    print(f"Sucesso: {len(sucesso)}/{QUANTIDADE_DE_REQUISICOES}")
    print(f"Falhas : {len(falha)}/{QUANTIDADE_DE_REQUISICOES}")
    if tempos:
        print(f"Tempo médio de resposta (sucesso): {sum(tempos)/len(tempos):.1f} ms")
        print(f"Tempo máximo de resposta (sucesso): {max(tempos):.1f} ms")
    if falha:
        print("\nExemplos de falha:")
        for status, _ in falha[:5]:
            print(f"  - {status}")


if __name__ == "__main__":
    main()
