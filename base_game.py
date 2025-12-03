"""
Clase base para todos los juegos
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

class BaseGame:
    """Interfaz base que todos los juegos deben implementar"""
    
    def __init__(self, name: str, title: str = None, description: str = None):
        self.name = name
        self.title = title or name.replace('_', ' ').title()
        self.description = description or "Un juego divertido"
        
        # Crear app FastAPI para este juego
        self.app = FastAPI(
            title=self.title,
            description=self.description
        )
        
        # Configurar rutas estáticas del juego
        self._setup_static_files()
        
    def _setup_static_files(self):
        """Configurar archivos estáticos del juego"""
        game_dir = Path(__file__).parent / "games" / self.name
        
        # Montar archivos estáticos si existen
        static_dir = game_dir / "static"
        if static_dir.exists():
            self.app.mount("/static", StaticFiles(directory=str(static_dir)), name=f"{self.name}_static")
            
    def get_routes(self):
        """Obtener información de rutas del juego (para el hub)"""
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "path": f"/games/{self.name}"
        }