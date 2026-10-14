# controllers/cliente_controller.py — CRUD de clientes
# ============================================================
import math
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cliente import Cliente
from app.auth import get_admin

router = APIRouter(prefix="/clientes", tags=["Clientes"])
templates = Jinja2Templates(directory="app/templates")

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

    paginas.add(1)
    paginas.add(total_paginas)

    for i in range(
        max(1, pagina - limite),
        min(total_paginas, pagina + limite) + 1
    ):
        paginas.add(i)

    resultado = sorted(list(paginas))

    intervalo_com_dots = []
    anterior = None

    for p in resultado:

        if anterior is not None:

            if p - anterior == 2:
                intervalo_com_dots.append(anterior + 1)

            elif p - anterior > 2:
                intervalo_com_dots.append("...")

        intervalo_com_dots.append(p)

        anterior = p

    return intervalo_com_dots


@router.get("/")
def listar_clientes(
    request: Request,
    busca: str = "",
    apenas_associados: bool = False,
    pagina: int = 1,
    por_pagina: int = 2,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    # Query base
    query = db.query(Cliente)

    # Filtro por nome
    if busca:
        query = query.filter(
            Cliente.nome.ilike(f"%{busca}%")
        )

    # Filtro de associados
    if apenas_associados:
        query = query.filter(
            Cliente.is_associado == True
        )

    # Ordenação
    query = query.order_by(Cliente.nome)

    # Total de clientes depois dos filtros
    total_clientes = query.count()

    # Garante valores válidos
    pagina = max(pagina, 1)
    por_pagina = max(por_pagina, 1)

    # Calcula quantidade de páginas
    total_paginas = (
        math.ceil(total_clientes / por_pagina)
        if total_clientes
        else 1
    )

    # Evita acessar uma página inexistente
    if pagina > total_paginas:
        pagina = total_paginas

    # Calcula o deslocamento
    offset = (pagina - 1) * por_pagina

    # Busca somente os clientes da página atual
    clientes = (
        query
        .offset(offset)
        .limit(por_pagina)
        .all()
    )

    # Total de associados ativos
    total_associados = db.query(Cliente).filter(
        Cliente.is_associado == True,
        Cliente.ativo == True
    ).count()

    # Gera os números da paginação
    intervalo_paginas = gerar_intervalo_paginas(
        pagina,
        total_paginas
    )

    return templates.TemplateResponse(
        request,
        "clientes/index.html",
        {
            "request": request,
            "usuario": admin,
            "clientes": clientes,

            # Filtros
            "busca": busca,
            "apenas_associados": apenas_associados,

            # Informações da paginação
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total_clientes": total_clientes,
            "total_paginas": total_paginas,
            "intervalo_paginas": intervalo_paginas,

            # Outros dados
            "total_associados": total_associados,
        }
    )


@router.get("/novo")
def form_novo(request: Request, admin = Depends(get_admin)):
    return templates.TemplateResponse(
        request,
        "clientes/form.html",
        {"request": request, "usuario": admin, "editando": None}
    )


@router.post("/novo")
def criar(
    request: Request,
    nome: str          = Form(...),
    is_associado: bool = Form(False),
    db: Session        = Depends(get_db),
    admin              = Depends(get_admin)
):
    novo_cliente = Cliente(
        nome         = nome.strip(),
        is_associado = is_associado,
        ativo        = True
    )
    
    db.add(novo_cliente)
    db.commit()

    return RedirectResponse(url="/clientes?criado=ok", status_code=302)


@router.get("/{cliente_id}/editar")
def form_editar(
    cliente_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    editando = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not editando:
        return RedirectResponse(url="/clientes", status_code=302)

    return templates.TemplateResponse(
        request,
        "clientes/form.html",
        {"request": request, "usuario": admin, "editando": editando}
    )


@router.post("/{cliente_id}/editar")
def editar(
    cliente_id: int,
    nome: str          = Form(...),
    is_associado: bool = Form(False),
    db: Session        = Depends(get_db),
    admin              = Depends(get_admin)
):
    editando = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not editando:
        return RedirectResponse(url="/clientes", status_code=302)

    editando.nome         = nome.strip()
    editando.is_associado = is_associado
    db.commit()

    return RedirectResponse(url="/clientes?editado=ok", status_code=302)


@router.post("/{cliente_id}/toggle-ativo")
def toggle_ativo(
    cliente_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_admin)
):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if cliente:
        cliente.ativo = not cliente.ativo
        db.commit()
    return RedirectResponse(url="/clientes", status_code=302)