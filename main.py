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
    print(f"[Config Error]: No se encontró el archivo 'clientes.json'.")
    CLIENTES = {}
    
# Obtenemos el número del negocio desde el .env
numero = os.getenv("NUMERO_NEGOCIO")
cfg = CLIENTES.get(numero)

if not cfg:
    print(f"[Config Warning]: El número {numero} no está registrado en el sistema.")

# Memoria temporal en RAM (key: número de teléfono, value: historial)
memoria_usuarios = {}

# Tokens
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
TELEFONO_ID = os.getenv("TELEFONO_ID")

# Endpoint de verificación
@app.get("/webhook")
async def verificar_webhook(request: Request):
    """
    Endpoint GET para que Meta valide la propiedad del servidor.
    
    Args:
        request (Request): Objeto de petición FastAPI que contiene los parámetros de consulta enviados por Meta.
        
    Returns:
        PlainTextResponse: El 'hub.challenge' devuelto en texto plano si el token es correcto.
    """
    hub_mode = request.query_params.get("hub.mode")
    hub_challenge = request.query_params.get("hub.challenge")
    hub_verify_token = request.query_params.get("hub.verify_token")

    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        print("[Webhook]: verificado correctamente por Meta.")
        return PlainTextResponse(content=hub_challenge, status_code=200)
    
    print("[Webhook Error]: Falló la autenticación del token de verificación.")
    raise HTTPException(status_code=403, detail="Error de autenticación.")


# Endpoint de mensajes
@app.post("/webhook")
async def recibir_mensaje(request: Request):
    """
    Endpoint POST. Recibe y procesa los eventos entrantes de la API de WhatsApp.
    Filtra los eventos de estado (entregado/leído) y envía los mensajes de texto al Agente LLM.
    
    Args:
        request (Request): Objeto de petición FastAPI que contiene el JSON que envía Meta con el mensaje o estado.
                           
    Returns:
        dict: Un diccionario JSON confirmando la recepción para que Meta no reintente enviar el mensaje.
    """
    try:
        body = await request.json()
        
        if "object" in body and body["object"] == "whatsapp_business_account":
            entry = body["entry"][0]
            changes = entry["changes"][0]
            value = changes["value"]
            
            # Verificamos que sea un mensaje y no una notificación de lectura/estado
            if "messages" in value:
                mensaje_meta = value["messages"][0]
                numero_cliente = mensaje_meta["from"]
                tipo_mensaje = mensaje_meta.get("type", "")
                
                # Audios
                if tipo_mensaje == "audio":
                    respuesta_audio = "¡Hola! Por el momento solo puedo leer mensajes de texto. ¿Podrías escribir tu consulta? 😊"
                    print(f"\n👤 [{numero_cliente}]: [Audio]")
                    print(f"🤖 [Bot]: {respuesta_audio}")
                    enviar_mensaje_whatsapp(numero_cliente, respuesta_audio)
                    return {"status": "ok", "reason": "audio_handled"}
                
                # Ignoramos cualquier otra cosa que no sea texto (imágenes, stickers, documentos)
                if tipo_mensaje != "text":
                    print(f"\n👤 [{numero_cliente}]: [Archivo multimedia/sticker ignorado]")
                    return {"status": "ignored", "reason": "not_a_text_message"}
                
                # Texto
                texto_cliente = mensaje_meta["text"]["body"]
                
                print(f"\n👤 [{numero_cliente}]: {texto_cliente}")
                
                # Crear o recuperar la memoria de este cliente específico
                if numero_cliente not in memoria_usuarios:
                    memoria_usuarios[numero_cliente] = []
                
                # Procesamiento LLM
                respuesta_bot = agent.generar_respuesta(texto_cliente, cfg, memoria_usuarios[numero_cliente])
                print(f"🤖 [Bot]: {respuesta_bot}")
                
                # Enviar respuesta a WhatsApp
                enviar_mensaje_whatsapp(numero_cliente, respuesta_bot)

        return {"status": "ok"}
    
    except KeyError as e:
        print(f"[Webhook Error]: {e}")
        return {"status": "error"}
    except Exception as e:
        print(f"[Internal Error]: {e}")
        return {"status": "error"}
    
def normalizar_numero_test(numero: str) -> str:
    """
    Normaliza números de teléfono argentinos para esquivar el bug del sandbox de Meta.
    Convierte el formato internacional con '9' (ej: 549341...) al formato local 
    con '15' (ej: 5434115...) exigido por la lista de números de prueba de Meta.
    
    Args:
        numero (str): El número de teléfono entrante en formato crudo de WhatsApp.

    Returns:
        str: El número modificado si es un celular argentino, o el número original intacto en caso contrario.
    """
    if numero.startswith("549") and len(numero) == 13:
        # Extraemos el código de área (ej: 341) y el número, y le metemos el 15
        codigo_area = numero[3:6]
        numero_local = numero[6:]
        return f"54{codigo_area}15{numero_local}"
    return numero

def enviar_mensaje_whatsapp(numero_destino: str, texto: str):
    """
    Realiza una petición HTTP POST a la Graph API de Meta para enviar un mensaje de texto al cliente.

    Args:
        numero_destino (str): El número de teléfono del cliente (extraído del mensaje original).
        texto (str): El contenido del mensaje generado por el Agente LLM.

    Returns:
        dict: Un diccionario JSON con la respuesta oficial de la API de Meta. Contiene el 'message_id' 
              en caso de éxito, o detalles del error (código y mensaje) en caso de fallo.
    """
    numero_destino = normalizar_numero_test(numero_destino)
    
    url = f"https://graph.facebook.com/v25.0/{TELEFONO_ID}/messages"
    
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
    
    if response.status_code != 200:
        print(f"[Meta Error]: Status {response.status_code} - {response.text}")
    
    return response.json()

if __name__ == "__main__":
    print("[Sistema]: Levantando túnel Ngrok...")
    connect_ngrok()
    
    print("[Sistema]: Servidor FastAPI encendido en el puerto 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)