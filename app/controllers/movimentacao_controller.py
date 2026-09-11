# controllers/movimentacao_controller.py
# ============================================================
# Entradas e saídas de estoque.
# Qualquer usuário logado pode registrar movimentações.
# Somente admins podem ver o histórico completo de todos
# os produtos — operadores veem apenas suas próprias.
# ============================================================

import math  # Importado para cálculos da paginação
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.movimentacao import Movimentacao, TipoMovimentacao
from app.models.produto import Produto
from app.auth import get_usuario_logado, get_admin

router = APIRouter(prefix="/movimentacoes", tags=["Movimentações"])

templates = Jinja2Templates(directory="app/templates")


def gerar_intervalo_paginas(pagina: int, total_paginas: int, limite: int = 2):
    pagina = max(1, int(pagina) if pagina else 1)
    total_paginas = max(1, int(total_paginas) if total_paginas else 1)

    if total_paginas <= 1:
        return [1]

    paginas = set()
    paginas.add(1)
    paginas.add(total_paginas)

    for i in range(max(1, pagina - limite), min(total_paginas, pagina + limite) + 1):
        paginas.add(i)

    resultado = sorted(list(paginas))

    intervalo_com_dots = []
    prev = None
    for p in resultado:
        if prev is not None:
            if p - prev == 2:
                intervalo_com_dots.append(prev + 1)
            elif p - prev > 2:
                intervalo_com_dots.append("...")
        intervalo_com_dots.append(p)
        prev = p

    return intervalo_com_dots


# ============================================================
# HISTÓRICO GERAL — somente admin
# ============================================================

@router.get("/", response_class=HTMLResponse)
def listar_movimentacoes(
    request: Request,
    produto_id: int = 0,     # filtra por produto específico
    tipo: str = "",          # "entrada", "saida", etc.
    db: Session = Depends(get_db),
    admin = Depends(get_admin),  # Apenas admins podem ver o histórico completo
    pagina: int = 1,
    por_pagina: int = 10,
):
    """
    Exibe o histórico completo de movimentações com paginação e
    filtros por produto e tipo.
    """
    # 1. Monta a query base com filtros
    query = db.query(Movimentacao).order_by(Movimentacao.criado_em.desc())

    if produto_id:
        query = query.filter(Movimentacao.produto_id == produto_id)

    if tipo in ("entrada", "saida", "cancelamento", "ajuste"):
        query = query.filter(Movimentacao.tipo == tipo)

    # 2. Total de registros filtrados para a paginação
    total_movimentacoes = query.count()

    # 3. Ajuste de páginas e offset
    pagina = max(pagina, 1)
    por_pagina = max(por_pagina, 1)

    total_paginas = math.ceil(total_movimentacoes / por_pagina) if total_movimentacoes else 1
    offset = (pagina - 1) * por_pagina

    # 4. Busca os registros da página atual
    movimentacoes = query.offset(offset).limit(por_pagina).all()

    # 5. Busca produtos ativos para preencher o select do filtro no HTML
    produtos = db.query(Produto).filter(Produto.ativo == True).all()

    # 6. Gera o intervalo da paginação (ex: [1, 2, '...', 10])
    intervalo_paginas = gerar_intervalo_paginas(pagina, total_paginas)

    return templates.TemplateResponse(
        request,
        "movimentacoes/index.html",
        {
            "request":             request,
            "usuario":             admin,
            "movimentacoes":       movimentacoes,
            "produtos":            produtos,
            "produto_id":          produto_id,
            "tipo":                tipo,
            "pagina":              pagina,
            "por_pagina":          por_pagina,
            "total_paginas":       total_paginas,
            "total_movimentacoes": total_movimentacoes,
            "intervalo_paginas":   intervalo_paginas,
        }
    )


# ============================================================
# REGISTRAR MOVIMENTAÇÃO
# ============================================================

@router.get("/nova")
def form_nova_movimentacao(
    request: Request,
    produto_id: int = 0,   # pré-seleciona o produto se vier da página de detalhe
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado)
):
    """
    Exibe o formulário de registro de movimentação.
    Pode receber produto_id via query string para
    pré-selecionar o produto direto da página de detalhe.
    """
    produtos = db.query(Produto).filter(Produto.ativo == True).all()

    return templates.TemplateResponse(
        request,
        "movimentacoes/form.html",
        {
            "request":    request,
            "usuario":    usuario,
            "produtos":   produtos,
            "produto_id": produto_id,
            "tipos":      TipoMovimentacao,  # passa o enum para o template
        }
    )


