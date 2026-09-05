from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
import uvicorn
import json
import requests
import agent

def cargar_cfg(archivo: str = 'clientes.json') -> dict:
    """
    Lee un archivo JSON y carga la configuración de las barberías.
    
    Args:
        archivo (str): La ruta y nombre del archivo JSON de configuración. 
                       Por defecto asume 'clientes.json'.

    Returns:
        dict: Un diccionario conteniendo la configuración de los clientes.
              Si el archivo no existe, lo devuelve vacío.
    """
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{archivo}'")
        return {}
    
def simulador():
    """
    Simula la interfaz de WhatsApp en terminal.
    """
    print("📱 Simulador de WhatsApp")
    
    # Cargar clientes
    clientes = cargar_cfg()
    if not clientes:
        return

    # Simulamos a qué número de negocio estamos escribiendo
    numero = "5493412104851" 
    cfg = clientes.get(numero)
    
    if not cfg:
        print(f"Error: El número {numero} no está registrado en el sistema.")
        return

    print(f"Conectado a la línea de: {cfg['nombre']}")
    print("ENTER para finalizar conversación.\n")

    historial = []
    
    # Chat
    while True:
        mensaje_usuario = input("👤 Vos: ")
        
        if not mensaje_usuario.strip():
            print("👋 ¡Nos vemos!")
            break
        
        try:
            respuesta = agent.generar_respuesta(mensaje_usuario, cfg, historial)
            print(f"🤖 Bot: {respuesta}\n")
            
        except Exception as e:
            print(f"Error interno del bot: {str(e)}\n")

if __name__ == "__main__":
    simulador()