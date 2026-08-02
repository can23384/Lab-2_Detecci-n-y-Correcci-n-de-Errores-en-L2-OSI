from __future__ import annotations

import csv
import random
import string
import sys
from pathlib import Path

# El emisor vive en el directorio padre de esta carpeta.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import emisor_crc32_hamming as emisor  # noqa: E402

ARCHIVO_SALIDA = "resultados.txt"

TAMANOS_CARACTERES = [4, 8, 16, 32, 64, 128]
PROBABILIDADES = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1]
ALGORITMOS = ["HAMMING", "CRC32", "AMBOS"]
REPETICIONES = 40

random.seed(42)


def generar_mensaje(cantidad_caracteres: int) -> str:
    alfabeto = string.ascii_letters + string.digits + " "
    return "".join(random.choice(alfabeto) for _ in range(cantidad_caracteres))


def decodificar_bloque_hamming_7_4(bloque: str) -> tuple[str, bool]:
    bits = [int(bit) for bit in bloque]

    s1 = bits[0] ^ bits[2] ^ bits[4] ^ bits[6]
    s2 = bits[1] ^ bits[2] ^ bits[5] ^ bits[6]
    s4 = bits[3] ^ bits[4] ^ bits[5] ^ bits[6]

    posicion_error = s1 + 2 * s2 + 4 * s4

    if posicion_error != 0:
        bits[posicion_error - 1] ^= 1

    datos = f"{bits[2]}{bits[4]}{bits[5]}{bits[6]}"

    return datos, posicion_error != 0


def decodificar_hamming_7_4(trama: str) -> tuple[str, int]:
    payload = ""
    bloques_corregidos = 0

    for inicio in range(0, len(trama), 7):
        bloque = trama[inicio:inicio + 7]
        datos, corregido = decodificar_bloque_hamming_7_4(bloque)
        payload += datos

        if corregido:
            bloques_corregidos += 1

    return payload, bloques_corregidos


def decodificar_ascii(bits: str) -> str:
    bytes_decimales = [
        int(bits[inicio:inicio + 8], 2)
        for inicio in range(0, len(bits), 8)
    ]

    if any(byte > 127 for byte in bytes_decimales):
        raise ValueError("Los datos no representan texto ASCII válido.")

    return bytes(bytes_decimales).decode("ascii").rstrip("\x00")


def simular_recepcion(
    algoritmo: str,
    trama_recibida: str,
) -> tuple[bool, int, bool]:
    """
    Replica la lógica del receptor real (JS) para poder correr miles de
    pruebas en un solo proceso. Devuelve:

    - exito_reportado: lo que el receptor concluiría con la información
      que tiene disponible (CRC y/o corrección Hamming).
    - bloques_corregidos: cantidad de bloques Hamming corregidos.
    - mensaje_decodificable: si el payload final es ASCII válido.
    """
    payload = trama_recibida
    bloques_corregidos = 0

    if algoritmo in ("HAMMING", "AMBOS"):
        payload, bloques_corregidos = decodificar_hamming_7_4(trama_recibida)

    exito_reportado = True

    if algoritmo in ("CRC32", "AMBOS"):
        datos = payload[:-32]
        crc_recibido = payload[-32:]
        crc_calculado = emisor.calcular_crc32(datos)
        exito_reportado = crc_recibido == crc_calculado
        payload = datos

    mensaje_decodificable = True

    if exito_reportado:
        try:
            decodificar_ascii(payload)
        except ValueError:
            mensaje_decodificable = False

    return exito_reportado, bloques_corregidos, mensaje_decodificable, payload


def ejecutar_prueba(
    algoritmo: str,
    probabilidad: float,
    cantidad_caracteres: int,
) -> dict[str, object]:
    mensaje = generar_mensaje(cantidad_caracteres)
    bits_originales = emisor.codificar_mensaje(mensaje)

    if algoritmo in ("CRC32", "AMBOS"):
        datos = emisor.agregar_padding(bits_originales)
    else:
        datos = bits_originales

    trama_sin_ruido = emisor.calcular_integridad(datos, algoritmo)

    trama_con_ruido, bits_alterados = emisor.aplicar_ruido(
        trama_sin_ruido,
        probabilidad,
    )

    (
        exito_reportado,
        bloques_corregidos,
        mensaje_decodificable,
        datos_recuperados,
    ) = simular_recepcion(algoritmo, trama_con_ruido)

    mensaje_correcto = (
        mensaje_decodificable
        and datos_recuperados == datos
    )

    overhead_bits = len(trama_sin_ruido) - len(bits_originales)
    overhead_pct = (overhead_bits / len(bits_originales)) * 100

    return {
        "algoritmo": algoritmo,
        "probabilidad": probabilidad,
        "caracteres_mensaje": cantidad_caracteres,
        "bits_datos": len(bits_originales),
        "bits_trama": len(trama_sin_ruido),
        "overhead_bits": overhead_bits,
        "overhead_pct": round(overhead_pct, 2),
        "bits_alterados": bits_alterados,
        "bloques_corregidos": bloques_corregidos,
        "exito_reportado": int(exito_reportado),
        "mensaje_correcto": int(mensaje_correcto),
    }


def main() -> None:
    columnas = [
        "algoritmo",
        "probabilidad",
        "caracteres_mensaje",
        "bits_datos",
        "bits_trama",
        "overhead_bits",
        "overhead_pct",
        "bits_alterados",
        "bloques_corregidos",
        "exito_reportado",
        "mensaje_correcto",
    ]

    total_pruebas = (
        len(ALGORITMOS)
        * len(PROBABILIDADES)
        * len(TAMANOS_CARACTERES)
        * REPETICIONES
    )

    print(f"Ejecutando {total_pruebas} pruebas...")

    ruta_salida = Path(__file__).resolve().parent / ARCHIVO_SALIDA

    with ruta_salida.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()

        contador = 0

        for algoritmo in ALGORITMOS:
            for probabilidad in PROBABILIDADES:
                for cantidad_caracteres in TAMANOS_CARACTERES:
                    for _ in range(REPETICIONES):
                        fila = ejecutar_prueba(
                            algoritmo,
                            probabilidad,
                            cantidad_caracteres,
                        )
                        escritor.writerow(fila)
                        contador += 1

    print(f"Listo. {contador} filas escritas en {ruta_salida}")


if __name__ == "__main__":
    main()
