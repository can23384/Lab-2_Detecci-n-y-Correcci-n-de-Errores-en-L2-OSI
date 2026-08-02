from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

ARCHIVO_ENTRADA = "resultados.txt"

ALGORITMOS = ["HAMMING", "CRC32", "AMBOS"]
COLORES = {"HAMMING": "tab:blue", "CRC32": "tab:orange", "AMBOS": "tab:green"}

# Valores de referencia usados para "congelar" una variable mientras se
# grafica el efecto de otra (p. ej. tamaño fijo al variar la probabilidad).
PROBABILIDAD_REFERENCIA = 0.01
TAMANO_REFERENCIA = 64


def leer_resultados(ruta: str) -> list[dict[str, float]]:
    """
    Lee el CSV generado por pruebas_experimentales.py con las columnas:

    algoritmo,probabilidad,caracteres_mensaje,bits_datos,bits_trama,
    overhead_bits,overhead_pct,bits_alterados,bloques_corregidos,
    exito_reportado,mensaje_correcto
    """
    archivo = Path(ruta)

    if not archivo.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo: {archivo.resolve()}"
        )

    resultados: list[dict[str, float]] = []

    with archivo.open("r", encoding="utf-8", newline="") as contenido:
        lector = csv.DictReader(contenido)

        if lector.fieldnames is None:
            raise ValueError("El archivo está vacío.")

        for fila in lector:
            resultados.append(
                {
                    "algoritmo": fila["algoritmo"],
                    "probabilidad": float(fila["probabilidad"]),
                    "caracteres_mensaje": int(fila["caracteres_mensaje"]),
                    "bits_datos": int(fila["bits_datos"]),
                    "bits_trama": int(fila["bits_trama"]),
                    "overhead_bits": int(fila["overhead_bits"]),
                    "overhead_pct": float(fila["overhead_pct"]),
                    "bits_alterados": int(fila["bits_alterados"]),
                    "bloques_corregidos": int(fila["bloques_corregidos"]),
                    "exito_reportado": int(fila["exito_reportado"]),
                    "mensaje_correcto": int(fila["mensaje_correcto"]),
                }
            )

    if not resultados:
        raise ValueError("El archivo no contiene resultados.")

    return resultados


def promedio(valores: list[float]) -> float:
    return sum(valores) / len(valores)


def graficar_exito_vs_tamano(
    resultados: list[dict[str, float]],
) -> None:
    """% de mensajes correctos según el tamaño de la trama, por algoritmo."""
    plt.figure(figsize=(9, 5))

    for algoritmo in ALGORITMOS:
        agrupado: dict[int, list[int]] = defaultdict(list)

        for fila in resultados:
            if (
                fila["algoritmo"] == algoritmo
                and fila["probabilidad"] == PROBABILIDAD_REFERENCIA
            ):
                agrupado[fila["caracteres_mensaje"]].append(
                    fila["mensaje_correcto"]
                )

        tamanos = sorted(agrupado)
        porcentajes = [
            promedio(agrupado[tamano]) * 100 for tamano in tamanos
        ]

        plt.plot(
            tamanos,
            porcentajes,
            marker="o",
            label=algoritmo,
            color=COLORES[algoritmo],
        )

    plt.title(
        "Mensajes recibidos correctamente vs. tamaño del mensaje\n"
        f"(probabilidad de error = {PROBABILIDAD_REFERENCIA})"
    )
    plt.xlabel("Tamaño del mensaje original (caracteres)")
    plt.ylabel("Mensajes correctos (%)")
    plt.ylim(-5, 105)
    plt.legend(title="Algoritmo")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("exito_vs_tamano.png", dpi=300)
    plt.close()


def graficar_exito_vs_probabilidad(
    resultados: list[dict[str, float]],
) -> None:
    """% de mensajes correctos según la probabilidad de error, por algoritmo."""
    plt.figure(figsize=(9, 5))

    for algoritmo in ALGORITMOS:
        agrupado: dict[float, list[int]] = defaultdict(list)

        for fila in resultados:
            if (
                fila["algoritmo"] == algoritmo
                and fila["caracteres_mensaje"] == TAMANO_REFERENCIA
            ):
                agrupado[fila["probabilidad"]].append(
                    fila["mensaje_correcto"]
                )

        probabilidades = sorted(agrupado)
        porcentajes = [
            promedio(agrupado[probabilidad]) * 100
            for probabilidad in probabilidades
        ]

        plt.plot(
            probabilidades,
            porcentajes,
            marker="o",
            label=algoritmo,
            color=COLORES[algoritmo],
        )

    plt.title(
        "Mensajes recibidos correctamente vs. probabilidad de error\n"
        f"(mensaje de {TAMANO_REFERENCIA} caracteres)"
    )
    plt.xlabel("Probabilidad de error por bit")
    plt.ylabel("Mensajes correctos (%)")
    plt.ylim(-5, 105)
    plt.legend(title="Algoritmo")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("exito_vs_probabilidad.png", dpi=300)
    plt.close()


