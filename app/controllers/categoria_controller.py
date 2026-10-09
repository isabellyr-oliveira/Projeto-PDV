# controllers/categoria_controller.py — CRUD de categorias

# Categorias são gerenciadas apenas por admins.
# Operadores apenas visualizam (via select no form de produto).
# ============================================================

import math

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.categoria import Categoria
from app.auth import get_admin

router = APIRouter(prefix="/categorias", tags=["Categorias"])

templates = Jinja2Templates(directory="app/templates")


# ============================================================
# FUNÇÃO PARA GERAR INTERVALO DE PÁGINAS
# ============================================================

def gerar_intervalo_paginas(
    pagina: int,
    total_paginas: int,
    limite: int = 2
):
    pagina = max(1, int(pagina) if pagina else 1)
    total_paginas = max(
        1,
        int(total_paginas) if total_paginas else 1
    )

    if total_paginas <= 1:
        return [1]

    paginas = set()

    # Primeira e última página
    paginas.add(1)
    paginas.add(total_paginas)

    # Páginas próximas da página atual
    for i in range(
        max(1, pagina - limite),
        min(total_paginas, pagina + limite) + 1
    ):
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
# LISTAGEM
# ============================================================

@router.get("/")
def listar_categorias(
    request: Request,
    pagina: int = 1,
    por_pagina: int = 2,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    """
    Lista as categorias ordenadas por nome
    com paginação.
    """

    # Garante valores válidos
    pagina = max(pagina, 1)
    por_pagina = max(por_pagina, 1)

    # Query base
    query = db.query(Categoria).order_by(Categoria.nome)

    # Total de categorias
    total_categorias = query.count()

    # Calcula quantidade de páginas
    total_paginas = (
        math.ceil(total_categorias / por_pagina)
        if total_categorias
        else 1
    )

    # Evita acessar uma página que não existe
    if pagina > total_paginas:
        pagina = total_paginas

    # Calcula o deslocamento
    offset = (pagina - 1) * por_pagina

    # Busca somente as categorias da página atual
    categorias = (
        query
        .offset(offset)
        .limit(por_pagina)
        .all()
    )

    # Gera os números da paginação
    intervalo_paginas = gerar_intervalo_paginas(
        pagina,
        total_paginas
    )

    return templates.TemplateResponse(
        request,
        "categorias/index.html",
        {
            "request": request,
            "usuario": admin,
            "categorias": categorias,

            # Paginação
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total_paginas": total_paginas,
            "total_categorias": total_categorias,
            "intervalo_paginas": intervalo_paginas,
        }
    )


# ============================================================
# CADASTRO
# ============================================================

@router.get("/nova")
def form_nova_categoria(
    request: Request,
    admin = Depends(get_admin)
):
    """Exibe o formulário de cadastro de categoria."""

    return templates.TemplateResponse(
        request,
        "categorias/form.html",
        {
            "request": request,
            "usuario": admin,
            "editando": None,
        }
    )


@router.post("/nova")
def criar_categoria(
    request: Request,
    nome: str = Form(...),
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    """Cria uma nova categoria verificando duplicidade de nome."""

    existente = db.query(Categoria).filter(
        Categoria.nome.ilike(nome)
    ).first()

    if existente:
        return templates.TemplateResponse(
            request,
            "categorias/form.html",
            {
                "request": request,
                "usuario": admin,
                "editando": None,
                "erro": "Já existe uma categoria com este nome.",
                "valores": {"nome": nome},
            },
            status_code=400
        )

    db.add(Categoria(nome=nome.strip()))
    db.commit()

    return RedirectResponse(
        url="/categorias?criado=ok",
        status_code=302
    )


# ============================================================
# EDIÇÃO
# ============================================================

@router.get("/{categoria_id}/editar")
def form_editar_categoria(
    categoria_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    """Exibe o formulário preenchido com os dados da categoria."""

    editando = db.query(Categoria).filter(
        Categoria.id == categoria_id
    ).first()

    if not editando:
        return RedirectResponse(
            url="/categorias",
            status_code=302
        )

    return templates.TemplateResponse(
        request,
        "categorias/form.html",
        {
            "request": request,
            "usuario": admin,
            "editando": editando,
        }
    )


@router.post("/{categoria_id}/editar")
def editar_categoria(
    categoria_id: int,
    request: Request,
    nome: str = Form(...),
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    """Atualiza o nome da categoria."""

    editando = db.query(Categoria).filter(
        Categoria.id == categoria_id
    ).first()

    if not editando:
        return RedirectResponse(
            url="/categorias",
            status_code=302
        )

    conflito = db.query(Categoria).filter(
        Categoria.nome.ilike(nome),
        Categoria.id != categoria_id
    ).first()

    if conflito:
        return templates.TemplateResponse(
            request,
            "categorias/form.html",
            {
                "request": request,
                "usuario": admin,
                "editando": editando,
                "erro": "Já existe outra categoria com este nome.",
            },
            status_code=400
        )

    editando.nome = nome.strip()
    db.commit()

    return RedirectResponse(
        url="/categorias?editado=ok",
        status_code=302
    )


# ============================================================
# EXCLUSÃO FÍSICA
# ============================================================

@router.get("/{categoria_id}/deletar")
def deletar_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    """Apaga permanentemente a categoria do banco de dados."""

    categoria = db.query(Categoria).filter(
        Categoria.id == categoria_id
    ).first()

    if categoria:
        db.delete(categoria)
        db.commit()

    return RedirectResponse(
        url="/categorias?deletado=ok",
        status_code=302
    )


# ============================================================
# TOGGLE ATIVO
# ============================================================

@router.post("/{categoria_id}/toggle-ativo")
def toggle_ativo(
    categoria_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    """
    Ativa ou desativa uma categoria.
    """

    categoria = db.query(Categoria).filter(
        Categoria.id == categoria_id
    ).first()

    if not categoria:
        return RedirectResponse(
            url="/categorias",
            status_code=302
        )

    if categoria.ativo:
        produtos_ativos = [
            p for p in categoria.produtos
            if p.ativo
        ]

        if produtos_ativos:
            return RedirectResponse(
                url=f"/categorias?erro=produtos_vinculados&categoria={categoria.nome}",
                status_code=302
            )

    categoria.ativo = not categoria.ativo
    db.commit()

    return RedirectResponse(
        url="/categorias",
        status_code=302
    )