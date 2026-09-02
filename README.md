# AI WhatsApp Booking Bot

Asistente virtual inteligente desarrollado con Python e Inteligencia Artificial (LLMs) para automatizar la gestión de turnos y atención al cliente en barberías y salones. 

El bot simula una conversación natural, entiende el contexto, recuerda mensajes previos y se integra directamente con el ecosistema de Google para leer precios y agendar o cancelar citas en tiempo real.

## Características principales

* **Procesamiento de Lenguaje Natural:** Capacidad para entender fechas relativas ("mañana a la tarde") e intenciones utilizando modelos de lenguaje avanzados vía Groq API (Llama 3.1 / Qwen).
* **Memoria Conversacional:** Mantiene el contexto de la charla para solicitar únicamente los datos faltantes sin reiniciar la conversación.
* **Integración con Google Calendar:** 
  * Búsqueda inteligente de disponibilidad cruzando horarios de atención, feriados y turnos ya ocupados.
  * Creación y cancelación automática de eventos (citas).
* **Integración con Google Sheets:** Lectura dinámica de la lista de servicios y precios actualizados.

## Tecnologías utilizadas

* **Lenguaje:** Python 3.14.7
* **Inteligencia Artificial:** Groq API (Agentic Function Calling / Tool Use)
* **APIs de Terceros:** Google Calendar API, Google Sheets API
* **Autenticación:** Google Service Accounts (OAuth2)

## Instalación y uso

1. **Clonar el repositorio:**

   ```bash
   git clone [https://github.com/maximoalva/whatsapp-booking-bot.git](https://github.com/maximoalva/whatsapp-booking-bot.git)
   cd whatsapp-booking-bot
   ```
2. **Crear y activar entorno virtual:**

    ```bash
    python -m venv env
    ```

    Linux/macOS:

    ```bash
    source env/bin/activate
    ```

    Windows:

    ```bash
    env\Scripts\activate
    ```

3. **Instalar dependencias:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Configurar variables de entorno y credenciales:**

    * Colocar el archivo `credenciales.json` (Google Service Account) en la raíz del proyecto.
    * Agregar archivo `.env` con tu API Key de Groq en la raíz del proyecto.
    * Agregar archivo `clientes.json` con tus IDs de Google Sheets y Calendar.

5. **Ejecutar simulador local:**

    ```bash
    python main.py
    ```