@router.post("/nova")
def registrar_movimentacao(
    request: Request,
    produto_id: int     = Form(...),
    tipo: str           = Form(...),
    quantidade: int     = Form(...),
    preco_unitario: float = Form(...),
    observacao: str     = Form(""),
    db: Session         = Depends(get_db),
    usuario             = Depends(get_usuario_logado)
):
    """
    Registra a movimentação e atualiza o estoque do produto
    em uma única transação — garante consistência.
    """
    produtos = db.query(Produto).filter(Produto.ativo == True).all()

    # Valida se o tipo enviado é válido
    if tipo not in (TipoMovimentacao.ENTRADA, TipoMovimentacao.SAIDA):
        return templates.TemplateResponse(
            request,
            "movimentacoes/form.html",
            {
                "request":    request,
                "usuario":    usuario,
                "produtos":   produtos,
                "produto_id": produto_id,
                "tipos":      TipoMovimentacao,
                "erro":       "Tipo de movimentação inválido.",
            },
            status_code=400
        )

    if quantidade <= 0:
        return templates.TemplateResponse(
            request,
            "movimentacoes/form.html",
            {
                "request":    request,
                "usuario":    usuario,
                "produtos":   produtos,
                "produto_id": produto_id,
                "tipos":      TipoMovimentacao,
                "erro":       "A quantidade deve ser maior que zero.",
            },
            status_code=400
        )

    # Busca o produto com lock para evitar race condition
    produto = db.query(Produto).filter(
        Produto.id == produto_id
    ).with_for_update().first()

    if not produto:
        return RedirectResponse(url="/movimentacoes/nova", status_code=302)

    # Impede saída maior que o estoque disponível
    if tipo == TipoMovimentacao.SAIDA and quantidade > produto.estoque_atual:
        return templates.TemplateResponse(
            request,
            "movimentacoes/form.html",
            {
                "request":    request,
                "usuario":    usuario,
                "produtos":   produtos,
                "produto_id": produto_id,
                "tipos":      TipoMovimentacao,
                "erro": (
                    f"Estoque insuficiente. "
                    f"Disponível: {produto.estoque_atual} unidade(s)."
                ),
            },
            status_code=400
        )

    # Atualiza o estoque do produto
    if tipo == TipoMovimentacao.ENTRADA:
        produto.estoque_atual += quantidade
    else:
        produto.estoque_atual -= quantidade

    # Registra a movimentação no histórico
    movimentacao = Movimentacao(
        tipo           = tipo,
        quantidade     = quantidade,
        preco_unitario = preco_unitario,
        observacao     = observacao or None,
        produto_id     = produto_id,
        usuario_id     = usuario.get("id"),
    )

    db.add(movimentacao)
    db.commit()

    return RedirectResponse(
        url=f"/produtos/{produto_id}?movimentacao=ok",
        status_code=302
    )


# ============================================================
# HISTÓRICO POR PRODUTO — acessível por qualquer logado
# ============================================================

@router.get("/produto/{produto_id}")
def historico_produto(
    produto_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado)
):
    """
    Exibe o histórico de movimentações de um produto específico
    com o resumo de entradas, saídas e saldo.
    """
    produto = db.query(Produto).filter(Produto.id == produto_id).first()

    if not produto:
        return RedirectResponse(url="/produtos", status_code=302)

    movimentacoes = (
        db.query(Movimentacao)
        .filter(Movimentacao.produto_id == produto_id)
        .order_by(Movimentacao.criado_em.desc())
        .all()
    )

    total_entradas = sum(
        m.quantidade for m in movimentacoes
        if m.tipo == TipoMovimentacao.ENTRADA
    )
    total_saidas = sum(
        m.quantidade for m in movimentacoes
        if m.tipo == TipoMovimentacao.SAIDA
    )

    return templates.TemplateResponse(
        request,
        "movimentacoes/historico.html",
        {
            "request":        request,
            "usuario":        usuario,
            "produto":        produto,
            "movimentacoes":  movimentacoes,
            "total_entradas": total_entradas,
            "total_saidas":   total_saidas,
        }
    )