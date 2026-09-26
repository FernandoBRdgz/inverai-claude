import random

# Lógica de negocio: lista de saludos del asistente (migrada desde el cliente).
# Antes vivía como un array de JavaScript en chat.html; ahora es el servidor
# quien decide la respuesta, para que el frontend dependa de una API real.
SALUDOS = [
    "¡Hola! Un placer atenderle. 🤝",
    "Buenos días, ¿en qué puedo asesorarle hoy? 💼",
    "Buenas tardes, quedo a su disposición. 📈",
    "Buenas noches, gracias por su confianza. 🌙",
    "¡Saludos! Estoy para servirle. 🖋️",
    "Bienvenido, será un gusto ayudarle. 🏦",
    "Un cordial saludo, cuénteme en qué le apoyo. 🤝",
    "¡Hola! Gracias por escribir, aquí estoy. 📊",
]


def saludo_aleatorio() -> str:
    """Elige un saludo al azar de la lista de saludos del asistente."""
    return random.choice(SALUDOS)
