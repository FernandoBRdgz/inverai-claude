import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { ConversacionHistorial, HistorialService } from '../../core/services/historial';

const MINUTO = 60_000;
const HORA = 60 * MINUTO;
const DIA = 24 * HORA;

/** Fecha relativa simple, sin librería: "hace 5 min", "ayer", o una fecha corta. */
function tiempoRelativo(iso: string): string {
  const diferencia = Date.now() - new Date(iso).getTime();
  if (diferencia < MINUTO) return 'justo ahora';
  if (diferencia < HORA) return `hace ${Math.floor(diferencia / MINUTO)} min`;
  if (diferencia < DIA) return `hace ${Math.floor(diferencia / HORA)} h`;
  if (diferencia < 2 * DIA) return 'ayer';
  return new Date(iso).toLocaleDateString('es', { day: 'numeric', month: 'short' });
}

@Component({
  imports: [RouterLink],
  selector: 'app-historial',
  styleUrl: './historial.css',
  templateUrl: './historial.html',
})
export class Historial {
  private readonly historial = inject(HistorialService);

  protected readonly conversaciones = computed<ConversacionHistorial[]>(() =>
    [...this.historial.conversaciones()].sort((a, b) => b.actualizadaEn.localeCompare(a.actualizadaEn))
  );

  protected fechaRelativa(iso: string): string {
    return tiempoRelativo(iso);
  }

  // --- Eliminar una conversación (confirmación en línea, igual que Portafolio) ----
  protected readonly confirmandoId = signal<string | null>(null);

  pedirConfirmacion(id: string): void {
    this.confirmandoId.set(id);
  }

  cancelarEliminacion(): void {
    this.confirmandoId.set(null);
  }

  confirmarEliminacion(id: string): void {
    this.historial.eliminarConversacion(id);
    this.confirmandoId.set(null);
  }

  // --- Vaciar todo el historial (misma idea, para la acción completa) ------------
  protected readonly confirmandoVaciar = signal(false);

  pedirConfirmacionVaciar(): void {
    this.confirmandoVaciar.set(true);
  }

  cancelarVaciar(): void {
    this.confirmandoVaciar.set(false);
  }

  confirmarVaciar(): void {
    this.historial.limpiarHistorial();
    this.confirmandoVaciar.set(false);
  }
}
