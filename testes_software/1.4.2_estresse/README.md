# 1.4.2 — Teste de Estresse

## O que é

Teste de estresse submete o sistema a uma carga **acima** do uso normal
(muitas requisições simultâneas, muitos dados, pouco tempo entre ações)
para descobrir como ele reage quando é sobrecarregado. O objetivo não é
"quebrar por quebrar": é descobrir **onde** e **como** o sistema quebra,
para que a equipe saiba o limite dele e trate os erros com elegância
(em vez de travar tudo ou corromper dados).

## O que este teste cobre no projeto

- `test_estresse.py` (roda com pytest, em memória, ótimo para CI):
  - Muitas leituras simultâneas em `/produtos` (ex.: vários caixas
    consultando o estoque ao mesmo tempo).
  - Muitos cadastros de categoria simultâneos, para observar como o
    SQLite se comporta sob concorrência de escrita.

- `estresse_servidor_real.py` (script avulso, **não** é pytest):
  contra o servidor `uvicorn` rodando de verdade, mede tempo de resposta
  e taxa de erro sob carga usando requisições HTTP reais.

## Como rodar

```bash
# 1) teste automatizado (em memória)
pytest testes_software/1.4.2_estresse/test_estresse.py -v -s

# 2) teste contra o servidor real (opcional, mais realista)
pip install requests
python -m uvicorn app.main:app --reload        # terminal 1
python testes_software/1.4.2_estresse/estresse_servidor_real.py   # terminal 2
```

## Por que o SQLite é um ótimo exemplo em sala de aula

Este projeto usa SQLite, um banco de dados simples baseado em arquivo.
SQLite permite várias LEITURAS simultâneas, mas só uma ESCRITA por vez —
quando duas escritas colidem, uma delas espera (ou falha com erro de
"database is locked" se a espera for muito longa). Isso é uma limitação
real e conhecida do SQLite, muito usada como exemplo didático:

- Em bancos como PostgreSQL ou MySQL, escritas concorrentes são tratadas
  de forma muito mais robusta.
- Um teste de estresse é exatamente a ferramenta que **revela** esse tipo
  de limitação antes que ela vire um problema em produção.

## Discussão com a turma

Depois de rodar os testes, pergunte:

1. O tempo de resposta aumentou conforme a carga aumentou?
2. Alguma requisição falhou? Com qual erro?
3. O que aconteceria se este sistema fosse usado em uma loja com 50
   caixas registrando vendas ao mesmo tempo?
4. Que mudanças poderiam tornar o sistema mais resistente a picos de
   uso (ex.: trocar SQLite por PostgreSQL, adicionar cache, limitar
   requisições por usuário)?

## Ferramentas profissionais (fora do escopo deste projeto)

Para testes de estresse "de verdade" em ambiente profissional, ferramentas
como **Locust** (Python) ou **k6** (JavaScript) são o padrão de mercado,
pois simulam milhares de usuários com relatórios gráficos prontos.
Um exemplo de `locustfile.py` para este mesmo projeto ficaria assim:

```python
# locustfile.py — instale com: pip install locust
# Rode com: locust -f locustfile.py --host=http://127.0.0.1:8000
from locust import HttpUser, task, between

class UsuarioDoEstoque(HttpUser):
    wait_time = between(1, 3)  # espera entre 1 e 3s entre as ações

    @task
    def ver_lista_de_produtos(self):
        self.client.get("/produtos")
```

Não incluímos essa ferramenta como dependência obrigatória do projeto
porque ela não é necessária para os testes automatizados da turma — mas
vale a pena mostrar em aula como um próximo passo.
