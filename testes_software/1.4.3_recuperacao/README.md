# 1.4.3 — Teste de Recuperação

## O que é

Teste de recuperação verifica se o sistema volta a funcionar corretamente
(e sem perder/corromper dados) depois de uma falha: queda de conexão com
o banco, erro inesperado durante uma operação, o processo do servidor
sendo encerrado e reiniciado, falta de energia, etc.

## O que o `test_recuperacao.py` cobre (automatizado em Python)

| Teste | Falha simulada | O que verificamos |
|---|---|---|
| `test_sistema_recusa_token_corrompido_sem_travar` | Cookie de sessão adulterado/corrompido | Sistema responde 401 (não trava, não dá erro 500) |
| `test_sistema_recusa_token_expirado_sem_travar` | Token JWT expirado | Sistema responde 401 corretamente |
| `test_dados_nao_ficam_corrompidos_se_commit_falhar` | Banco "cai" no meio do `db.commit()` | Nenhum dado incompleto fica salvo |
| `test_dados_persistem_apos_reiniciar_conexao_com_banco` | Processo do servidor é "reiniciado" | Dados gravados antes continuam lá depois |

Rode com:

```bash
pytest testes_software/1.4.3_recuperacao/test_recuperacao.py -v
```

## O que NÃO dá para automatizar só com Python (e como fazer manualmente)

Testes de recuperação "de verdade" muitas vezes envolvem mexer no sistema
operacional, no processo do servidor ou em arquivos de backup — coisas
que não fazem sentido dentro de um `pytest`. Aqui está o passo a passo
para fazer isso manualmente com a turma.

### 1. Simular o servidor "caindo" e voltar a funcionar

```bash
# Terminal 1: suba o servidor normalmente
python -m uvicorn app.main:app --reload

# Cadastre um produto pela interface (http://127.0.0.1:8000/produtos/novo)

# Terminal 2: mate o processo do servidor abruptamente (simula uma queda)
# Descubra o PID:
ps aux | grep uvicorn
# Mate o processo (Linux/Mac):
kill -9 <PID>
```

**O que observar:** o navegador do usuário mostra um erro de conexão
(esperado — o servidor caiu de verdade). Agora suba o servidor de novo
(`python -m uvicorn app.main:app --reload`) e acesse `/produtos`
novamente.

**Critério de sucesso:** o produto cadastrado antes da queda ainda deve
aparecer na lista — porque o SQLite grava em disco a cada `commit()`,
então o dado sobrevive independente do processo do servidor ter caído.

### 2. Backup e restauração do banco de dados

Um dos pilares de recuperação é: "se o banco for corrompido ou apagado
por engano, existe uma cópia recente para restaurar?"

```bash
# 1. Faça uma cópia de segurança do banco (com o servidor PARADO)
cp banco.db backup_banco.db

# 2. Simule uma "catástrofe": apague ou corrompa o banco
rm banco.db
# (ou, para simular corrupção sem apagar: echo "lixo" > banco.db)

# 3. Tente rodar o servidor -- vai dar erro, pois a tabela não existe mais
python -m uvicorn app.main:app --reload
# Ctrl+C para parar

# 4. Restaure o backup
cp backup_banco.db banco.db

# 5. Suba o servidor de novo e confirme que os dados voltaram
python -m uvicorn app.main:app --reload
```

**Discussão com a turma:** o que aconteceria se NÃO existisse backup?
Com que frequência um sistema real deveria fazer backup automático?

### 3. Recuperação via migrations (Alembic)

Esse projeto usa Alembic para controlar mudanças no esquema do banco.
Isso também é uma forma de recuperação: se uma migration quebrar o
banco, é possível "desfazer" (rollback):

```bash
# Ver o histórico de migrations aplicadas
python -m alembic history

# Desfazer a última migration aplicada
python -m alembic downgrade -1

# Aplicar de novo
python -m alembic upgrade head
```

### 4. Roteiro de discussão em sala

1. O que aconteceu com os dados em cada simulação: sobreviveram ou se
   perderam?
2. O sistema atual tem rotina de backup automático? (Resposta: não —
   ótimo gancho para propor isso como melhoria do projeto.)
3. O que este sistema poderia fazer melhor para se recuperar de falhas
   (ex.: tratar exceções de banco com try/except e mostrar uma mensagem
   amigável em vez de erro 500)?
