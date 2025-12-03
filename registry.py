"""
Sistema de registro automático de juegos
"""
import importlib
import pkgutil
from pathlib import Path
from fastapi import FastAPI

def discover_games():
    """Descubre y registra todos los juegos en la carpeta games/"""
    games = {}
    games_dir = Path(__file__).parent / "games"
    
    print(f"🔍 Buscando juegos en: {games_dir}")
    
    # Buscar todas las carpetas en games/ que tengan __init__.py
    for item in games_dir.iterdir():
        if item.is_dir() and not item.name.startswith('__') and not item.name.startswith('.'):
            game_name = item.name
            try:
                # Intentar importar el módulo del juego
                module_path = f"games.{game_name}"
                print(f"  Intentando cargar juego: {module_path}")
                
                game_module = importlib.import_module(module_path)
                
                # Buscar la app FastAPI en el módulo
                if hasattr(game_module, 'app'):
                    games[game_name] = game_module.app
                    print(f"  ✓ Juego '{game_name}' cargado exitosamente")
                else:
                    print(f"  ✗ Juego '{game_name}' no tiene 'app' FastAPI")
                    
            except ImportError as e:
                print(f"  ✗ Error importando juego '{game_name}': {e}")
            except Exception as e:
                print(f"  ✗ Error cargando juego '{game_name}': {e}")
    
    print(f"🎯 Total de juegos descubiertos: {len(games)}")
    return games