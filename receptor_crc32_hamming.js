"use strict";

const net = require("node:net");

// ============================================================
// CONFIGURACIÓN
// ============================================================
const HOST = "0.0.0.0";
const PORT = 5000;

// Mismo polinomio de 33 bits usado por el emisor Python.
const CRC32_POLYNOMIAL = 0x104C11DB7n
  .toString(2)
  .padStart(33, "0");

const CRC_BITS = 32;

const ALGORITMOS_VALIDOS = new Set(["HAMMING", "CRC32", "AMBOS"]);


function decodificarBloqueHamming74(bloque) {
  if (!/^[01]{7}$/.test(bloque)) {
    throw new Error(
      "Cada bloque Hamming debe contener exactamente 7 bits."
    );
  }

  const bits = bloque.split("").map(Number);


  const s1 = bits[0] ^ bits[2] ^ bits[4] ^ bits[6];
  const s2 = bits[1] ^ bits[2] ^ bits[5] ^ bits[6];
  const s4 = bits[3] ^ bits[4] ^ bits[5] ^ bits[6];


  const posicionError = s1 + 2 * s2 + 4 * s4;

  // Hamming(7,4) puede corregir un bit incorrecto por bloque.
  if (posicionError !== 0) {
    bits[posicionError - 1] ^= 1;
  }

  // Se extraen los bits de datos:
  // posiciones 3, 5, 6 y 7.
  const datos =
    `${bits[2]}${bits[4]}${bits[5]}${bits[6]}`;

  return {
    datos,
    corregido: posicionError !== 0,
    posicionError,
    bloqueCorregido: bits.join(""),
  };
}


function decodificarHamming74(trama) {
  if (!trama || !/^[01]+$/.test(trama)) {
    throw new Error(
      "La trama debe ser una cadena binaria no vacía."
    );
  }

  if (trama.length % 7 !== 0) {
    throw new Error(
      `La longitud de la trama (${trama.length}) ` +
      "no es múltiplo de 7."
    );
  }

  let payload = "";
  const correcciones = [];

  for (let inicio = 0; inicio < trama.length; inicio += 7) {
    const numeroBloque = inicio / 7;
    const bloque = trama.slice(inicio, inicio + 7);

    const resultado =
      decodificarBloqueHamming74(bloque);

    payload += resultado.datos;

    if (resultado.corregido) {
      correcciones.push({
        bloque: numeroBloque + 1,
        posicion: resultado.posicionError,
        recibido: bloque,
        corregido: resultado.bloqueCorregido,
      });
    }
  }

  return {
    payload,
    correcciones,
  };
}


function xorBit(a, b) {
  return a === b ? "0" : "1";
}


function calcularCRC32(datosBits) {
  if (!datosBits || !/^[01]+$/.test(datosBits)) {
    throw new Error(
      "Los datos para CRC deben ser una cadena binaria no vacía."
    );
  }


  const dividendo = (
    datosBits + "0".repeat(CRC_BITS)
  ).split("");

  for (
    let posicion = 0;
    posicion < datosBits.length;
    posicion += 1
  ) {
    if (dividendo[posicion] === "1") {
      for (
        let indice = 0;
        indice < CRC32_POLYNOMIAL.length;
        indice += 1
      ) {
        const destino = posicion + indice;

        dividendo[destino] = xorBit(
          dividendo[destino],
          CRC32_POLYNOMIAL[indice]
        );
      }
    }
  }

  return dividendo.slice(-CRC_BITS).join("");
}


function decodificarAscii(datosBits) {
  if (!datosBits || !/^[01]+$/.test(datosBits)) {
    throw new Error(
      "Los datos ASCII deben ser una cadena binaria no vacía."
    );
  }

  if (datosBits.length % 8 !== 0) {
    throw new Error(
      `La longitud de los datos (${datosBits.length}) ` +
      "no es múltiplo de 8."
    );
  }

  const bytes = [];

  for (
    let inicio = 0;
    inicio < datosBits.length;
    inicio += 8
  ) {
    const byteBinario =
      datosBits.slice(inicio, inicio + 8);

    const byteDecimal =
      Number.parseInt(byteBinario, 2);

    bytes.push(byteDecimal);
  }

  if (bytes.some((byte) => byte > 127)) {
    throw new Error(
      "Los datos recibidos no representan texto ASCII válido."
    );
  }


  return Buffer
    .from(bytes)
    .toString("ascii")
    .replace(/\x00+$/g, "");
}


function verificarIntegridad(datosBits) {
  const crcRecibido = datosBits.slice(-CRC_BITS);
  const datos = datosBits.slice(0, -CRC_BITS);
  const crcCalculado = calcularCRC32(datos);

  return {
    datos,
    crcRecibido,
    crcCalculado,
    integridadValida: crcRecibido === crcCalculado,
  };
}