def graficar_errores_por_tamano(
    resultados: list[dict[str, float]],
) -> None:
    """Bits alterados promedio según el tamaño de la trama, por algoritmo."""
    plt.figure(figsize=(9, 5))

    for algoritmo in ALGORITMOS:
        agrupado: dict[int, list[int]] = defaultdict(list)

        for fila in resultados:
            if (
                fila["algoritmo"] == algoritmo
                and fila["probabilidad"] == PROBABILIDAD_REFERENCIA
            ):
                agrupado[fila["bits_trama"]].append(fila["bits_alterados"])

        tamanos = sorted(agrupado)
        errores_promedio = [
            promedio(agrupado[tamano]) for tamano in tamanos
        ]

        plt.plot(
            tamanos,
            errores_promedio,
            marker="o",
            label=algoritmo,
            color=COLORES[algoritmo],
        )

    plt.title(
        "Errores promedio en función del tamaño de la trama\n"
        f"(probabilidad de error = {PROBABILIDAD_REFERENCIA})"
    )
    plt.xlabel("Tamaño de la trama enviada (bits)")
    plt.ylabel("Cantidad promedio de bits alterados")
    plt.legend(title="Algoritmo")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("errores_por_tamano.png", dpi=300)
    plt.close()


def graficar_overhead(
    resultados: list[dict[str, float]],
) -> None:
    """Overhead (%) introducido por cada algoritmo según el tamaño del mensaje."""
    plt.figure(figsize=(9, 5))

    for algoritmo in ALGORITMOS:
        agrupado: dict[int, list[float]] = defaultdict(list)

        for fila in resultados:
            if fila["algoritmo"] == algoritmo:
                agrupado[fila["caracteres_mensaje"]].append(
                    fila["overhead_pct"]
                )

        tamanos = sorted(agrupado)
        overhead_promedio = [
            promedio(agrupado[tamano]) for tamano in tamanos
        ]

        plt.plot(
            tamanos,
            overhead_promedio,
            marker="o",
            label=algoritmo,
            color=COLORES[algoritmo],
        )

    plt.title("Overhead de redundancia según el tamaño del mensaje")
    plt.xlabel("Tamaño del mensaje original (caracteres)")
    plt.ylabel("Overhead (% de bits extra sobre los datos)")
    plt.legend(title="Algoritmo")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("overhead_por_algoritmo.png", dpi=300)
    plt.close()


def mostrar_resumen(resultados: list[dict[str, float]]) -> None:
    print("\nResumen general por algoritmo")
    print("-" * 70)
    print(
        f"{'Algoritmo':>10} "
        f"{'Pruebas':>10} "
        f"{'Éxito':>10} "
        f"{'Overhead prom.':>16}"
    )
    print("-" * 70)

    for algoritmo in ALGORITMOS:
        filas = [f for f in resultados if f["algoritmo"] == algoritmo]

        if not filas:
            continue

        exito = promedio([f["mensaje_correcto"] for f in filas]) * 100
        overhead = promedio([f["overhead_pct"] for f in filas])

        print(
            f"{algoritmo:>10} "
            f"{len(filas):>10} "
            f"{exito:>9.2f}% "
            f"{overhead:>15.2f}%"
        )


def main() -> None:
    resultados = leer_resultados(ARCHIVO_ENTRADA)

    mostrar_resumen(resultados)

    graficar_exito_vs_tamano(resultados)
    graficar_exito_vs_probabilidad(resultados)
    graficar_errores_por_tamano(resultados)
    graficar_overhead(resultados)

    print("\nGráficas guardadas:")
    print("- exito_vs_tamano.png")
    print("- exito_vs_probabilidad.png")
    print("- errores_por_tamano.png")
    print("- overhead_por_algoritmo.png")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}")
