"""
EXTRA — Manejo de CAPTCHAs
==========================
Un CAPTCHA es una barrera diseñada para frenar bots. NO se "rompe" por fuerza:
las estrategias legítimas son básicamente tres.

------------------------------------------------------------------------------
ESTRATEGIA 1 (la mejor): EVITARLO
------------------------------------------------------------------------------
Muchos CAPTCHAs solo aparecen cuando el sitio sospecha que eres un bot:
  - Vas demasiado rápido            -> baja el ritmo (DOWNLOAD_DELAY, sleep).
  - User-Agent de bot               -> usa uno de navegador real.
  - Sin cookies / sesión "humana"   -> reutiliza una sesión con login real.
  - ¿Hay una API por detrás (téc. 3)? La API normalmente NO tiene CAPTCHA.
Si scrapeas con calma y pareces un usuario normal, muchas veces ni aparece.

------------------------------------------------------------------------------
ESTRATEGIA 2: RESOLVERLO TÚ (semi-manual con Playwright)
------------------------------------------------------------------------------
Para volúmenes pequeños, abre un navegador NO headless, resuelve el CAPTCHA
a mano una vez, y deja que el script continúe con la sesión ya validada.
"""

# --- Ejemplo Estrategia 2: pausa para resolver a mano ---
def captcha_manual():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=False)  # visible a propósito
        pagina = navegador.new_page()
        pagina.goto("https://www.google.com/recaptcha/api2/demo")

        print("Resuelve el CAPTCHA en la ventana del navegador...")
        # Esperamos hasta que aparezca la marca de éxito (selector del sitio).
        # El usuario resuelve manualmente; el script espera sin hacer nada.
        pagina.wait_for_selector("#recaptcha-demo-submit", timeout=120_000)
        print("CAPTCHA resuelto. La sesión ya puede continuar automáticamente.")
        navegador.close()


# ------------------------------------------------------------------------------
# ESTRATEGIA 3: SERVICIO EXTERNO DE RESOLUCIÓN (de pago)
# ------------------------------------------------------------------------------
# Servicios como 2Captcha o Anti-Captcha resuelven el reto por ti (humanos o IA)
# y te devuelven el token. Tú lo inyectas en el formulario.
# Requiere:  pip install 2captcha-python   y una API key con saldo.
def captcha_servicio_externo(sitekey: str, url: str):
    """Esqueleto de uso de un solver externo (requiere API key real)."""
    from twocaptcha import TwoCaptcha  # parte del paquete 2captcha-python

    solver = TwoCaptcha("TU_API_KEY")
    resultado = solver.recaptcha(sitekey=sitekey, url=url)
    token = resultado["code"]
    # Ese 'token' se inyecta en el campo g-recaptcha-response del formulario
    # y luego se envía el formulario como siempre.
    return token


# ------------------------------------------------------------------------------
# NOTA LEGAL / ÉTICA
# ------------------------------------------------------------------------------
# - Respeta el robots.txt y los Términos de Servicio del sitio.
# - Saltarse CAPTCHAs en sitios de terceros puede violar sus términos.
# - Para PRACTICAR usa sitios pensados para ello (toscrape.com) o tus propios
#   sistemas (como tu dashboard de Kapso, donde tienes permiso).

if __name__ == "__main__":
    print(__doc__)
    print("Edita este archivo y descomenta la estrategia que quieras probar.")
    # captcha_manual()
