import ngrok
from dotenv import load_dotenv
 
def connect_ngrok() -> None:
    """
    Inicia el túnel de Ngrok usando el dominio estático gratuito.
    Requiere que NGROK_AUTHTOKEN esté definido en las variables de entorno.
    """
    load_dotenv()
    forwarder = ngrok.forward("localhost:8000", authtoken_from_env=True, domain="expediter-easing-wizard.ngrok-free.dev")
    print(f"Available at: {forwarder.url()}")
