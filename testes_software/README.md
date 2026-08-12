# Testes de Software — Projeto de Controle de Estoque e PDV

Esta pasta é material de estudo sobre **teste de software**, construído
em cima do projeto real que vocês estão desenvolvendo (FastAPI +
SQLAlchemy + SQLite, com cadastro de usuários, categorias e produtos,
autenticação por JWT e controle de estoque).

Cobrimos as 6 técnicas do plano de ensino:

| # | Técnica | Pasta | Automatizado com Python? |
|---|---|---|---|
| 1.4.1 | Regressão | [`1.4.1_regressao/`](1.4.1_regressao) | ✅ Totalmente |
| 1.4.2 | Estresse | [`1.4.2_estresse/`](1.4.2_estresse) | ✅ Parcialmente (+ script para servidor real) |
| 1.4.3 | Recuperação | [`1.4.3_recuperacao/`](1.4.3_recuperacao) | ✅ Parcialmente (+ passo a passo manual) |
| 1.4.4 | Performance | [`1.4.4_performance/`](1.4.4_performance) | ✅ Totalmente |
| 1.4.5 | Segurança | [`1.4.5_seguranca/`](1.4.5_seguranca) | ✅ Totalmente |
| 1.4.6 | Paralelo | [`1.4.6_paralelo/`](1.4.6_paralelo) | ⚠️ Só o conceito (exemplo didático) — o cenário real precisa de passo a passo manual |

Cada pasta tem:

- Um arquivo `test_*.py` com os testes em Python, **comentado linha a
  linha**, explicando o quê e o porquê de cada trecho.
- Um `README.md` próprio explicando a técnica, o que o teste cobre, como
  rodar, e uma atividade sugerida para a turma.
- Quando alguma parte da técnica não dá para automatizar dentro de um
  `pytest` (ex.: matar o processo do servidor de verdade, restaurar um
  backup, subir duas versões do sistema em paralelo), o passo a passo
  manual está detalhado no `README.md` daquela pasta.

## Por que algumas técnicas não são 100% automatizáveis em Python

Testes automatizados em Python (com pytest) são ótimos para testar
**código** — chamadas de função, rotas HTTP, regras de negócio. Mas
algumas técnicas de teste envolvem coisas que acontecem **fora** do
código Python em si:

- **Recuperação**: matar o processo do servidor, desligar a energia,
  restaurar um backup de arquivo — são ações de sistema operacional.
- **Paralelo**: por definição, precisa de DUAS versões completas do
  sistema rodando ao mesmo tempo, muitas vezes em servidores diferentes.
- **Estresse** "de verdade": ferramentas profissionais como Locust ou k6
  geram uma carga de rede muito mais realista do que conseguimos simular
  com um TestClient rodando "em memória".

Nesses casos, fizemos o que É possível em Python (para ensinar o
conceito e ter algo executável e verificável) e documentamos o restante
como um roteiro manual — que é exatamente como um profissional de QA
faria fora de um ambiente 100% automatizado.

## Como preparar o ambiente

Na raiz do projeto (`projeto-aapm-seducb/`):

```bash
# 1. Dependências da aplicação (se ainda não tiver instalado)
pip install -r requirements.txt

# 2. Dependências para RODAR os testes
pip install -r testes_software/requirements-teste.txt
```

## Como rodar tudo

```bash
# Todas as técnicas de uma vez
pytest testes_software -v

# Uma técnica específica
pytest testes_software/1.4.1_regressao -v
pytest testes_software/1.4.5_seguranca -v -s
```

> `-v` mostra o nome de cada teste (verboso). `-s` também mostra os
> `print()` que alguns testes usam para exibir relatórios (estresse,
> performance, paralelo).

## Como os testes funcionam por baixo dos panos (leia antes de mexer)

O arquivo [`conftest.py`](conftest.py), na raiz desta pasta, é
compartilhado por **todos** os testes das subpastas. Ele:

1. Aponta a aplicação para um banco SQLite **exclusivo de teste**
   (`testes_software/banco_teste.db`), para nunca bagunçar o
   `banco.db` real usado em desenvolvimento.
2. Cria e destrói as tabelas automaticamente a cada execução da suíte.
3. Limpa as tabelas entre cada teste individual, para que um teste nunca
   dependa de dados deixados por outro (boa prática: testes
   independentes, que podem rodar em qualquer ordem).
4. Oferece "fixtures" prontas para os testes usarem, como:
   - `client` — simula um navegador conversando com o FastAPI.
   - `criar_admin(...)` / `criar_operador(...)` — criam usuários de teste.
   - `login_como(email, senha)` — faz login de verdade pela rota
     `/auth/login` e guarda o cookie de sessão.
   - `sessao_db` — dá acesso direto ao banco de teste, útil para
     conferir o que ficou salvo.

Vale a pena ler os comentários do `conftest.py` com a turma antes de
começar — ele ensina conceitos importantes de teste automatizado
(fixtures, isolamento entre testes, dependency override) que se aplicam
a qualquer projeto Python, não só a este.

## Estrutura de pastas

```
testes_software/
├── README.md                      <- você está aqui
├── conftest.py                    <- configuração e fixtures compartilhadas
├── pytest.ini                     <- configuração do pytest
├── requirements-teste.txt         <- dependências só de teste
├── 1.4.1_regressao/
│   ├── test_regressao.py
│   └── README.md
├── 1.4.2_estresse/
│   ├── test_estresse.py
│   ├── estresse_servidor_real.py  <- script opcional contra servidor real
│   └── README.md
├── 1.4.3_recuperacao/
│   ├── test_recuperacao.py
│   └── README.md
├── 1.4.4_performance/
│   ├── test_performance.py
│   └── README.md
├── 1.4.5_seguranca/
│   ├── test_seguranca.py
│   └── README.md
└── 1.4.6_paralelo/
    ├── test_paralelo.py
    └── README.md
```

## Sugestão de roteiro de aula (6 aulas, uma por técnica)

1. Explique o conceito da técnica (use o início do `README.md` da pasta).
2. Rode a suíte de testes com a turma projetada na tela.
3. Leia o código do teste linha a linha, perguntando "por que essa linha
   está aqui?" antes de revelar o comentário.
4. Faça a atividade sugerida no `README.md` da pasta (geralmente envolve
   quebrar algo de propósito e ver o teste pegar o problema).
5. Feche com a seção de discussão do `README.md`, quando houver.
