# controllers/pdv_controller.py — Ponto de Venda

# O PDV funciona assim:
# 1. GET /pdv        → tela com produtos + campo de cliente
# 2. O carrinho vive inteiro no JavaScript (sessionStorage)
# 3. POST /pdv/finalizar → recebe um JSON com os itens e os dados de pagamento
#                          cria Venda + ItensVenda + Pagamentos + baixa estoque
# ============================================================

import json
from typing import Optional
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.venda import Venda, ItemVenda, PagamentoVenda
from app.models.produto import Produto
from app.models.cliente import Cliente
from app.auth import get_usuario_logado

router = APIRouter(prefix="/pdv", tags=["PDV"])
templates = Jinja2Templates(directory="app/templates")

DESCONTO_ASSOCIADO = 10.0  # percentual fixo


# 🔒 FUNÇÃO AUXILIAR: Verifica com segurança se o utilizador atual é administrador
def verificar_eh_admin(usuario) -> bool:
    """Verifica se o utilizador logado tem permissão de administrador."""
    if not usuario:
        return False
    if isinstance(usuario, dict):
        is_adm = usuario.get("is_admin", False)
        username = str(usuario.get("username") or usuario.get("nome") or "").lower()
        cargo = str(usuario.get("cargo") or usuario.get("role") or "").lower()
        return bool(is_adm) or username == "admin" or cargo == "admin"

    is_adm = getattr(usuario, "is_admin", False)
    username = str(getattr(usuario, "username", getattr(usuario, "nome", "")) or "").lower()
    cargo = str(getattr(usuario, "cargo", getattr(usuario, "role", "")) or "").lower()
    return bool(is_adm) or username == "admin" or cargo == "admin"


@router.get("/")
def tela_pdv(
    request: Request,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado)
):
    """
    Carrega a tela do PDV com todos os produtos ativos
    e a lista de clientes para o campo de busca.
    """
    produtos  = (
        db.query(Produto)
        .filter(Produto.ativo == True, Produto.estoque_atual > 0)
        .order_by(Produto.nome)
        .all()
    )
    clientes  = (
        db.query(Cliente)
        .filter(Cliente.ativo == True)
        .order_by(Cliente.nome)
        .all()
    )

    # 🔒 VERIFICA SE O UTILIZADOR É ADMIN PARA EXIBIR/OCULTAR O DESCONTO MANUAL NO FRONT
    eh_admin = verificar_eh_admin(usuario)

    return templates.TemplateResponse(
        request,
        "pdv/index.html",
        {
            "request":             request,
            "usuario":             usuario,
            "produtos":            produtos,
            "clientes":            clientes,
            "desconto_associado":  DESCONTO_ASSOCIADO,
            "eh_admin":            eh_admin,  # 👈 Variável enviada para o template HTML
        }
    )


