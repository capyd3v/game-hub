"""
Hub de Juegos - Portal centralizado para múltiples juegos
"""
import importlib
import pkgutil
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import registry

app = FastAPI(
    title="Hub de Juegos",
    description="Portal centralizado para jugar a diferentes juegos online",
    version="1.0.0"
)

# Configurar templates
templates = Jinja2Templates(directory="templates")

# Montar archivos estáticos del hub
app.mount("/static/hub", StaticFiles(directory="static/hub"), name="hub_static")

# Registrar todos los juegos
games = registry.discover_games()

# Montar cada juego bajo su propia ruta
for game_name, game_app in games.items():
    app.mount(f"/games/{game_name}", game_app, name=game_name)
    print(f"✓ Juego registrado: {game_name} en /games/{game_name}")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Página principal del hub"""
    game_list = []
    for game_name, game_app in games.items():
        game_list.append({
            "name": game_name,
            "title": getattr(game_app, 'game_title', game_name.replace('_', ' ').title()),
            "description": getattr(game_app, 'game_description', "Juego divertido"),
            "path": f"/games/{game_name}"
        })
    
    return templates.TemplateResponse(
        "hub.html",
        {
            "request": request,
            "games": game_list,
            "total_games": len(games)
        }
    )

@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse(url="/static/hub/favicon.ico")

if __name__ == "__main__":
    import uvicorn
    print(f"\n🎮 Hub de Juegos iniciado!")
    print(f"📦 Juegos disponibles: {len(games)}")
    for game in games.keys():
        print(f"   → /games/{game}")
    print("\n👉 Abre http://localhost:8000 en tu navegador\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)