"""
Adaptador completo para el juego 3 en Raya (3-in-row)
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from pathlib import Path
import json
import uuid
import time
import random
from typing import Dict, List
import sys
import os

# --- CONFIGURACIÓN BÁSICA ---
app = FastAPI(
    title="3 en Raya Online",
    description="Juego clásico de 3 en raya para dos jugadores",
    version="1.0.0"
)

# Metadatos para el hub
app.game_title = "3 en Raya Online"
app.game_description = "Juega al clásico juego de 3 en raya con amigos en tiempo real"

# Directorios importantes
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Crear directorios si no existen
STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

# Configurar templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# --- LÓGICA COMPLETA DEL JUEGO ---
conexiones: Dict[str, WebSocket] = {}
jugador_sala: Dict[str, str] = {}

class SalaManager:
    def __init__(self):
        self.salas: Dict[str, Dict] = {}
    
    def crear_sala(self, clave: str, creador: str) -> str:
        sala_id = str(uuid.uuid4())[:8]
        self.salas[sala_id] = {
            "id": sala_id,
            "clave": clave,
            "jugadores": [creador],
            "simbolos": {creador: "X"},
            "tablero": [""] * 9,
            "turno": "X",
            "estado": "esperando",
            "ganador": None,
            "creador": creador,
            "timestamp": time.time(),
            "reinicio_pendiente": [],
            "marcador": {creador: 0},
            "partidas_jugadas": 0
        }
        print(f"✓ Sala creada: {sala_id} por {creador}")
        return sala_id
    
    def unir_sala(self, sala_id: str, clave: str, jugador: str) -> Dict:
        sala = self.salas.get(sala_id)
        if not sala:
            return {"exito": False, "mensaje": "Sala no encontrada"}
        if sala["clave"] != clave:
            return {"exito": False, "mensaje": "Clave incorrecta"}
        if len(sala["jugadores"]) >= 2:
            return {"exito": False, "mensaje": "Sala llena"}
        if jugador in sala["jugadores"]:
            return {"exito": False, "mensaje": "Ya estás en esta sala"}
            
        sala["jugadores"].append(jugador)
        sala["simbolos"][jugador] = "O"
        sala["marcador"][jugador] = 0
        
        if len(sala["jugadores"]) == 2:
            primer_turno = random.choice(["X", "O"])
            sala["turno"] = primer_turno
            sala["estado"] = "jugando"
            print(f"✓ Segundo jugador {jugador} unido. Turno inicial: {primer_turno}")
        
        return {"exito": True, "sala": sala}
    
    def obtener_simbolo_jugador(self, sala_id: str, jugador: str) -> str:
        sala = self.salas.get(sala_id)
        if not sala:
            return None
        return sala["simbolos"].get(jugador)
    
    def hacer_movimiento(self, sala_id: str, posicion: int, jugador: str) -> bool:
        sala = self.salas.get(sala_id)
        if not sala or sala["estado"] != "jugando":
            return False
        
        simbolo_jugador = self.obtener_simbolo_jugador(sala_id, jugador)
        if not simbolo_jugador or sala["turno"] != simbolo_jugador:
            return False
        
        if posicion < 0 or posicion > 8 or sala["tablero"][posicion] != "":
            return False
        
        sala["tablero"][posicion] = simbolo_jugador
        
        # Verificar ganador
        if self.verificar_ganador(sala["tablero"], simbolo_jugador):
            sala["estado"] = "terminado"
            sala["ganador"] = jugador
            sala["marcador"][jugador] = sala["marcador"].get(jugador, 0) + 1
            sala["partidas_jugadas"] += 1
            print(f"🎉 {jugador} gana la partida!")
        elif all(celda != "" for celda in sala["tablero"]):
            sala["estado"] = "empate"
            sala["partidas_jugadas"] += 1
            print("🤝 ¡Empate!")
        else:
            sala["turno"] = "O" if sala["turno"] == "X" else "X"
        
        return True
    
    def verificar_ganador(self, tablero: List[str], jugador: str) -> bool:
        lineas_ganadoras = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],
            [0, 3, 6], [1, 4, 7], [2, 5, 8],
            [0, 4, 8], [2, 4, 6]
        ]
        for linea in lineas_ganadoras:
            if all(tablero[pos] == jugador for pos in linea):
                return True
        return False
    
    def solicitar_reinicio(self, sala_id: str, jugador: str) -> Dict:
        """Solicitar reinicio de partida"""
        sala = self.salas.get(sala_id)
        if not sala:
            return {"exito": False, "mensaje": "Sala no encontrada"}
        
        if sala["estado"] not in ["terminado", "empate"]:
            return {"exito": False, "mensaje": "La partida no ha terminado"}
        
        if jugador not in sala["reinicio_pendiente"]:
            sala["reinicio_pendiente"].append(jugador)
            print(f"Jugador {jugador} solicita reinicio. Pendientes: {sala['reinicio_pendiente']}")
        
        # Verificar si ambos jugadores han aceptado el reinicio
        if len(sala["reinicio_pendiente"]) == 2:
            # Reiniciar partida
            self.reiniciar_partida(sala_id)
            return {"exito": True, "reiniciado": True, "sala": sala}
        else:
            # Encontrar quién falta por aceptar
            jugadores_faltantes = [j for j in sala["jugadores"] if j not in sala["reinicio_pendiente"]]
            return {"exito": True, "reiniciado": False, "faltante": jugadores_faltantes[0] if jugadores_faltantes else None}
    
    def reiniciar_partida(self, sala_id: str):
        """Reiniciar completamente la partida"""
        sala = self.salas.get(sala_id)
        if not sala:
            return
        
        # Limpiar tablero
        sala["tablero"] = [""] * 9
        
        # Reiniciar estado de reinicio
        sala["reinicio_pendiente"] = []
        
        # Intercambiar símbolos para dar ventaja al que perdió
        if sala["ganador"] and len(sala["jugadores"]) == 2:
            # El ganador anterior ahora será O, el perdedor será X
            ganador_anterior = sala["ganador"]
            perdedor = [j for j in sala["jugadores"] if j != ganador_anterior][0]
            
            sala["simbolos"][ganador_anterior] = "O"
            sala["simbolos"][perdedor] = "X"
            # El que perdió empieza (el que ahora tiene X)
            sala["turno"] = "X"
        else:
            # En caso de empate o primera partida, alternar aleatoriamente
            simbolos = ["X", "O"]
            random.shuffle(simbolos)
            for i, jugador in enumerate(sala["jugadores"]):
                sala["simbolos"][jugador] = simbolos[i]
            # El que tiene X empieza
            sala["turno"] = "X"
        
        sala["estado"] = "jugando"
        sala["ganador"] = None
        
        print(f"Partida reiniciada en sala {sala_id}. Nuevos símbolos: {sala['simbolos']}, Turno: {sala['turno']}")
    
    def obtener_info_sala(self, sala_id: str) -> Dict:
        return self.salas.get(sala_id)
    
    def obtener_salas_publicas(self) -> List[Dict]:
        ahora = time.time()
        salas_publicas = []
        
        for sala_id, sala in self.salas.items():
            es_valida = (
                ahora - sala["timestamp"] < 600 and
                len(sala["jugadores"]) < 2 and 
                sala["estado"] == "esperando"
            )
            
            if es_valida:
                salas_publicas.append({
                    "id": sala["id"],
                    "jugadores": sala["jugadores"],
                    "creador": sala["creador"],
                    "cantidad_jugadores": len(sala["jugadores"])
                })
        
        return salas_publicas
    
    def eliminar_sala(self, sala_id: str):
        """Eliminar una sala específica"""
        if sala_id in self.salas:
            del self.salas[sala_id]
            print(f"Sala {sala_id} eliminada")

sala_manager = SalaManager()

async def enviar_a_todos_en_sala(sala_id: str, mensaje: dict):
    """Envía un mensaje a todos los jugadores en una sala"""
    sala = sala_manager.obtener_info_sala(sala_id)
    if sala:
        for jugador in sala["jugadores"]:
            if jugador in conexiones:
                try:
                    await conexiones[jugador].send_text(json.dumps(mensaje))
                except Exception as e:
                    print(f"Error enviando a {jugador}: {e}")

# --- RUTAS DEL JUEGO ---

@app.get("/")
async def servir_juego(request: Request):
    """Servir la página principal del juego"""
    index_path = STATIC_DIR / "index.html"
    
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    else:
        return templates.TemplateResponse("game_fallback.html", {
            "request": request,
            "game_name": "3 en Raya"
        })

# WebSocket endpoint
@app.websocket("/ws/{sala_id}/{jugador}")
async def websocket_endpoint(websocket: WebSocket, sala_id: str, jugador: str):
    await websocket.accept()
    
    if jugador != "temp" and jugador != "salas":
        conexiones[jugador] = websocket
        jugador_sala[jugador] = sala_id
        print(f"👤 Jugador {jugador} conectado a WebSocket")
    
    try:
        while True:
            data = await websocket.receive_text()
            mensaje = json.loads(data)
            print(f"📩 Mensaje recibido de {jugador}: {mensaje['tipo']}")
            
            if mensaje["tipo"] == "crear_sala":
                clave = mensaje["clave"]
                jugador_nombre = mensaje.get("jugador", jugador)
                sala_id_nueva = sala_manager.crear_sala(clave, jugador_nombre)
                jugador_sala[jugador_nombre] = sala_id_nueva
                
                await websocket.send_text(json.dumps({
                    "tipo": "sala_creada",
                    "sala_id": sala_id_nueva
                }))
                print(f"✅ Sala creada: {sala_id_nueva} para {jugador_nombre}")
            
            elif mensaje["tipo"] == "unir_sala":
                clave = mensaje["clave"]
                jugador_nombre = mensaje.get("jugador", jugador)
                resultado = sala_manager.unir_sala(sala_id, clave, jugador_nombre)
                
                if resultado["exito"]:
                    sala = resultado["sala"]
                    simbolo_jugador = sala_manager.obtener_simbolo_jugador(sala_id, jugador_nombre)
                    jugador_sala[jugador_nombre] = sala_id
                    
                    await websocket.send_text(json.dumps({
                        "tipo": "unido_exitoso",
                        "sala": sala,
                        "tu_simbolo": simbolo_jugador
                    }))
                    
                    # Notificar a TODOS en la sala (incluyendo al creador)
                    await enviar_a_todos_en_sala(sala_id, {
                        "tipo": "estado_actualizado",
                        "sala": sala
                    })
                    print(f"✅ {jugador_nombre} se unió a sala {sala_id} como {simbolo_jugador}")
                else:
                    await websocket.send_text(json.dumps({
                        "tipo": "error",
                        "mensaje": resultado["mensaje"]
                    }))
                    print(f"❌ Error uniendo a sala: {resultado['mensaje']}")
            
            elif mensaje["tipo"] == "movimiento":
                sala_id_real = jugador_sala.get(jugador)
                if not sala_id_real:
                    await websocket.send_text(json.dumps({
                        "tipo": "error",
                        "mensaje": "No estás en ninguna sala"
                    }))
                    continue
                
                posicion = mensaje["posicion"]
                print(f"♟️  Movimiento de {jugador} en posición {posicion}, sala: {sala_id_real}")
                
                if sala_manager.hacer_movimiento(sala_id_real, posicion, jugador):
                    sala = sala_manager.obtener_info_sala(sala_id_real)
                    # Notificar a todos en la sala
                    await enviar_a_todos_en_sala(sala_id_real, {
                        "tipo": "actualizar_tablero",
                        "tablero": sala["tablero"],
                        "turno": sala["turno"],
                        "estado": sala["estado"],
                        "ganador": sala["ganador"],
                        "marcador": sala["marcador"],
                        "partidas_jugadas": sala["partidas_jugadas"]
                    })
                    print(f"✅ Movimiento procesado. Estado: {sala['estado']}, Turno: {sala['turno']}")
                else:
                    # Obtener información de debug para el error
                    sala = sala_manager.obtener_info_sala(sala_id_real)
                    simbolo_jugador = sala_manager.obtener_simbolo_jugador(sala_id_real, jugador)
                    
                    error_msg = f"Movimiento inválido. Turno actual: {sala['turno'] if sala else 'N/A'}, Tu símbolo: {simbolo_jugador}"
                    print(f"❌ Error movimiento: {error_msg}")
                    
                    await websocket.send_text(json.dumps({
                        "tipo": "error",
                        "mensaje": error_msg
                    }))
            
            elif mensaje["tipo"] == "solicitar_reinicio":
                # Obtener la sala REAL del jugador
                sala_id_real = jugador_sala.get(jugador)
                if not sala_id_real:
                    await websocket.send_text(json.dumps({
                        "tipo": "error",
                        "mensaje": "No estás en ninguna sala"
                    }))
                    continue
                
                resultado = sala_manager.solicitar_reinicio(sala_id_real, jugador)
                
                if resultado["exito"]:
                    if resultado.get("reiniciado"):
                        # Partida reiniciada, enviar nuevo estado a todos
                        sala = sala_manager.obtener_info_sala(sala_id_real)
                        await enviar_a_todos_en_sala(sala_id_real, {
                            "tipo": "partida_reiniciada",
                            "sala": sala,
                            "marcador": sala["marcador"]
                        })
                        print(f"🔄 Partida reiniciada en sala {sala_id_real}")
                    else:
                        # Solo un jugador ha aceptado, notificar a todos
                        sala = sala_manager.obtener_info_sala(sala_id_real)
                        await enviar_a_todos_en_sala(sala_id_real, {
                            "tipo": "reinicio_pendiente",
                            "solicitado_por": jugador,
                            "esperando_a": resultado["faltante"],
                            "reinicio_pendiente": sala["reinicio_pendiente"]
                        })
                        print(f"⏳ Reinicio pendiente en sala {sala_id_real}, esperando a {resultado['faltante']}")
                else:
                    await websocket.send_text(json.dumps({
                        "tipo": "error",
                        "mensaje": resultado["mensaje"]
                    }))
            
            elif mensaje["tipo"] == "obtener_estado":
                sala_id_real = jugador_sala.get(jugador)
                if sala_id_real:
                    sala = sala_manager.obtener_info_sala(sala_id_real)
                    if sala:
                        simbolo_jugador = sala_manager.obtener_simbolo_jugador(sala_id_real, jugador)
                        await websocket.send_text(json.dumps({
                            "tipo": "estado_actual",
                            "sala": sala,
                            "tu_simbolo": simbolo_jugador,
                            "marcador": sala["marcador"],
                            "partidas_jugadas": sala["partidas_jugadas"]
                        }))
            
            elif mensaje["tipo"] == "obtener_salas":
                salas_publicas = sala_manager.obtener_salas_publicas()
                await websocket.send_text(json.dumps({
                    "tipo": "lista_salas",
                    "salas": salas_publicas
                }))
                print(f"📋 Listado de salas enviado: {len(salas_publicas)} salas")
    
    except WebSocketDisconnect:
        print(f"👋 Jugador {jugador} desconectado")
        if jugador in conexiones:
            del conexiones[jugador]
        
        # Limpiar sala si está vacía
        sala_id_real = jugador_sala.get(jugador)
        if sala_id_real and jugador in jugador_sala:
            del jugador_sala[jugador]
            
            sala = sala_manager.obtener_info_sala(sala_id_real)
            if sala and jugador in sala["jugadores"]:
                sala["jugadores"].remove(jugador)
                if jugador in sala["simbolos"]:
                    del sala["simbolos"][jugador]
                if jugador in sala["marcador"]:
                    del sala["marcador"][jugador]
                if jugador in sala["reinicio_pendiente"]:
                    sala["reinicio_pendiente"].remove(jugador)
                
                # Si la sala queda vacía, eliminarla
                if not sala["jugadores"]:
                    sala_manager.eliminar_sala(sala_id_real)
                    print(f"🗑️  Sala {sala_id_real} eliminada por estar vacía")
                else:
                    # Notificar al otro jugador que se desconectó
                    await enviar_a_todos_en_sala(sala_id_real, {
                        "tipo": "jugador_desconectado",
                        "mensaje": f"El jugador {jugador} se ha desconectado"
                    })
                    print(f"⚠️  Jugador {jugador} desconectado de sala {sala_id_real}")

# Ruta para favicon
@app.get("/favicon.ico")
async def favicon():
    favicon_path = STATIC_DIR / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path)
    return RedirectResponse(url="/static/favicon.ico")

# Ruta para archivos estáticos específicos
@app.get("/{filename:path}")
async def servir_archivo(filename: str):
    """Servir archivos estáticos directamente"""
    file_path = STATIC_DIR / filename
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    return {"error": "Archivo no encontrado"}

# --- INICIALIZACIÓN ---

# Crear template de fallback si no existe
fallback_template = TEMPLATES_DIR / "game_fallback.html"
if not fallback_template.exists():
    with open(fallback_template, "w", encoding="utf-8") as f:
        f.write("""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{{ game_name }}</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0;
            padding: 20px;
        }
        .container { 
            background: white; 
            padding: 40px; 
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 500px;
        }
        h1 { color: #333; margin-bottom: 20px; }
        .error { 
            color: #e74c3c; 
            background: #ffeaea;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #e74c3c;
        }
        .btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            margin-top: 20px;
            transition: transform 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 {{ game_name }}</h1>
        <div class="error">
            ⚠️ El juego se está cargando desde el hub...
        </div>
        <p>Si ves este mensaje, es porque los archivos del juego están siendo procesados.</p>
        <a href="/" class="btn">← Volver al Hub de Juegos</a>
    </div>
</body>
</html>""")

print(f"✅ Juego '3-in-row' adaptado para el hub")
print(f"📁 Directorio: {BASE_DIR}")
print(f"🌐 Accesible en: /games/3-in-row")
print(f"🔌 WebSocket: /games/3-in-row/ws/")
print(f"📊 Estado: Listo para jugar")