@router.post("/finalizar")
def finalizar_venda(
    request: Request,
    carrinho_json: str = Form(...),  # JSON serializado pelo JS
    forma_pagamento_1: str = Form(""),
    valor_pagamento_1: float = Form(0.0),
    forma_pagamento_2: str = Form(""),
    valor_pagamento_2: float = Form(0.0),
    cliente_id: int    = Form(0),    # 0 = sem cliente identificado
    desconto_manual: float = Form(0.0),  # Recebe o valor do desconto manual
    tipo_desconto: str = Form("RS"),     # 👈 ACRESCENTADO: Recebe se o desconto é em "RS" (R$) ou "PCT" (%)
    observacao: str    = Form(""),
    db: Session        = Depends(get_db),
    usuario            = Depends(get_usuario_logado)
):
    """
    Recebe o carrinho como JSON, valida pagamentos (1 ou 2) e persiste a venda.

    Formato esperado do carrinho_json:
    [
        {"produto_id": 1, "nome": "Caneta", "preco": 2.50, "quantidade": 3},
        {"produto_id": 2, "nome": "Caderno", "preco": 15.00, "quantidade": 1}
    ]
    """
    try:
        itens = json.loads(carrinho_json)
    except (json.JSONDecodeError, ValueError):
        return RedirectResponse(url="/pdv?erro=json", status_code=302)

    if not itens:
        return RedirectResponse(url="/pdv?erro=vazio", status_code=302)

    # Busca o cliente e verifica se é associado
    cliente             = None
    desconto_percentual = 0.0

    if cliente_id:
        cliente = db.query(Cliente).filter(
            Cliente.id == cliente_id,
            Cliente.ativo == True
        ).first()

        if cliente and cliente.is_associado:
            desconto_percentual = DESCONTO_ASSOCIADO

    # ── Valida estoque e calcula totais ──────────────────────
    total_bruto = 0.0
    itens_validados = []

    for item in itens:
        produto = db.query(Produto).filter(
            Produto.id == item["produto_id"],
            Produto.ativo == True
        ).with_for_update().first()

        if not produto:
            return RedirectResponse(
                url=f"/pdv?erro=produto_inexistente&id={item['produto_id']}",
                status_code=302
            )

        qtd = int(item["quantidade"])

        if qtd <= 0:
            return RedirectResponse(url="/pdv?erro=quantidade", status_code=302)

        if produto.estoque_atual < qtd:
            return RedirectResponse(
                url=f"/pdv?erro=estoque&produto={produto.nome}",
                status_code=302
            )

        subtotal    = produto.preco * qtd
        total_bruto += subtotal

        itens_validados.append({
            "produto":       produto,
            "quantidade":    qtd,
            "preco":         produto.preco,
            "produto_nome":  produto.nome,
        })

    # ── 🔴 CÁLCULO E TRAVA DE SEGURANÇA DO DESCONTO MANUAL (R$ OU %) ──
    desconto_associado_valor = total_bruto * (desconto_percentual / 100)
    val_manual = max(0.0, float(desconto_manual or 0.0))

    # 👈 ACRESCENTADO: Converte a percentagem em valor monetário se for do tipo %
    if tipo_desconto == "PCT":
        desconto_manual_val = total_bruto * (val_manual / 100.0)
    else:
        desconto_manual_val = val_manual

    # 🔴 BLOQUEIO NO BACK-END: Se o desconto manual for maior que o valor bruto, recusa a venda
    if desconto_manual_val > total_bruto:
        return RedirectResponse(
            url="/pdv?erro=desconto_maior_total",
            status_code=302
        )

    # Soma os dois descontos
    desconto_total_valor = desconto_associado_valor + desconto_manual_val

    # Garante que o desconto total acumulado não ultrapasse 100% do valor bruto
    if desconto_total_valor > total_bruto:
        desconto_total_valor = total_bruto

    # Calcula o valor líquido real com desconto
    total_liquido  = round(total_bruto - desconto_total_valor, 2)
    desconto_percentual_efetivo = (desconto_total_valor / total_bruto * 100) if total_bruto > 0 else 0.0

    # ── Valida formas de pagamento (Sprint 3) ────────────────
    pagamentos = []

    if forma_pagamento_1 and valor_pagamento_1 > 0:
        pagamentos.append({
            "forma": forma_pagamento_1,
            "valor": float(valor_pagamento_1)
        })

    if forma_pagamento_2 and valor_pagamento_2 > 0:
        pagamentos.append({
            "forma": forma_pagamento_2,
            "valor": float(valor_pagamento_2)
        })

    if not pagamentos:
        return RedirectResponse(url="/pdv?erro=sem_pagamento", status_code=302)

    soma_pagamentos = round(sum(p["valor"] for p in pagamentos), 2)

    # Valida se a soma dos pagamentos fecha exatamente o total líquido
    if abs(soma_pagamentos - total_liquido) > 0.01:
        return RedirectResponse(url="/pdv?erro=pagamento_divergente", status_code=302)

    # Captura o ID do utilizador com segurança
    usuario_id = usuario.get("id") if isinstance(usuario, dict) else getattr(usuario, "id", None) if usuario else None

    # ── Persiste tudo em uma única transação ─────────────────
    venda = Venda(
        cliente_id          = cliente_id or None,
        usuario_id          = usuario_id,
        desconto_percentual = round(desconto_percentual_efetivo, 2),
        total_bruto         = round(total_bruto, 2),
        total_liquido       = total_liquido,
        observacao          = observacao or None,
    )
    db.add(venda)
    db.flush()  # gera o venda.id sem commitar ainda

    for item in itens_validados:
        db.add(ItemVenda(
            venda_id       = venda.id,
            produto_id     = item["produto"].id,
            produto_nome   = item["produto_nome"],
            quantidade     = item["quantidade"],
            preco_unitario = item["preco"],
        ))
        # Baixa o estoque do produto
        item["produto"].estoque_atual -= item["quantidade"]

    # Salva os pagamentos registrados
    for pag in pagamentos:
        db.add(PagamentoVenda(
            venda_id        = venda.id,
            forma_pagamento = pag["forma"],
            valor           = pag["valor"]
        ))

    db.commit()

    return RedirectResponse(
        url=f"/pdv/venda/{venda.id}?sucesso=ok",
        status_code=302
    )


@router.get("/venda/{venda_id}")
def detalhe_venda(
    venda_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado)
):
    """Comprovante da venda — exibido imediatamente após finalizar."""
    venda = db.query(Venda).filter(Venda.id == venda_id).first()

    if not venda:
        return RedirectResponse(url="/pdv", status_code=302)

    return templates.TemplateResponse(
        request,
        "pdv/comprovante.html",
        {"request": request, "usuario": usuario, "venda": venda}
    )


@router.get("/historico")
def historico_vendas(
    request: Request,
    db: Session = Depends(get_db),
    usuario = Depends(get_usuario_logado)
):
    """Histórico de todas as vendas."""
    vendas = (
        db.query(Venda)
        .order_by(Venda.criado_em.desc())
        .limit(100)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "pdv/historico.html",
        {"request": request, "usuario": usuario, "vendas": vendas}
    )