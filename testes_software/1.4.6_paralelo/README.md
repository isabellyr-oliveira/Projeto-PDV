# 1.4.6 — Teste Paralelo

## O que é

Teste paralelo roda **duas versões** de um sistema (ou de uma regra de
negócio) **ao mesmo tempo**, com as **mesmas entradas**, e compara as
saídas. É a técnica clássica usada quando uma empresa está substituindo
um sistema antigo (legado) por um novo e quer ter certeza de que o novo
se comporta do jeito esperado antes de desligar o antigo — em vez de
confiar "no achismo", ela compara resultado a resultado.

Repare que essa técnica é diferente de todas as outras desta pasta:
regressão, estresse, recuperação, performance e segurança testam **um
único sistema**. Teste paralelo, por definição, **precisa de duas
versões** para comparar — por isso ele é o mais difícil de encaixar
dentro de um único projeto pequeno como o de vocês.

## O que o `test_paralelo.py` demonstra (o que DEU para automatizar)

Como este projeto ainda não tem uma "versão antiga" real para comparar,
criamos um exemplo didático dentro do próprio arquivo: duas
implementações de uma futura função de **cálculo de troco do PDV**:

- `calcular_troco_versao_antiga`: usa subtração direta de `float`,
  igual a maioria dos códigos escritos sem cuidado — sofre com o clássico
  problema de arredondamento de ponto flutuante (`0.30000000000000004`
  em vez de `0.3`, um bug real e comum em sistemas financeiros).
- `calcular_troco_versao_nova`: converte para centavos antes de calcular,
  evitando o problema.

O teste roda as duas em **threads separadas ao mesmo tempo** para cada
caso de teste, reúne as divergências em um relatório, e confirma que a
versão nova está matematicamente correta nos casos em que ela diverge da
antiga.

Rode com:

```bash
pytest testes_software/1.4.6_paralelo -v -s
```

## Como aplicar teste paralelo DE VERDADE neste projeto (passo a passo manual)

Isso é o que fazer quando o projeto do PDV/estoque tiver uma nova versão
para substituir uma versão em produção — cenário real de teste paralelo,
que não dá para simular só com pytest dentro de um repositório:

### 1. Suba as duas versões ao mesmo tempo, em portas diferentes

```bash
# Terminal 1 — versão ATUAL (produção), na porta 8000
git checkout main
python -m uvicorn app.main:app --port 8000

# Terminal 2 — versão NOVA (ex.: branch com uma mudança em desenvolvimento)
git checkout minha-branch-nova
python -m uvicorn app.main:app --port 8001
```

Use **bancos de dados separados** (arquivos `.db` diferentes) mas com os
**mesmos dados iniciais** — copie o mesmo `banco.db` para os dois antes
de começar, assim as duas versões partem do mesmo estado.

### 2. Prepare uma lista de operações para repetir nas duas versões

Por exemplo, uma lista de produtos para cadastrar, buscas para fazer,
edições para aplicar — sempre as MESMAS operações, na MESMA ordem, nas
duas versões.

### 3. Envie as mesmas requisições para as duas portas e compare

```python
# exemplo_comparar_servidores.py — rode manualmente, não é pytest
import requests

OPERACOES = [
    {"nome": "Caneta Azul", "preco": "2.50", "estoque_atual": "100", "categoria_id": "0"},
    {"nome": "Caderno",     "preco": "15.9", "estoque_atual": "20",  "categoria_id": "0"},
]

for operacao in OPERACOES:
    resposta_producao = requests.post("http://127.0.0.1:8000/produtos/novo", data=operacao)
    resposta_nova      = requests.post("http://127.0.0.1:8001/produtos/novo", data=operacao)

    if resposta_producao.status_code != resposta_nova.status_code:
        print(f"DIVERGÊNCIA em {operacao['nome']}: "
              f"produção={resposta_producao.status_code} "
              f"nova={resposta_nova.status_code}")
```

(Esse script é só um esqueleto para adaptar — ele não faz login/cookies,
que precisariam ser tratados também, um por servidor.)

### 4. Analise as divergências encontradas

Para cada diferença encontrada entre as duas versões, a equipe decide:

- É uma **melhoria intencional** (ex.: uma validação nova que a versão
  antiga não tinha)? Documentar e seguir em frente.
- É uma **regressão** (algo que funcionava e parou de funcionar, ou
  passou a se comportar de forma diferente sem motivo)? Corrigir antes
  de substituir a versão antiga.

### 5. Só depois de rodar em paralelo por um tempo, "desligue" a versão antiga

Em empresas grandes, esse processo de "rodar em paralelo" pode durar
dias ou semanas, direcionando uma cópia (shadow) do tráfego real de
produção para a versão nova sem que os usuários percebam, exatamente
para ganhar confiança antes da migração definitiva.

## Discussão com a turma

1. Por que o teste paralelo funcionou tão bem para pegar o bug de
   ponto flutuante no exemplo de troco?
2. Por que essa técnica seria cara/trabalhosa de aplicar em um sistema
   grande, com banco de dados compartilhado entre várias equipes?
3. Que outras regras de negócio do sistema (além do troco) seriam boas
   candidatas a um teste paralelo quando o projeto crescer (ex.:
   cálculo de desconto, cálculo de comissão, relatório de vendas)?
