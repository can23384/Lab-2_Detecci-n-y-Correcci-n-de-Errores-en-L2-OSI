from __future__ import annotations

import random
import socket

# ============================================================
# CONFIGURACIÓN
# ============================================================
IP_RECEPTOR = "127.0.0.1"
PUERTO_RECEPTOR = 5000

# Polinomio generador de 33 bits para CRC-32.
CRC32_POLYNOMIAL = f"{0x104C11DB7:033b}"
MIN_DATA_BITS = 32

ALGORITMOS = {
    "1": "HAMMING",
    "2": "CRC32",
    "3": "AMBOS",
}


def solicitar_mensaje() -> str:
    """Capa de aplicación: solicita el texto a enviar."""
    while True:
        mensaje = input("Mensaje ASCII a enviar: ")

        if not mensaje:
            print("El mensaje no puede estar vacío.")
            continue

        try:
            mensaje.encode("ascii")
        except UnicodeEncodeError:
            print("Usa solamente caracteres ASCII (sin tildes, ñ ni emojis).")
            continue

        return mensaje


def solicitar_algoritmo() -> str:
    """Capa de aplicación: solicita el algoritmo para comprobar la integridad."""
    print("\n¿Qué algoritmo de integridad quieres usar?")
    print("  1) Hamming(7,4)  -- corrección de errores")
    print("  2) CRC-32        -- detección de errores")
    print("  3) Ambos         -- CRC-32 + Hamming(7,4)")

    while True:
        opcion = input("Elige una opción [1/2/3]: ").strip()

        if opcion in ALGORITMOS:
            return ALGORITMOS[opcion]

        print("Opción inválida. Escribe 1, 2 o 3.")


def solicitar_probabilidad_ruido() -> float:
    """Capa de ruido: solicita la tasa de error a aplicar sobre la trama."""
    print(
        "\n¿Con qué probabilidad se altera cada bit al transmitirlo? "
        "(ej. 0.01 = 1 error por cada 100 bits)"
    )

    while True:
        entrada = input("Probabilidad de ruido [0.0 - 1.0]: ").strip()

        try:
            probabilidad = float(entrada)
        except ValueError:
            print("Escribe un número decimal, por ejemplo 0.01.")
            continue

        if not 0.0 <= probabilidad <= 1.0:
            print("La probabilidad debe estar entre 0 y 1.")
            continue

        return probabilidad


def codificar_mensaje(mensaje: str) -> str:
    """Capa de presentación: convierte cada carácter ASCII en 8 bits."""
    return "".join(f"{byte:08b}" for byte in mensaje.encode("ascii"))


def agregar_padding(bits: str) -> str:
    """Agrega ceros al final si el mensaje tiene menos de 32 bits."""
    if len(bits) >= MIN_DATA_BITS:
        return bits

    return bits.ljust(MIN_DATA_BITS, "0")


def xor_bit(a: str, b: str) -> str:
    return "0" if a == b else "1"


def calcular_crc32(datos_bits: str) -> str:
    """Calcula un residuo CRC-32 de exactamente 32 bits."""
    if not datos_bits or any(bit not in "01" for bit in datos_bits):
        raise ValueError("Los datos deben ser una cadena binaria no vacía.")

    dividendo = list(datos_bits + ("0" * 32))

    for posicion in range(len(datos_bits)):
        if dividendo[posicion] == "1":
            for indice, bit_polinomio in enumerate(CRC32_POLYNOMIAL):
                destino = posicion + indice
                dividendo[destino] = xor_bit(
                    dividendo[destino],
                    bit_polinomio,
                )

    return "".join(dividendo[-32:])


def codificar_bloque_hamming_7_4(datos: str) -> str:
    """
    Codifica 4 bits usando Hamming(7,4) con paridad par.

    Posiciones:
    1=p1, 2=p2, 3=d1, 4=p4, 5=d2, 6=d3, 7=d4
    """
    if len(datos) != 4 or any(bit not in "01" for bit in datos):
        raise ValueError("Cada bloque de Hamming debe contener exactamente 4 bits.")

    d1, d2, d3, d4 = (int(bit) for bit in datos)

    p1 = d1 ^ d2 ^ d4
    p2 = d1 ^ d3 ^ d4
    p4 = d2 ^ d3 ^ d4

    return f"{p1}{p2}{d1}{p4}{d2}{d3}{d4}"


