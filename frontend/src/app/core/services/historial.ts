import { Service, signal } from '@angular/core';

import { escribir, leer } from './storage-efimera';

export interface MensajeHistorial {
  autor: 'usuario' | 'asistente';
  texto: string;
}

export interface ConversacionHistorial {
  id: string;
  titulo: string;
  iniciadaEn: string; // ISO
  actualizadaEn: string; // ISO
  mensajes: MensajeHistorial[];
}

const CLAVE = 'historial-conversaciones';
const MAX_CONVERSACIONES = 20;
const LARGO_TITULO = 60;

function generarId(): string {
  return crypto.randomUUID?.() ?? `conv-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function derivarTitulo(mensaje: string): string {
  const limpio = mensaje.trim();
  return limpio.length > LARGO_TITULO ? `${limpio.slice(0, LARGO_TITULO)}…` : limpio;
}

/**
 * Historial de conversaciones con el asistente: persistencia efímera (ver
 * storage-efimera.ts), solo de esta sesión del navegador. Guarda "metadatos"
 * ligeros — título, fechas y el texto de los mensajes — nunca el estado de UI
 * del chat (votos, cajas de retroalimentación, etc.), que es responsabilidad
 * exclusiva de Chat.
 */
@Service()
export class HistorialService {
  readonly conversaciones = signal<ConversacionHistorial[]>(leer<ConversacionHistorial[]>(CLAVE) ?? []);

  /** Crea una conversación a partir del primer mensaje real del usuario y devuelve su id. */
  iniciarConversacion(primerMensaje: string): string {
    const ahora = new Date().toISOString();
    const nueva: ConversacionHistorial = {
      id: generarId(),
      titulo: derivarTitulo(primerMensaje) || 'Conversación sin título',
      iniciadaEn: ahora,
      actualizadaEn: ahora,
      mensajes: [],
    };
    // Más reciente primero; tope de tamaño (no de expiración, sessionStorage ya se
    // limpia sola al cerrar la pestaña) para no inflar la cuota en sesiones largas.
    this.actualizar([nueva, ...this.conversaciones()].slice(0, MAX_CONVERSACIONES));
    return nueva.id;
  }

  registrarMensaje(id: string, mensaje: MensajeHistorial): void {
    this.actualizar(
      this.conversaciones().map((c) =>
        c.id === id
          ? { ...c, mensajes: [...c.mensajes, mensaje], actualizadaEn: new Date().toISOString() }
          : c
      )
    );
  }

  obtener(id: string): ConversacionHistorial | undefined {
    return this.conversaciones().find((c) => c.id === id);
  }

  eliminarConversacion(id: string): void {
    this.actualizar(this.conversaciones().filter((c) => c.id !== id));
  }

  limpiarHistorial(): void {
    this.actualizar([]);
  }

  private actualizar(lista: ConversacionHistorial[]): void {
    this.conversaciones.set(lista);
    escribir(CLAVE, lista);
  }
}
