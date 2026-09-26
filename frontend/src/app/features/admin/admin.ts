import { Component, computed, inject, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';

import { HistorialService } from '../../core/services/historial';
import { PortfolioService } from '../../core/services/portfolio';
import { EstadoService, EstadoSistema } from './services/estado';

type EstadoCarga = 'cargando' | 'ok' | 'error';

@Component({
  imports: [DecimalPipe],
  selector: 'app-admin',
  styleUrl: './admin.css',
  templateUrl: './admin.html',
})
export class Admin {
  private readonly estadoService = inject(EstadoService);
  private readonly historial = inject(HistorialService);
  private readonly portfolio = inject(PortfolioService);

  protected readonly estadoCarga = signal<EstadoCarga>('cargando');
  protected readonly estado = signal<EstadoSistema | null>(null);

  protected readonly conversaciones = computed(() => this.historial.conversaciones().length);
  protected readonly mensajesEnviados = computed(() =>
    this.historial.conversaciones().reduce((total, c) => total + c.mensajes.length, 0)
  );
  protected readonly posicionesRegistradas = computed(() => this.portfolio.posiciones().length);
  protected readonly valorPortafolio = computed(() =>
    this.posicionesRegistradas() > 0 ? this.portfolio.valorTotal() : null
  );

  // --- Restablecer datos de esta sesión (confirmación en línea) -------------------
  protected readonly confirmandoReset = signal(false);

  constructor() {
    this.cargarEstado();
  }

  private async cargarEstado(): Promise<void> {
    try {
      this.estado.set(await this.estadoService.obtenerEstado());
      this.estadoCarga.set('ok');
    } catch {
      this.estadoCarga.set('error');
    }
  }

  pedirConfirmacionReset(): void {
    this.confirmandoReset.set(true);
  }

  cancelarReset(): void {
    this.confirmandoReset.set(false);
  }

  confirmarReset(): void {
    this.historial.limpiarHistorial();
    this.portfolio.vaciarCartera();
    this.confirmandoReset.set(false);
  }
}
