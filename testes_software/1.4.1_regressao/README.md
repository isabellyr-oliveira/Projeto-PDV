# 1.4.1 — Teste de Regressão

## O que é

Teste de regressão é reexecutar um conjunto de testes já existentes toda
vez que o código muda (correção de bug, nova funcionalidade, refatoração)
para garantir que uma parte do sistema que já funcionava não **voltou a
quebrar** (regrediu). É a técnica mais usada no dia a dia de qualquer
equipe de desenvolvimento.

## O que este teste cobre no projeto

O arquivo `test_regressao.py` funciona como a "suíte principal" do
sistema de controle de estoque/PDV, cobrindo o fluxo essencial:

- Cadastro de categoria (com e sem duplicidade)
- Cadastro de produto (com e sem duplicidade)
- Edição de produto
- Desativação (soft delete) de produto
- Busca de produto por nome
- Controle de acesso: operador x admin
- Login com senha certa e errada
- Regra de negócio de "estoque baixo"

## Como rodar

Na raiz do projeto:

```bash
pip install -r requirements.txt
pip install -r testes_software/requirements-teste.txt
pytest testes_software/1.4.1_regressao -v
```

## Atividade sugerida para a turma

1. Rode a suíte e confirme que os 12 testes passam (isso é o seu
   "baseline" — a foto do sistema funcionando).
2. Escolha um aluno para alterar uma regra de negócio sem avisar o
   restante da turma. Exemplos simples:
   - Em `app/models/produto.py`, trocar `estoque_atual <= 10` por
     `estoque_atual < 10`.
   - Em `app/controllers/produto_controller.py`, remover a checagem de
     produto duplicado.
3. Rode a suíte de novo: `pytest testes_software/1.4.1_regressao -v`.
4. Discuta com a turma: qual teste quebrou? Ele apontou exatamente qual
   comportamento mudou? Essa é a essência do teste de regressão — pegar
   o problema antes que ele chegue para o usuário final.

## Quando rodar na prática

- Antes de todo `git push`/pull request.
- Em um pipeline de CI (GitHub Actions, por exemplo), a cada commit.
- Sempre que uma correção de bug for feita — adicione um teste que
  reproduz o bug (deve falhar antes da correção e passar depois).
