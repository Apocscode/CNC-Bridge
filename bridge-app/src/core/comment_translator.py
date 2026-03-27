"""
CNC Bridge — G-code Comment Translator

Translates G-code comments between English and Spanish using a built-in
machining-specific dictionary. No internet required — all translations
are from a curated CNC/machining vocabulary.
"""

import re
import logging

logger = logging.getLogger(__name__)

# Bidirectional machining dictionary: English <-> Spanish
# Covers common CNC shop-floor terminology
_DICTIONARY = {
    # Operations
    "roughing": "desbaste",
    "finishing": "acabado",
    "drilling": "taladrado",
    "boring": "mandrinado",
    "tapping": "roscado",
    "reaming": "escariado",
    "facing": "refrentado",
    "pocketing": "cajera",
    "profiling": "perfilado",
    "chamfering": "achaflanado",
    "contouring": "contorneado",
    "threading": "roscado",
    "grooving": "ranurado",
    "slotting": "ranurado",
    "engraving": "grabado",
    "plunging": "plungeado",
    "ramping": "rampa",

    # Tools
    "tool": "herramienta",
    "tool change": "cambio de herramienta",
    "end mill": "fresa",
    "drill": "broca",
    "tap": "macho de roscar",
    "reamer": "escariador",
    "boring bar": "barra de mandrilar",
    "face mill": "fresa de planear",
    "ball end mill": "fresa de bola",
    "spot drill": "broca de centrar",
    "center drill": "broca de centrar",
    "chamfer mill": "fresa de chaflán",
    "insert": "inserto",
    "collet": "pinza",
    "holder": "portaherramientas",

    # Materials
    "aluminum": "aluminio",
    "steel": "acero",
    "stainless steel": "acero inoxidable",
    "cast iron": "hierro fundido",
    "brass": "latón",
    "copper": "cobre",
    "titanium": "titanio",
    "plastic": "plástico",
    "wood": "madera",

    # Machine parts
    "spindle": "husillo",
    "table": "mesa",
    "vise": "prensa",
    "clamp": "brida",
    "fixture": "utillaje",
    "coolant": "refrigerante",
    "flood coolant": "refrigerante por inundación",
    "mist coolant": "refrigerante por niebla",
    "chip": "viruta",
    "workpiece": "pieza",
    "part": "pieza",
    "stock": "material en bruto",
    "origin": "origen",
    "zero": "cero",
    "home": "inicio",
    "rapid": "rápido",
    "feed": "avance",
    "speed": "velocidad",
    "depth": "profundidad",
    "width": "ancho",
    "height": "altura",
    "diameter": "diámetro",
    "radius": "radio",
    "length": "longitud",
    "offset": "compensación",
    "clearance": "holgura",
    "retract": "retracción",

    # Actions / Status
    "start": "inicio",
    "stop": "parar",
    "pause": "pausa",
    "abort": "abortar",
    "safe start": "inicio seguro",
    "program start": "inicio de programa",
    "program end": "fin de programa",
    "end of program": "fin de programa",
    "tool table": "tabla de herramientas",
    "operation": "operación",
    "setup": "preparación",
    "first pass": "primera pasada",
    "final pass": "pasada final",
    "finish pass": "pasada de acabado",
    "rough pass": "pasada de desbaste",
    "spring pass": "pasada de limpieza",
    "contour": "contorno",
    "pocket": "cajera",
    "hole": "agujero",
    "slot": "ranura",
    "step": "escalón",
    "chamfer": "chaflán",
    "fillet": "redondeo",
    "surface": "superficie",
    "bottom": "fondo",
    "top": "parte superior",
    "side": "lado",
    "left": "izquierda",
    "right": "derecha",
    "front": "frente",
    "back": "atrás",
    "center": "centro",

    # Directions
    "clockwise": "sentido horario",
    "counterclockwise": "sentido antihorario",
    "up": "arriba",
    "down": "abajo",

    # Units
    "inches": "pulgadas",
    "inch": "pulgada",
    "millimeters": "milímetros",
    "millimeter": "milímetro",
    "ipm": "pulgadas/min",
    "rpm": "RPM",

    # Common comments
    "safe position": "posición segura",
    "retract to safe height": "retracción a altura segura",
    "spindle on": "husillo encendido",
    "spindle off": "husillo apagado",
    "coolant on": "refrigerante encendido",
    "coolant off": "refrigerante apagado",
    "move to start": "mover al inicio",
    "approach": "aproximación",
    "plunge": "inmersión",
    "return to zero": "retorno a cero",
    "done": "terminado",
    "complete": "completado",
    "warning": "advertencia",
    "caution": "precaución",
    "note": "nota",
    "check": "verificar",
    "verify": "verificar",
    "measure": "medir",
    "inspect": "inspeccionar",
}

# Build reverse dictionary (Spanish -> English)
_REVERSE = {v.lower(): k for k, v in _DICTIONARY.items()}


def _translate_phrase(text: str, dictionary: dict) -> str:
    """Translate a text string using dictionary, longest-match-first."""
    result = text
    # Sort by length descending to match longer phrases first
    sorted_keys = sorted(dictionary.keys(), key=len, reverse=True)
    lower = result.lower()
    for key in sorted_keys:
        idx = lower.find(key)
        if idx != -1:
            replacement = dictionary[key]
            # Preserve original case of first char
            if result[idx].isupper():
                replacement = replacement[0].upper() + replacement[1:]
            result = result[:idx] + replacement + result[idx + len(key):]
            lower = result.lower()
    return result


def translate_comment(comment_text: str, to_language: str = "es") -> str:
    """Translate a single comment string.
    
    Args:
        comment_text: The comment text (without parentheses)
        to_language: "es" for English->Spanish, "en" for Spanish->English
    
    Returns:
        Translated comment text
    """
    if to_language == "es":
        return _translate_phrase(comment_text, _DICTIONARY)
    else:
        return _translate_phrase(comment_text, _REVERSE)


def translate_gcode(gcode_text: str, to_language: str = "es") -> str:
    """Translate all comments in a G-code program.
    
    Only translates text inside parentheses `(...)`.
    All G-code commands are left unchanged.
    
    Args:
        gcode_text: Full G-code program text
        to_language: "es" for English->Spanish, "en" for Spanish->English
    
    Returns:
        G-code with translated comments
    """
    def replace_comment(match):
        inner = match.group(1)
        translated = translate_comment(inner, to_language)
        return f"({translated})"

    # Match comments in parentheses
    result = re.sub(r'\(([^)]+)\)', replace_comment, gcode_text)
    return result


def get_supported_languages() -> list[tuple[str, str]]:
    """Return list of (code, display_name) for supported languages."""
    return [
        ("en", "English"),
        ("es", "Español"),
    ]


def get_dictionary_size() -> int:
    """Return the number of terms in the dictionary."""
    return len(_DICTIONARY)
