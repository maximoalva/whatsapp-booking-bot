import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import datetime

# Configuración de credenciales
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/calendar'
]
credenciales = Credentials.from_service_account_file('credenciales.json', scopes=SCOPES)

# Google Sheets
def obtener_servicios(id_planilla: str) -> list[dict]:
    """
    Se conecta a Google Sheets y extrae los datos de la primera hoja.
    
    Args:
        id_planilla (str): El ID del documento de Google Sheets.

    Returns:
        list[dict]: Una lista de diccionarios donde cada elemento representa una fila de la planilla.
    """
    cliente = gspread.authorize(credenciales)
    hoja = cliente.open_by_key(id_planilla).sheet1
    registros = hoja.get_all_records() 
    
    return registros

# Google Calendar
def buscar_turnos_libres(id_calendario: str, fecha: str, ventanas: list[dict], duracion_turno: int)-> list[str]:
    """
    Busca los eventos del día en el Calendar y devuelve una lista de horarios libres
    basado en las ventanas de atención y la duración de los turnos.
    
    Args:
        id_calendario (str): El ID del Google Calendar.
        fecha (str): Fecha a consultar en formato 'YYYY-MM-DD'.
        ventanas (list[dict]): Las ventanas son diccionarios con claves 'apertura' y 'cierre' con los horarios en formato 'HH:MM' como valor
        duracion_turno (int): Entero con los minutos que dura un turno.

    Returns:
        list[str]: Lista con los horarios disponibles en formato 'HH:MM'. Si no hay turnos disponibles la devuelve vacía.
    """
    # Si el local está cerrado
    if not ventanas:
        return []

    servicio_calendar = build('calendar', 'v3', credentials=credenciales)
    
    # El rango de búsqueda irá desde la primera apertura hasta el último cierre del día
    inicio = f"{fecha}T{ventanas[0]['apertura']}:00-03:00" 
    fin = f"{fecha}T{ventanas[-1]['cierre']}:00-03:00"
    
    # Eventos (turnos ocupados)
    consulta_api = servicio_calendar.events().list(
        calendarId=id_calendario, timeMin=inicio, timeMax=fin,
        singleEvents=True, orderBy='startTime').execute()
    eventos = consulta_api.get('items', [])
    
    # Obtener el reloj actual (para evitar dar turnos del pasado)
    tiempo_actual = datetime.datetime.now()
    
    # Generar turnos basado en las ventanas y la duración del turno
    turnos_posibles = []
    
    for v in ventanas:
        tiempo_x = datetime.datetime.strptime(f"{fecha} {v['apertura']}", "%Y-%m-%d %H:%M")
        tiempo_fin = datetime.datetime.strptime(f"{fecha} {v['cierre']}", "%Y-%m-%d %H:%M")
        
        # Mientras el inicio del turno + la duración no supere la hora de cierre
        while tiempo_x + datetime.timedelta(minutes=duracion_turno) <= tiempo_fin:
            # Solo agregamos el horario si es en el futuro 
            if tiempo_x > tiempo_actual:
                turnos_posibles.append(tiempo_x.strftime("%H:%M"))
            
            # Avanzamos el reloj para calcular el siguiente turno
            tiempo_x += datetime.timedelta(minutes=duracion_turno)
            
    # Filtrar los turnos que ya están ocupados en Calendar
    turnos_libres = []
    
    for turno in turnos_posibles:
        # Convertimos nuestro turno a objetos datetime reales para comparar bien
        inicio_turno = datetime.datetime.strptime(f"{fecha} {turno}", "%Y-%m-%d %H:%M")
        fin_turno = inicio_turno + datetime.timedelta(minutes=duracion_turno)
        
        ocupado = False
        
        for evento in eventos:
            # Detectar si hay un evento de "Todo el día" (vacaciones) y descartar
            if 'date' in evento['start'] and 'dateTime' not in evento['start']:
                ocupado = True
                break
                
            # Si es un evento normal, extraer inicio y fin
            inicio_evento = datetime.datetime.strptime(evento['start']['dateTime'][:16], "%Y-%m-%dT%H:%M")
            fin_evento = datetime.datetime.strptime(evento['end']['dateTime'][:16], "%Y-%m-%dT%H:%M")
            
            # Verificar solapamiento
            if inicio_turno < fin_evento and fin_turno > inicio_evento:
                ocupado = True
                break
                
        if not ocupado:
            turnos_libres.append(turno)
            
    return turnos_libres

