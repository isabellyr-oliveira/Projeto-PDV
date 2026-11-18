# Ponte de entrada do meu sistema
from datetime import datetime, time, timedelta
from fastapi import FastAPI, Request, Depends, status
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.auth import get_usuario_opcional
from app.database import get_db
from app.models.venda import Venda, PagamentoVenda
from app.models.produto import Produto
from app.models.cliente import Cliente

from app.controllers import auth_controller
from app.controllers import usuario_controller
from app.controllers import categoria_controller
from app.controllers import produto_controller
from app.controllers import movimentacao_controller
from app.controllers import cliente_controller
from app.controllers import pdv_controller


app = FastAPI(title="Sistema de Ponto de venda")

# Configurar a pasta para servir os arquivos estáticos (CSS, JS e IMG)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configurar o jinja2 para renderizar os HTML
templates = Jinja2Templates(directory="app/templates")

# Inclui os routers dos controladores
app.include_router(auth_controller.router)
app.include_router(usuario_controller.router)
app.include_router(categoria_controller.router)
app.include_router(produto_controller.router)
app.include_router(movimentacao_controller.router)
app.include_router(cliente_controller.router) 
app.include_router(pdv_controller.router) 

# ==========================================
# TRATAMENTO GLOBAL DE ERROS (401, 403, 404)
# ==========================================
@app.exception_handler(StarletteHTTPException)
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: Exception):
    # Trata o código de status vindo da exceção
    status_code = getattr(exc, "status_code", 500)
    detail = getattr(exc, "detail", "")

    # Se o erro for de não autenticado (401), vai direto para a tela de login
    if status_code == status.HTTP_401_UNAUTHORIZED:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    # Definição das mensagens amigáveis baseadas no código de status
    titulo_erro = "Acesso Negado"
    mensagem_erro = "Você não tem permissão para acessar esta página."

    if status_code == 404:
        titulo_erro = "Página Não Encontrada"
        mensagem_erro = "A página ou recurso que você está tentando acessar não existe."
    elif isinstance(detail, str) and detail != "Not Found" and detail != "":
        mensagem_erro = detail

    # Tenta obter o usuário logado para manter o nome/navbar ativo na tela de erro
    usuario = None
    try:
        usuario = await get_usuario_opcional(request)
    except Exception:
        pass

    # Exibe a tela amigável de erro (erro.html)
    return templates.TemplateResponse(
        request,
        "erro.html",
        {
            "request": request,
            "status_code": status_code,
            "titulo_erro": titulo_erro,
            "mensagem": mensagem_erro,
            "usuario": usuario
        },
        status_code=status_code
    )


@app.get("/")
def tela_inicial(
    request: Request,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_opcional)
):
    # Tela não logado
    if usuario is None:
        return templates.TemplateResponse(
            request,
            "tela_inicio.html",
            {"request": request}
        )

    # Intervalo de data de hoje
    hoje = datetime.now().date()
    inicio_hoje = datetime.combine(hoje, time.min)
    fim_hoje = datetime.combine(hoje, time.max)

    # 1. KPIs do dia atual
    faturamento_hoje = (
        db.query(func.coalesce(func.sum(Venda.total_liquido), 0.0))
        .filter(Venda.criado_em >= inicio_hoje, Venda.criado_em <= fim_hoje)
        .scalar()
    ) or 0.0

    vendas_hoje = (
        db.query(func.count(Venda.id))
        .filter(Venda.criado_em >= inicio_hoje, Venda.criado_em <= fim_hoje)
        .scalar()
    ) or 0

    ticket_medio = (faturamento_hoje / vendas_hoje) if vendas_hoje > 0 else 0.0

    # 2. KPI de Estoque Baixo (estoque_atual <= 10 conforme model Produto)
    total_estoque_baixo = (
        db.query(func.count(Produto.id))
        .filter(Produto.ativo == True, Produto.estoque_atual <= 10)
        .scalar()
    ) or 0

    # 3. KPI de Clientes Ativos
    total_clientes = (
        db.query(func.count(Cliente.id))
        .filter(Cliente.ativo == True)
        .scalar()
    ) or 0

    # 4. Dados do Gráfico 1: Faturamento dos últimos 7 dias
    labels_7_dias = []
    valores_7_dias = []

    for i in range(6, -1, -1):
        dia = hoje - timedelta(days=i)
        dt_ini = datetime.combine(dia, time.min)
        dt_fim = datetime.combine(dia, time.max)

        total_dia = (
            db.query(func.coalesce(func.sum(Venda.total_liquido), 0.0))
            .filter(Venda.criado_em >= dt_ini, Venda.criado_em <= dt_fim)
            .scalar()
        ) or 0.0

        labels_7_dias.append(dia.strftime("%d/%m"))
        valores_7_dias.append(round(float(total_dia), 2))

    # 5. Dados do Gráfico 2: Vendas por Forma de Pagamento
    pagamentos_agrupados = (
        db.query(
            PagamentoVenda.forma_pagamento,
            func.coalesce(func.sum(PagamentoVenda.valor), 0.0)
        )
        .group_by(PagamentoVenda.forma_pagamento)
        .all()
    )

    labels_pagamentos = [p[0].capitalize() if p[0] else "Outros" for p in pagamentos_agrupados]
    valores_pagamentos = [round(float(p[1]), 2) for p in pagamentos_agrupados]

    # 6. Tabela: Últimas 6 vendas registradas
    ultimas_vendas = (
        db.query(Venda)
        .order_by(Venda.criado_em.desc())
        .limit(6)
        .all()
    )

    # 7. Tabela: Top 6 produtos com estoque crítico (menor saldo primeiro)
    produtos_criticos = (
        db.query(Produto)
        .filter(Produto.ativo == True, Produto.estoque_atual <= 10)
        .order_by(Produto.estoque_atual.asc(), Produto.nome.asc())
        .limit(6)
        .all()
    )

    # Logado - exibir o Dashboard
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "request": request,
            "usuario": usuario,
            "faturamento_hoje": float(faturamento_hoje),
            "vendas_hoje": int(vendas_hoje),
            "ticket_medio": float(ticket_medio),
            "total_estoque_baixo": int(total_estoque_baixo),
            "total_clientes": int(total_clientes),
            "labels_7_dias": labels_7_dias,
            "valores_7_dias": valores_7_dias,
            "labels_pagamentos": labels_pagamentos,
            "valores_pagamentos": valores_pagamentos,
            "ultimas_vendas": ultimas_vendas,
            "produtos_criticos": produtos_criticos,
        }
    )