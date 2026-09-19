# AI WhatsApp Booking Bot

Asistente virtual inteligente desarrollado con Python e Inteligencia Artificial (LLMs) para automatizar la gestión de turnos y atención al cliente en barberías y salones. 

El bot entiende el contexto, mantiene memoria de la conversación y se integra directamente con la API Cloud oficial de WhatsApp (Meta) y el ecosistema de Google para leer precios y agendar o cancelar citas en tiempo real.

## Características principales

* **Procesamiento de Lenguaje Natural:** Capacidad para entender fechas relativas ("mañana a la tarde") e intenciones utilizando modelos de lenguaje avanzados vía Groq API (Llama 3 / Qwen).
* **Memoria Conversacional:** Mantiene el contexto de la charla para solicitar únicamente los datos faltantes sin reiniciar la conversación.
* **Integración con Google Calendar:** 
  * Búsqueda inteligente de disponibilidad cruzando horarios de atención, feriados y turnos ya ocupados.
  * Creación y cancelación automática de eventos (citas).
* **Integración con Google Sheets:** Lectura dinámica de la lista de servicios y precios actualizados.
* **Integración con WhatsApp Cloud API:** Recepción y envío de mensajes en tiempo real mediante Webhooks.

## 🛠️ Tecnologías utilizadas

## Tecnologías utilizadas

* **Lenguaje:** Python 3.14.7
* **Framework Web:** FastAPI, Uvicorn
* **Inteligencia Artificial:** Groq API (Agentic Function Calling / Tool Use)
* **APIs de Terceros:** Meta WhatsApp Cloud API, Google Calendar API, Google Sheets API
* **Infraestructura:** Ngrok 

## Instalación y uso

1. **Clonar el repositorio:**

   ```bash
   git clone https://github.com/maximoalva/whatsapp-booking-bot.git
   cd whatsapp-booking-bot
   ```
2. **Crear y activar entorno virtual:**

    ```bash
    python -m venv venv
    ```

    Linux/macOS:

    ```bash
    source venv/bin/activate
    ```

    Windows:

    ```bash
    venv\Scripts\activate
    ```

3. **Instalar dependencias:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Configurar variables de entorno y credenciales:**

    * Colocar el archivo `credenciales.json` (Google Service Account) en la raíz del proyecto.
    * Agregar archivo `clientes.json` con la configuración de tu negocio y sus IDs de Google Sheets y Calendar.
    * Crear un archivo `.env` en la raíz del proyecto con las siguientes variables:
       ```bash
       GROQ_API_KEY=tu_clave_de_groq
       MODELO_LLM=qwen-2.5-32b
       VERIFY_TOKEN=token_inventado_para_webhook
       WHATSAPP_TOKEN=token_de_acceso_meta
       TELEFONO_ID=id_del_numero_meta
       NGROK_AUTHTOKEN=tu_token_de_ngrok
       NUMERO_NEGOCIO=numero_id_en_clientes_json
       ```

5. **Ejecutar simulador local:**

    ```bash
    python main.py
    ```
    Al ejecutar este comando, se iniciará el servidor FastAPI en el puerto 8000 y se abrirá automáticamente un túnel Ngrok. La terminal mostrará la URL pública que debes configurar en Meta for Developers.

6. **Configurar Webhook en Meta:**

   * Dirigirse a Meta for Developers > WhatsApp > Configuración.
   * Pegar la URL proporcionada por Ngrok agregando `/webhook` al final.
   * Utilizar el `VERIFY_TOKEN` definido en tu archivo `.env`.
   * Suscribirse a los eventos de `messages`.
