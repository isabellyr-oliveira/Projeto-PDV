# ============================================================================
# 1.4.6 TESTE PARALELO
# ============================================================================
#
# O QUE É?
# Teste paralelo (também chamado de "teste em paralelo" ou, no mercado,
# de "shadow testing" / "comparison testing") consiste em rodar DUAS
# versões de um mesmo sistema (ou de uma mesma regra de negócio) AO
# MESMO TEMPO, com EXATAMENTE as mesmas entradas, e comparar as saídas.
# Se as saídas forem diferentes, é sinal de que a versão nova mudou um
# comportamento — de propósito (uma melhoria) ou sem querer (um bug).
#
# É muito usado quando uma empresa está migrando um sistema antigo para
# um novo e precisa ter certeza de que o novo se comporta igual (ou
# melhor, mas de forma conhecida) antes de desligar o antigo de vez.
#
# POR QUE ESTE ARQUIVO É DIFERENTE DOS OUTROS
# O projeto de vocês ainda não tem uma "versão antiga" de verdade para
# comparar — ele é a única versão que existe! Por isso, este arquivo é
# um EXEMPLO DIDÁTICO: criamos duas implementações da mesma regra de
# negócio (cálculo de troco de uma venda no PDV) só para demonstrar a
# TÉCNICA. O README.md desta pasta explica como aplicar o mesmo
# raciocínio quando o projeto realmente tiver duas versões para comparar
# (esse é o cenário mais comum de teste paralelo, e normalmente não dá
# para automatizar dentro de um único repositório/pytest — envolve dois
# sistemas rodando de verdade).
#
# COMO RODAR (a partir da raiz do projeto):
#   pytest testes_software/1.4.6_paralelo -v -s
# ============================================================================

from concurrent.futures import ThreadPoolExecutor


# ------------------------------------------------------------------
# "VERSÃO ANTIGA" do cálculo de troco (com um bug de arredondamento)
# ------------------------------------------------------------------
def calcular_troco_versao_antiga(total_da_compra: float, valor_pago: float) -> float:
    """
    Implementação ingênua: subtrai os dois floats diretamente. Isso pode
    gerar resultados como 0.30000000000000004 por causa de como números
    decimais são representados em ponto flutuante — um bug clássico em
    sistemas financeiros que usam float em vez de Decimal/centavos.
    """
    return valor_pago - total_da_compra


# ------------------------------------------------------------------
# "VERSÃO NOVA" do cálculo de troco (corrigida)
# ------------------------------------------------------------------
def calcular_troco_versao_nova(total_da_compra: float, valor_pago: float) -> float:
    """
    Implementação corrigida: converte para centavos (inteiros) antes de
    subtrair, evitando o problema de arredondamento do ponto flutuante,
    e só volta para reais (float) no resultado final, já arredondado.
    """
    total_em_centavos = round(total_da_compra * 100)
    pago_em_centavos = round(valor_pago * 100)
    troco_em_centavos = pago_em_centavos - total_em_centavos
    return round(troco_em_centavos / 100, 2)


# ------------------------------------------------------------------
# CASOS DE TESTE (as mesmas entradas para as duas versões)
# ------------------------------------------------------------------
CASOS_DE_TESTE = [
    # (total_da_compra, valor_pago)
    (10.00, 20.00),
    (9.90, 10.00),
    (0.10, 0.30),        # caso clássico de erro de ponto flutuante
    (19.99, 20.00),
    (100.00, 100.00),
    (33.33, 50.00),
    (1.10, 2.00),
]


def rodar_as_duas_versoes_em_paralelo(total, pago):
    """
    Dispara as duas implementações em threads separadas, "ao mesmo tempo"
    — replicando a ideia central do teste paralelo: as duas versões
    recebem a MESMA entrada, no mesmo instante, sem uma influenciar a
    outra.
    """
    with ThreadPoolExecutor(max_workers=2) as executor:
        tarefa_antiga = executor.submit(calcular_troco_versao_antiga, total, pago)
        tarefa_nova = executor.submit(calcular_troco_versao_nova, total, pago)
        resultado_antigo = tarefa_antiga.result()
        resultado_novo = tarefa_nova.result()
    return resultado_antigo, resultado_novo


def test_paralelo_compara_versao_antiga_e_nova_do_calculo_de_troco():
    """
    Roda todos os casos de teste nas duas versões e reporta as
    divergências — exatamente como um teste paralelo faria ao comparar
    um sistema legado com o substituto antes de decidir migrar de vez.
    """
    divergencias = []

    for total, pago in CASOS_DE_TESTE:
        resultado_antigo, resultado_novo = rodar_as_duas_versoes_em_paralelo(total, pago)

        if resultado_antigo != resultado_novo:
            divergencias.append({
                "entrada": (total, pago),
                "versao_antiga": resultado_antigo,
                "versao_nova": resultado_novo,
            })

    print("\n===== RELATÓRIO DO TESTE PARALELO =====")
    for divergencia in divergencias:
        print(
            f"Entrada {divergencia['entrada']}: "
            f"antiga={divergencia['versao_antiga']!r} "
            f"x nova={divergencia['versao_nova']!r}"
        )
    print(f"Total de casos: {len(CASOS_DE_TESTE)} | Divergências: {len(divergencias)}")

    # Neste exemplo, ESPERAMOS divergências (é o bug de float que a nova
    # versão corrige) — por isso não usamos "assert não há divergência".
    # Em um teste paralelo real, depois de analisar o relatório, a equipe
    # decide: "essa diferença é uma correção esperada" ou "isso é uma
    # regressão que precisa ser corrigida antes de migrar".
    assert len(divergencias) > 0, (
        "Era esperado encontrar pelo menos o caso clássico de erro de "
        "ponto flutuante (0.10 / 0.30) — se não apareceu, revise as "
        "duas implementações."
    )

    # Verificação extra: quando HÁ divergência, a versão nova precisa
    # estar correta (o troco deve bater com a conta feita "na mão").
    for divergencia in divergencias:
        total, pago = divergencia["entrada"]
        assert divergencia["versao_nova"] == round(pago - total, 2)