function procesarTrama(tramaCruda) {
  const contenido = tramaCruda.trim();

  if (!contenido) {
    throw new Error("Se recibió una trama vacía.");
  }

  const separador = contenido.indexOf("\n");

  if (separador === -1) {
    throw new Error(
      "No se encontró el encabezado con el algoritmo utilizado."
    );
  }

  const algoritmo = contenido.slice(0, separador).trim();
  const trama = contenido.slice(separador + 1).trim();

  if (!ALGORITMOS_VALIDOS.has(algoritmo)) {
    throw new Error(`Algoritmo desconocido: "${algoritmo}".`);
  }

  if (!trama || !/^[01]+$/.test(trama)) {
    throw new Error(
      "La trama contiene caracteres distintos de 0 y 1."
    );
  }

  let payload = trama;
  let correcciones = [];

  if (algoritmo === "HAMMING" || algoritmo === "AMBOS") {
    ({ payload, correcciones } = decodificarHamming74(trama));
  }

  let datosBits = payload;
  let crcRecibido = null;
  let crcCalculado = null;
  let integridadValida = true;

  if (algoritmo === "CRC32" || algoritmo === "AMBOS") {
    if (payload.length < CRC_BITS + 8) {
      throw new Error(
        "El payload es demasiado corto para contener datos y CRC-32."
      );
    }

    const verificacion = verificarIntegridad(payload);

    datosBits = verificacion.datos;
    crcRecibido = verificacion.crcRecibido;
    crcCalculado = verificacion.crcCalculado;
    integridadValida = verificacion.integridadValida;
  }

  let mensaje = null;
  let errorDecodificacion = null;

  if (integridadValida) {
    try {
      mensaje = decodificarAscii(datosBits);
    } catch (error) {
      errorDecodificacion = error.message;
    }
  }

  return {
    algoritmo,
    trama,
    payload,
    datosBits,
    crcRecibido,
    crcCalculado,
    integridadValida,
    correcciones,
    mensaje,
    errorDecodificacion,
  };
}


function mostrarResultado(resultado, remoto) {
  console.log(
    "\n============================================================"
  );

  console.log(`Conexión recibida desde ${remoto}`);
  console.log(`Algoritmo: ${resultado.algoritmo}`);
  console.log(`Bits recibidos: ${resultado.trama.length}`);

  if (resultado.algoritmo === "HAMMING" || resultado.algoritmo === "AMBOS") {
    console.log(
      `Bloques Hamming: ${resultado.trama.length / 7}`
    );

    console.log(
      `Bloques corregidos: ${resultado.correcciones.length}`
    );

    for (const correccion of resultado.correcciones) {
      console.log(
        `  - Bloque ${correccion.bloque}: ` +
        `bit ${correccion.posicion} ` +
        `(${correccion.recibido} -> ${correccion.corregido})`
      );
    }
  }

  console.log(
    `Datos recuperados: ${resultado.datosBits}`
  );

  if (resultado.algoritmo === "CRC32" || resultado.algoritmo === "AMBOS") {
    console.log(
      `CRC recibido:       ${resultado.crcRecibido}`
    );

    console.log(
      `CRC calculado:      ${resultado.crcCalculado}`
    );

    if (!resultado.integridadValida) {
      console.error(
        "ERROR: CRC-32 inválido. Quedaron errores que " +
        "no pudieron ser corregidos."
      );

      return;
    }
  }

  if (resultado.errorDecodificacion) {
    console.error(
      `ERROR: ${resultado.errorDecodificacion}`
    );

    return;
  }

  console.log("Integridad: válida");

  console.log(
    `Mensaje recibido: ${JSON.stringify(resultado.mensaje)}`
  );
}


function iniciarServidor() {
  const servidor = net.createServer((socket) => {
    const direccion =
      socket.remoteAddress ?? "dirección desconocida";

    const puerto =
      socket.remotePort ?? "puerto desconocido";

    const remoto = `${direccion}:${puerto}`;

    socket.setEncoding("ascii");
    socket.setTimeout(15000);

    let tramaRecibida = "";

    socket.on("data", (fragmento) => {
      tramaRecibida += fragmento;
    });


    socket.on("end", () => {
      try {
        const resultado =
          procesarTrama(tramaRecibida);

        mostrarResultado(resultado, remoto);
      } catch (error) {
        console.error(
          `\nError al procesar la trama de ${remoto}: ` +
          error.message
        );
      }
    });

    socket.on("timeout", () => {
      console.error(
        `\nTiempo agotado para la conexión ${remoto}.`
      );

      socket.destroy();
    });

    socket.on("error", (error) => {
      console.error(
        `\nError de socket con ${remoto}: ${error.message}`
      );
    });
  });

  servidor.on("error", (error) => {
    if (error.code === "EADDRINUSE") {
      console.error(
        `El puerto ${PORT} ya está en uso.`
      );
    } else {
      console.error(
        `Error del servidor: ${error.message}`
      );
    }

    process.exitCode = 1;
  });

  servidor.listen(PORT, HOST, () => {
    console.log(
      "=== RECEPTOR TCP: CRC-32 + HAMMING(7,4) ==="
    );

    console.log(
      `Escuchando en ${HOST}:${PORT}`
    );

    console.log(
      "Esperando tramas del emisor Python..."
    );
  });
}

iniciarServidor();
