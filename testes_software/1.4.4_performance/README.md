# 1.4.4 — Teste de Performance

## O que é

Teste de performance mede **quanto tempo** o sistema leva para responder
em condições de uso normal (não sobrecarregado — isso é estresse, pasta
1.4.2). É sobre velocidade e eficiência: a página carrega rápido? A
consulta ao banco fica lenta conforme os dados crescem?

## O que este teste cobre no projeto

- Tempo de resposta da página inicial (`GET /`).
- Tempo médio (e percentil 95) da listagem de produtos com 200 registros
  cadastrados — simula um estoque de tamanho realista.
- Tempo de resposta do login, que usa bcrypt (hash de senha
  propositalmente lento por segurança — ver pasta 1.4.5).

## Como rodar

```bash
pytest testes_software/1.4.4_performance -v -s
```

O `-s` é importante aqui: sem ele, o pytest esconde os `print()` que
mostram os tempos medidos.

## Sobre os limites (thresholds) usados

Os limites de tempo (`LIMITE_MS`) neste arquivo são propositalmente
generosos, para o teste não falhar só por causa de uma máquina mais
lenta durante a aula. Em um projeto profissional, esses limites seriam
definidos junto com a área de produto/negócio, com base em métricas reais
de UX (ex.: "95% das páginas devem carregar em menos de 300ms").

## Atividade sugerida para a turma

1. Rode os testes e observe os tempos impressos no terminal.
2. Aumente `QUANTIDADE_DE_PRODUTOS` em `test_listagem_de_produtos_com_muitos_registros`
   de 200 para 5000 e rode de novo. O tempo médio aumentou? Por quê?
   (Dica: veja a consulta em `produto_controller.py` — ela usa
   `ORDER BY nome`, que fica mais cara conforme a tabela cresce, a menos
   que exista um índice — e o campo `nome` já tem `index=True` no model,
   o que ajuda bastante).
3. Compare o tempo do login com o tempo da listagem. Por que o login é
   naturalmente mais lento, mesmo sendo uma operação "mais simples"?
   (Resposta: o bcrypt é desenhado para ser lento de propósito, para
   dificultar ataques de força bruta — ver 1.4.5 Segurança.)

## Ferramentas profissionais (fora do escopo deste projeto)

Ferramentas como **Locust**, **k6** ou **Apache JMeter** medem
performance sob carga real de rede e geram gráficos de latência ao longo
do tempo. Para este projeto, medir com `time.perf_counter()` já é
suficiente para ensinar o conceito sem precisar instalar ferramentas
externas.
