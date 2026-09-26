/**
 * Adaptador de una sola responsabilidad sobre sessionStorage: leer/escribir/borrar
 * JSON, con manejo defensivo (modo privado, cuota llena, etc.). Es el único archivo
 * que sabe DÓNDE vive el dato — si mañana cambia a localStorage, IndexedDB o un
 * endpoint del backend, solo este módulo se toca; HistorialService no se entera.
 *
 * "Efímera" es literal: sessionStorage sobrevive a recargas y a navegar entre
 * vistas, pero se borra solo al cerrar la pestaña. No hace falta lógica de
 * expiración propia.
 */

export function leer<T>(clave: string): T | null {
  try {
    const guardado = sessionStorage.getItem(clave);
    return guardado ? (JSON.parse(guardado) as T) : null;
  } catch {
    return null;
  }
}

export function escribir<T>(clave: string, valor: T): void {
  try {
    sessionStorage.setItem(clave, JSON.stringify(valor));
  } catch {
    // sessionStorage no disponible o sin cuota: el dato solo vive en memoria.
  }
}

export function borrar(clave: string): void {
  try {
    sessionStorage.removeItem(clave);
  } catch {
    // ignorar
  }
}
