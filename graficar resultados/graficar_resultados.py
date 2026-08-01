from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


ARCHIVO_ENTRADA = "resultados.txt"


def leer_resultados(ruta: str) -> list[dict[str, int]]:
    """
    Lee un archivo con las columnas:

    bits_enviados,errores,correcciones,crc_valido
    """
    archivo = Path(ruta)

    if not archivo.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo: {archivo.resolve()}"
        )

    resultados: list[dict[str, int]] = []

    with archivo.open("r", encoding="utf-8", newline="") as contenido:
        lector = csv.DictReader(contenido)

        columnas_requeridas = {
            "bits_enviados",
            "errores",
            "correcciones",
            "crc_valido",
        }

        if lector.fieldnames is None:
            raise ValueError("El archivo está vacío.")

        columnas_encontradas = {
            columna.strip() for columna in lector.fieldnames
        }

        if not columnas_requeridas.issubset(columnas_encontradas):
            raise ValueError(
                "El archivo debe contener estas columnas: "
                "bits_enviados, errores, correcciones, crc_valido"
            )

        for numero_fila, fila in enumerate(lector, start=2):
            try:
                bits_enviados = int(fila["bits_enviados"])
                errores = int(fila["errores"])
                correcciones = int(fila["correcciones"])
                crc_valido = int(fila["crc_valido"])
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Datos inválidos en la fila {numero_fila}."
                ) from error

            if bits_enviados <= 0:
                raise ValueError(
                    f"Los bits enviados deben ser mayores que cero "
                    f"en la fila {numero_fila}."
                )

            if errores < 0 or correcciones < 0:
                raise ValueError(
                    f"Los errores y correcciones no pueden ser negativos "
                    f"en la fila {numero_fila}."
                )

            if crc_valido not in (0, 1):
                raise ValueError(
                    f"crc_valido debe ser 0 o 1 en la fila {numero_fila}."
                )

            resultados.append(
                {
                    "bits_enviados": bits_enviados,
                    "errores": errores,
                    "correcciones": correcciones,
                    "crc_valido": crc_valido,
                }
            )

    if not resultados:
        raise ValueError("El archivo no contiene resultados.")

    return resultados


def agrupar_resultados(
    resultados: list[dict[str, int]],
) -> dict[int, dict[str, float]]:
    """
    Agrupa las pruebas según la cantidad de bits enviados y calcula:

    - promedio de errores;
    - promedio de correcciones;
    - porcentaje de error;
    - porcentaje de transmisiones exitosas.
    """
    grupos: dict[int, list[dict[str, int]]] = defaultdict(list)

    for resultado in resultados:
        grupos[resultado["bits_enviados"]].append(resultado)

    resumen: dict[int, dict[str, float]] = {}

    for bits_enviados, pruebas in grupos.items():
        cantidad_pruebas = len(pruebas)

        total_errores = sum(
            prueba["errores"] for prueba in pruebas
        )

        total_correcciones = sum(
            prueba["correcciones"] for prueba in pruebas
        )

        total_exitos = sum(
            prueba["crc_valido"] for prueba in pruebas
        )

        promedio_errores = total_errores / cantidad_pruebas
        promedio_correcciones = (
            total_correcciones / cantidad_pruebas
        )

        # Porcentaje promedio de bits alterados respecto
        # del total de bits transmitidos.
        tasa_error = (
            total_errores
            / (bits_enviados * cantidad_pruebas)
            * 100
        )

        porcentaje_exito = (
            total_exitos / cantidad_pruebas * 100
        )

        resumen[bits_enviados] = {
            "pruebas": cantidad_pruebas,
            "promedio_errores": promedio_errores,
            "promedio_correcciones": promedio_correcciones,
            "tasa_error": tasa_error,
            "porcentaje_exito": porcentaje_exito,
        }

    return resumen


def mostrar_resumen(
    resumen: dict[int, dict[str, float]],
) -> None:
    print("\nResumen de resultados")
    print("-" * 81)
    print(
        f"{'Bits':>10} "
        f"{'Pruebas':>10} "
        f"{'Errores prom.':>16} "
        f"{'Tasa error':>14} "
        f"{'Éxito CRC':>14}"
    )
    print("-" * 81)

    for bits in sorted(resumen):
        datos = resumen[bits]

        print(
            f"{bits:>10} "
            f"{int(datos['pruebas']):>10} "
            f"{datos['promedio_errores']:>16.2f} "
            f"{datos['tasa_error']:>13.2f}% "
            f"{datos['porcentaje_exito']:>13.2f}%"
        )


def graficar_errores_por_tamano(
    resumen: dict[int, dict[str, float]],
) -> None:
    tamanos = sorted(resumen)

    errores_promedio = [
        resumen[tamano]["promedio_errores"]
        for tamano in tamanos
    ]

    plt.figure(figsize=(9, 5))
    plt.plot(tamanos, errores_promedio, marker="o")

    plt.title(
        "Errores promedio en función del tamaño de la trama"
    )
    plt.xlabel("Tamaño de la trama enviada (bits)")
    plt.ylabel("Cantidad promedio de bits alterados")
    plt.grid(True)
    plt.tight_layout()

    plt.savefig(
        "errores_por_tamano.png",
        dpi=300,
    )

    plt.show()


def graficar_exito_por_tamano(
    resumen: dict[int, dict[str, float]],
) -> None:
    tamanos = sorted(resumen)

    porcentaje_exito = [
        resumen[tamano]["porcentaje_exito"]
        for tamano in tamanos
    ]

    plt.figure(figsize=(9, 5))
    plt.plot(tamanos, porcentaje_exito, marker="o")

    plt.title(
        "Transmisiones exitosas en función del tamaño de la trama"
    )
    plt.xlabel("Tamaño de la trama enviada (bits)")
    plt.ylabel("Transmisiones con CRC válido (%)")
    plt.ylim(0, 105)
    plt.grid(True)
    plt.tight_layout()

    plt.savefig(
        "exito_crc_por_tamano.png",
        dpi=300,
    )

    plt.show()


def main() -> None:
    resultados = leer_resultados(ARCHIVO_ENTRADA)
    resumen = agrupar_resultados(resultados)

    mostrar_resumen(resumen)
    graficar_errores_por_tamano(resumen)
    graficar_exito_por_tamano(resumen)

    print("\nGráficas guardadas:")
    print("- errores_por_tamano.png")
    print("- exito_crc_por_tamano.png")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}")