# Ponte de entrada do meu sistema
from fastapi import FastAPI, Request, Depends, status
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from app.auth import get_usuario_opcional

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
    usuario = Depends(get_usuario_opcional)
):
    # Tela não logado
    if usuario is None:
        return templates.TemplateResponse(
            request,
            "tela_inicio.html",
            {"request": request}
        )
    # Logado - exibir a tela de funcionario
    return templates.TemplateResponse(
        request,
        "home.html",
        {"request": request, "usuario": usuario}
    )