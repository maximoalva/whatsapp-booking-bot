import os
import json
import datetime
from groq import Groq, GroqError
from dotenv import load_dotenv
import google_api

# Variables de entorno (API Key)
load_dotenv()
cliente = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODELO_LLM = os.getenv("MODELO_LLM")

# Herramientas para el LLM
HERRAMIENTAS = [
    {
        "type": "function",
        "function": {
            "name": "obtener_servicios",
            "description": "Obtiene la lista de servicios y precios de la barbería.",
            "parameters": {
                "type": "object",
                "properties": {}, 
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_turnos_libres",
            "description": "Busca horarios disponibles para agendar un turno. Útil cuando el cliente pregunta por disponibilidad o dice 'para hoy', 'para mañana', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fecha": {
                        "type": "string",
                        "description": "La fecha exacta para buscar turnos en formato 'YYYY-MM-DD'. Deduce la fecha basándote en la fecha actual."
                    }
                },
                "required": ["fecha"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "agendar_turno",
            "description": "Agenda un turno en el calendario. Usar SOLO cuando el cliente ya confirmó explícitamente la fecha, la hora, su nombre y el servicio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fecha": {"type": "string", "description": "Formato 'YYYY-MM-DD'"},
                    "hora": {"type": "string", "description": "Formato 'HH:MM'"},
                    "cliente": {"type": "string", "description": "Nombre del cliente"},
                    "servicio": {"type": "string", "description": "Servicio elegido (ej: 'Corte y Barba')"}
                },
                "required": ["fecha", "hora", "cliente", "servicio"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancelar_turno",
            "description": "Cancela o anula un turno existente en el calendario. Usar SOLO cuando el cliente pide explícitamente cancelar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fecha": {"type": "string", "description": "Formato 'YYYY-MM-DD'"},
                    "hora": {"type": "string", "description": "Formato 'HH:MM'"},
                    "cliente": {"type": "string", "description": "Nombre del cliente"}
                },
                "required": ["fecha", "hora", "cliente"]
            }
        }
    }
]

# Agente
def generar_respuesta(mensaje_usuario: str, cfg: dict, historial: list) -> str:
    """
    Procesa el mensaje del usuario, administra el historial de la conversación 
    y orquesta la toma de decisiones del LLM junto con la ejecución de herramientas (APIs).

    Args:
        mensaje_usuario (str): El texto entrante enviado por el cliente.
        cfg (dict): Diccionario con la configuración del local (nombre, id_sheet, id_calendar, horarios, etc.).
        historial (list): Lista de diccionarios con los mensajes previos de la charla. 
                          Se modifica por referencia (in-place) para mantener el contexto.

    Returns:
        str: El texto final generado por el asistente virtual, listo para enviar al cliente.
    """
    tiempo_actual = datetime.datetime.now()
    
    if not historial:
        # Prompt del Sistema: Le da personalidad, reglas y contexto temporal
        prompt_sistema = f"""
        Sos el recepcionista virtual de {cfg.get('nombre', 'la barbería')}.
        Tu objetivo es atender clientes por WhatsApp de forma amable, clara y directa. Tratá de 'vos'.
        Hoy es {tiempo_actual.strftime('%A, %Y-%m-%d')} y la hora actual es {tiempo_actual.strftime('%H:%M')}.
        Reglas:
        1. Si piden precios o servicios, usá obtener_servicios.
        2. Si piden turnos, deducí la fecha y usá buscar_turnos_libres.
        3. Si van a agendar, confirmá que tenés su nombre, la fecha, la hora y el servicio ANTES de usar agendar_turno. Si falta un dato, preguntalo amablemente.
        4. Si piden CANCELAR, asegurate de tener la fecha, la hora exacta del turno y el nombre del cliente, y usá cancelar_turno.
        5. ESTRICTAMENTE PROHIBIDO pedir datos extra como teléfono, email o DNI.
        """
        historial.append({"role": "system", "content": prompt_sistema})
    
    historial.append({"role": "user", "content": mensaje_usuario})
    
    try:
        # Primera llamada: La IA piensa y decide qué hacer (Responder o usar herramienta)
        respuesta_inicial = cliente.chat.completions.create(
            model=MODELO_LLM, 
            messages=historial,
            tools=HERRAMIENTAS,
            tool_choice="auto"
        )

        respuesta = respuesta_inicial.choices[0].message

        # Si la IA decidió usar una herramienta, entra acá:
        if respuesta.tool_calls:
            historial.append(respuesta) # Guardar decisión en el historial
            
            for tool_call in respuesta.tool_calls:
                funcion = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                
                # Google API
                if funcion == "obtener_servicios":
                    resultado = google_api.obtener_servicios(cfg["id_sheet"])
                    
                elif funcion == "buscar_turnos_libres":
                    fecha_pedida = args.get("fecha")
                    fecha_obj = datetime.datetime.strptime(fecha_pedida, "%Y-%m-%d")
                    dia_semana_str = str(fecha_obj.isoweekday())
                    
                    # Buscar si la fecha exacta es feriado, sino usa horario normal
                    ventanas = cfg.get("feriados", {}).get(fecha_pedida)
                    if ventanas is None:
                        ventanas = cfg.get("horarios", {}).get(dia_semana_str, [])
                    
                    resultado = google_api.buscar_turnos_libres(
                        cfg["id_calendar"], fecha_pedida, ventanas, cfg["duracion_turno"]
                    )    
                    
                elif funcion == "agendar_turno":
                    resultado = google_api.agendar_turno(
                        cfg["id_calendar"], args.get("fecha"), args.get("hora"), 
                        args.get("cliente"), args.get("servicio"), cfg["duracion_turno"]
                    )
                    
                elif funcion == "cancelar_turno":
                    resultado = google_api.cancelar_turno(
                        cfg["id_calendar"], args.get("fecha"), args.get("hora"), 
                        args.get("cliente"), cfg["duracion_turno"]
                    )    

                # Devolvemos el resultado a la IA simulando que somos la función
                historial.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": funcion,
                    "content": json.dumps(resultado)
                })

            # Segunda llamada: La IA lee los datos crudos y arma la respuesta final
            respuesta_final = cliente.chat.completions.create(
                model=MODELO_LLM,
                messages=historial
            )
            
            texto_final = respuesta_final.choices[0].message.content
            
            # Guardar la respuesta final del bot en la memoria
            historial.append({"role": "assistant", "content": texto_final})
            
            return texto_final

        # Si no usó herramientas, devuelve el mensaje directamente
        texto_final = respuesta.content
        historial.append({"role": "assistant", "content": texto_final})
        
        return texto_final
    
    except GroqError as e:
        print(f"[Groq Error]: {e}")
        return "Disculpá, estoy experimentando una breve demora en el sistema. ¿Me repetís tu mensaje en un ratito?"
        
    except Exception as e:
        print(f"[Error Inesperado]: {e}")
        return "Ups, tuve un error técnico interno procesando tu solicitud. Por favor intentá de nuevo."