def agendar_turno(id_calendario: str, fecha: str, hora: str, cliente: str, servicio: str, duracion_turno: int) -> dict[str, str]:
    """
    Crea un evento en Google Calendar.
    
    Args:
        id_calendario (str): El ID del Google Calendar.
        fecha_str (str): Fecha del turno en formato 'YYYY-MM-DD'.
        hora_str (str): Hora de inicio en formato 'HH:MM'.
        cliente (str): Nombre del cliente para el título del evento.
        servicio (str): Nombre del servicio para el título del evento.
        duracion_turno (int): Entero con los minutos que dura un turno.

    Returns:
        dict: Un diccionario con el estado de la operación.
              Ej: {"status": "success", "mensaje": "Turno agendado correctamente"}
    """
    servicio_calendar = build('calendar', 'v3', credentials=credenciales)
    
    # Calcular tiempo de inicio y fin como objetos datetime reales
    tiempo_inicio = datetime.datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
    tiempo_fin = tiempo_inicio + datetime.timedelta(minutes=duracion_turno)
    
    # Convertir al formato de texto estricto que exige Google (ISO 8601)
    inicio = f"{fecha}T{tiempo_inicio.strftime('%H:%M')}:00-03:00"
    fin = f"{fecha}T{tiempo_fin.strftime('%H:%M')}:00-03:00"

    evento = {
      'summary': f'{servicio} - {cliente}',
      'description': f'Turno agendado por WhatsApp vía Barbershop Chatbot. Cliente: {cliente}',
      'start': {
        'dateTime': inicio,
        'timeZone': 'America/Argentina/Buenos_Aires',
      },
      'end': {
        'dateTime': fin,
        'timeZone': 'America/Argentina/Buenos_Aires',
      },
    }

    try:
        # Ejecutar la inserción en Google Calendar
        servicio_calendar.events().insert(calendarId=id_calendario, body=evento).execute()
        return {"status": "success", "mensaje": f"Turno agendado para {cliente} a las {hora}hs."}
    except Exception as e:
        # Si falla Google
        return {"status": "error", "mensaje": str(e)}
    
def cancelar_turno(id_calendario: str, fecha: str, hora: str, cliente: str, duracion_turno: int) -> dict[str, str]:
    """
    Busca y elimina un evento en Google Calendar.
    
    Args:
        id_calendario (str): El ID del Google Calendar.
        fecha (str): Fecha del turno a cancelar en formato 'YYYY-MM-DD'.
        hora (str): Hora de inicio en formato 'HH:MM'.
        cliente (str): Nombre del cliente.
        duracion_turno (int): Minutos que dura el turno para calcular la ventana de búsqueda.

    Returns:
        dict: Un diccionario con el estado de la operación.
    """
    servicio_calendar = build('calendar', 'v3', credentials=credenciales)
    
    # Calcular tiempo de inicio y fin como objetos datetime reales
    tiempo_inicio = datetime.datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
    tiempo_fin = tiempo_inicio + datetime.timedelta(minutes=duracion_turno)
    
    # Convertir al formato de texto estricto que exige Google (ISO 8601)
    inicio = f"{fecha}T{tiempo_inicio.strftime('%H:%M')}:00-03:00"
    fin = f"{fecha}T{tiempo_fin.strftime('%H:%M')}:00-03:00"
    
    try:
        # Buscar el evento que arranca en ese horario
        consulta = servicio_calendar.events().list(
            calendarId=id_calendario, timeMin=inicio, timeMax=fin,
            singleEvents=True, orderBy='startTime').execute()
        
        eventos = consulta.get('items', [])
        
        if not eventos:
            return {"status": "error", "mensaje": "No encontré ningún turno agendado en ese día y horario."}
        
        # Tomamos el primer evento que coincida
        evento_a_borrar = eventos[0]
        id_evento = evento_a_borrar['id']
        
        # Borrar el evento usando su ID
        servicio_calendar.events().delete(calendarId=id_calendario, eventId=id_evento).execute()
        
        return {"status": "success", "mensaje": f"El turno de las {hora}hs fue cancelado correctamente."}
        
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}