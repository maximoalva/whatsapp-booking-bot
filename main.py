import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
import uvicorn
import json
import requests
import agent
from ngrok_tunnel import connect_ngrok

# Cargar variables de entorno
load_dotenv()

app = FastAPI(title="WhatsApp Booking Bot")

# Cargar configuración
try:
    with open('clientes.json', 'r', encoding='utf-8') as f:
        CLIENTES = json.load(f)
except FileNotFoundError:
    print(f"Error: No se encontró el archivo 'clientes.json'.")
    CLIENTES = {}
    
# Obtenemos el número del negocio desde el .env
numero = os.getenv("NUMERO_NEGOCIO")
cfg = CLIENTES.get(numero)

if not cfg:
    print(f"Advertencia: El número {numero} no está registrado en el sistema.")

# Memoria temporal en RAM (key: número de teléfono, value: historial)
memoria_usuarios = {}

# Tokens
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
TELEFONO_ID = os.getenv("TELEFONO_ID")

# Endpoint de verificación
@app.get("/webhook")
async def verificar_webhook(request: Request):
    """Endpoint para que Meta valide que somos los dueños del servidor."""
    hub_mode = request.query_params.get("hub.mode")
    hub_challenge = request.query_params.get("hub.challenge")
    hub_verify_token = request.query_params.get("hub.verify_token")

    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        print("✅ Webhook verificado correctamente por Meta.")
        return PlainTextResponse(content=hub_challenge, status_code=200)
    
    raise HTTPException(status_code=403, detail="Error de autenticación.")


# Endpoint de mensajes
@app.post("/webhook")
async def recibir_mensaje(request: Request):
    """Endpoint principal que recibe los mensajes de WhatsApp."""
    try:
        body = await request.json()
        
        # Navegamos por el JSON gigante que manda Meta para sacar el mensaje útil
        if "object" in body and body["object"] == "whatsapp_business_account":
            entry = body["entry"][0]
            changes = entry["changes"][0]
            value = changes["value"]
            
            if "messages" in value:
                mensaje_meta = value["messages"][0]
                
                # Datos del cliente
                numero_cliente = mensaje_meta["from"]
                texto_cliente = mensaje_meta["text"]["body"]
                
                print(f"\n👤 [{numero_cliente}] dice: {texto_cliente}")
                
                # Crear o recuperar la memoria de este cliente específico
                if numero_cliente not in memoria_usuarios:
                    memoria_usuarios[numero_cliente] = []
                
                # --- PASAMOS EL MENSAJE AL AGENTE (TU LÓGICA ACTUAL) ---
                respuesta_bot = agent.generar_respuesta(texto_cliente, cfg, memoria_usuarios[numero_cliente])
                print(f"🤖 Bot responde: {respuesta_bot}")
                
                # --- ENVIAR RESPUESTA A WHATSAPP ---
                enviar_mensaje_whatsapp(numero_cliente, respuesta_bot)

        return {"status": "ok"}
    except Exception as e:
        print(f"❌ Error interno: {e}")
        return {"status": "error"}

def enviar_mensaje_whatsapp(numero_destino: str, texto: str):
    """Función para pegarle a la API de Meta y devolver el mensaje al cliente."""
    url = f"https://graph.facebook.com/v17.0/{TELEFONO_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {"body": texto}
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

if __name__ == "__main__":
    print("Servidor FastAPI encendido en el puerto 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)