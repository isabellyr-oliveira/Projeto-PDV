# 1.4.5 — Teste de Segurança

## O que é

Teste de segurança usa o sistema de forma deliberadamente maliciosa —
como um atacante faria — para encontrar vulnerabilidades antes que
alguém de má-fé as explore. Não é sobre "achar bug", é sobre pensar
"como eu quebraria isso de propósito?".

## O que este teste cobre

| Teste | Ataque simulado |
|---|---|
| `test_busca_de_produto_resiste_a_injecao_de_sql` | Injeção de SQL no campo de busca |
| `test_operador_nao_acessa_gestao_de_usuarios` | Escalonamento de privilégio (operador tentando agir como admin) |
| `test_operador_nao_cria_categoria` | Mesma ideia, em outra rota administrativa |
| `test_visitante_sem_login_nao_acessa_produtos` | Acesso sem autenticação |
| `test_token_com_assinatura_adulterada_e_rejeitado` | Adulteração de um JWT legítimo |
| `test_nao_e_possivel_forjar_token_de_admin_sem_a_chave_secreta` | Forjar um token do zero, como admin, sem saber a `SECRET_KEY` |
| `test_senha_nunca_e_armazenada_em_texto_puro` | Vazamento de senha em caso de acesso direto ao banco |
| `test_cookie_de_sessao_tem_flag_httponly` | Roubo de cookie de sessão via JavaScript (XSS) |
| `test_nome_de_produto_com_script_e_escapado_no_html` | Cross-Site Scripting (XSS) refletido |
| `test_login_nao_possui_limite_de_tentativas` | **Achado de segurança** — força bruta no login |

## Como rodar

```bash
pytest testes_software/1.4.5_seguranca -v
```

## Sobre o "achado de segurança"

O último teste (`test_login_nao_possui_limite_de_tentativas`) é diferente
dos outros: ele não confirma que o sistema está seguro — ele **documenta
uma vulnerabilidade real** que existe hoje no projeto (`/auth/login` não
bloqueia depois de várias tentativas erradas, permitindo ataque de força
bruta).

### Atividade para a turma (exercício de correção)

1. Implemente um limite de tentativas em `app/controllers/auth_controller.py`
   (por exemplo: guardar um contador de tentativas erradas por e-mail —
   pode ser em memória para simplificar, ou uma nova coluna no model
   `Usuario` — e bloquear por alguns minutos após 5 tentativas).
2. Depois de implementar, **atualize** o teste
   `test_login_nao_possui_limite_de_tentativas` para verificar que, a
   partir da 6ª tentativa errada, o sistema recusa o login mesmo com a
   senha correta (até o bloqueio expirar).
3. Essa é a essência de um ciclo de segurança saudável: encontrar → medir
   → corrigir → provar com um teste automatizado que ficou corrigido.

## Outras vulnerabilidades para discutir em sala (não cobertas em teste)

- **CSRF (Cross-Site Request Forgery):** os formulários deste projeto não
  usam token CSRF. Como o cookie de sessão tem `samesite="lax"` (ver
  `auth_controller.py`), o risco é reduzido, mas não eliminado. Vale
  pesquisar com a turma o que é `samesite="strict"` e por que trocar
  para `strict` teria um trade-off de usabilidade.
- **Upload de arquivos:** em `produto_controller.py`, o nome original do
  arquivo enviado é usado diretamente (`nome_arquivo = f"{imagem.filename}"`).
  Isso pode permitir sobrescrever arquivos existentes ou nomes com
  caracteres estranhos. Um exercício interessante é pesquisar sobre
  "path traversal" e propor o uso de `uuid4()` para nomear os arquivos
  (o próprio comentário do código já sugere isso).
- **Rate limiting geral:** nenhuma rota tem limite de requisições por
  IP/usuário — o que também deixa a aplicação exposta a abuso, além do
  problema específico do login.