def codificar_hamming_7_4(payload: str) -> str:
    """Codifica el payload completo en bloques Hamming(7,4)."""
    if not payload or any(bit not in "01" for bit in payload):
        raise ValueError("El payload debe ser una cadena binaria no vacía.")

    if len(payload) % 4 != 0:
        raise ValueError("La longitud del payload debe ser múltiplo de 4.")

    return "".join(
        codificar_bloque_hamming_7_4(payload[inicio:inicio + 4])
        for inicio in range(0, len(payload), 4)
    )


def calcular_integridad(datos_bits: str, algoritmo: str) -> str:
    """
    Capa de enlace: aplica el/los algoritmo(s) de integridad elegidos y
    devuelve la trama final que se transmitirá.
    """
    if algoritmo == "CRC32":
        payload = datos_bits + calcular_crc32(datos_bits)
        return payload

    if algoritmo == "HAMMING":
        return codificar_hamming_7_4(datos_bits)

    # AMBOS: primero se agrega el CRC, luego se protege todo con Hamming.
    payload = datos_bits + calcular_crc32(datos_bits)
    return codificar_hamming_7_4(payload)


def aplicar_ruido(trama: str, probabilidad: float) -> tuple[str, int]:
    """Cambia cada bit de la trama con la probabilidad configurada."""
    if any(bit not in "01" for bit in trama):
        raise ValueError("La trama debe contener únicamente 0 y 1.")

    if not 0.0 <= probabilidad <= 1.0:
        raise ValueError("La probabilidad de ruido debe estar entre 0 y 1.")

    resultado: list[str] = []
    cantidad_cambios = 0

    for bit in trama:
        if random.random() < probabilidad:
            resultado.append("1" if bit == "0" else "0")
            cantidad_cambios += 1
        else:
            resultado.append(bit)

    return "".join(resultado), cantidad_cambios


def enviar_trama(host: str, puerto: int, algoritmo: str, trama: str) -> None:
    """
    Envía el modo de integridad usado (para que el receptor sepa cómo
    decodificar) seguido de la trama binaria. El cierre de la conexión
    marca el final del mensaje.
    """
    mensaje_saliente = f"{algoritmo}\n{trama}"

    try:
        with socket.create_connection((host, puerto), timeout=10) as cliente:
            cliente.sendall(mensaje_saliente.encode("ascii"))
    except ConnectionRefusedError as error:
        raise ConnectionError(
            "El receptor rechazó la conexión. Verifica que esté ejecutándose."
        ) from error
    except socket.timeout as error:
        raise TimeoutError(
            "La conexión con el receptor agotó el tiempo."
        ) from error
    except OSError as error:
        raise ConnectionError(f"Error de red: {error}") from error


def main() -> None:
    print("=== EMISOR TCP: CRC-32 + HAMMING(7,4) ===")

    mensaje = solicitar_mensaje()
    algoritmo = solicitar_algoritmo()
    probabilidad_ruido = solicitar_probabilidad_ruido()

    bits_originales = codificar_mensaje(mensaje)

    # El CRC-32 exige n > 32 bits (o padding si el mensaje es menor).
    if algoritmo in ("CRC32", "AMBOS"):
        datos = agregar_padding(bits_originales)
    else:
        datos = bits_originales

    trama_sin_ruido = calcular_integridad(datos, algoritmo)

    # El ruido se aplica sobre la trama que realmente viaja por el socket,
    # incluyendo los bits de redundancia (paridad y/o CRC).
    trama_con_ruido, bits_cambiados = aplicar_ruido(
        trama_sin_ruido,
        probabilidad_ruido,
    )

    overhead_bits = len(trama_sin_ruido) - len(bits_originales)
    overhead_pct = (overhead_bits / len(bits_originales)) * 100

    print("\n--- Resumen ---")
    print(f"Mensaje: {mensaje!r}")
    print(f"Algoritmo: {algoritmo}")
    print(f"Probabilidad de ruido: {probabilidad_ruido}")
    print(f"Datos binarios: {datos}")
    print(f"Trama sin ruido: {trama_sin_ruido}")
    print(f"Trama enviada: {trama_con_ruido}")
    print(f"Bits alterados por ruido: {bits_cambiados}")
    print(
        f"Overhead: {overhead_bits} bits "
        f"({overhead_pct:.1f}% sobre los datos originales)"
    )

    enviar_trama(IP_RECEPTOR, PUERTO_RECEPTOR, algoritmo, trama_con_ruido)

    print(
        f"\nTrama enviada correctamente a "
        f"{IP_RECEPTOR}:{PUERTO_RECEPTOR}"
    )


if __name__ == "__main__":
    try:
        main()
    except (ConnectionError, TimeoutError, ValueError) as error:
        print(f"Error: {error}")
