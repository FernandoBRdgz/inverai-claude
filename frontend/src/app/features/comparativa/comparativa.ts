import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { EMPRESAS_SP500 } from '../../core/data/empresas-sp500';
import { PlotlyChart, FiguraPlotly } from '../../shared/components/plotly-chart/plotly-chart';
import { CategoriaGrafica, ComparativaService } from './services/comparativa';

type Lado = 'izquierda' | 'derecha';

interface EstadoLado {
  ticker: string;
  cargando: boolean;
  error: string | null;
  figuras: FiguraPlotly[];
}

const CATEGORIAS: { valor: CategoriaGrafica; etiqueta: string }[] = [
  { valor: 'income', etiqueta: '📈 Estado de resultados' },
  { valor: 'fcf', etiqueta: '💰 Flujo de caja' },
  { valor: 'roic', etiqueta: '🏦 ROIC y balance' },
  { valor: 'precio', etiqueta: '📉 Precio histórico' },
];

/**
 * Comparativa de compañías en modo dual: la mitad izquierda y la derecha se cargan de
 * forma independiente (cada una con su propia compañía), pero comparten la categoría
 * de gráficas (viene de app/services/visualization.py en el backend).
 */
@Component({
  imports: [FormsModule, PlotlyChart],
  selector: 'app-comparativa',
  styleUrl: './comparativa.css',
  templateUrl: './comparativa.html',
})
export class Comparativa {
  private readonly comparativaService = inject(ComparativaService);

  protected readonly empresas = EMPRESAS_SP500;
  protected readonly categorias = CATEGORIAS;
  protected readonly categoria = signal<CategoriaGrafica>('income');

  // GOOGL/META por defecto — comparación funcional desde la primera vez que se abre la vista.
  protected readonly izquierda = signal<EstadoLado>(this.estadoInicial('GOOGL'));
  protected readonly derecha = signal<EstadoLado>(this.estadoInicial('META'));

  constructor() {
    this.cargarLado('izquierda');
    this.cargarLado('derecha');
  }

  cambiarCategoria(valor: CategoriaGrafica): void {
    if (valor === this.categoria()) return;
    this.categoria.set(valor);
    this.cargarLado('izquierda');
    this.cargarLado('derecha');
  }

  cambiarTicker(lado: Lado, ticker: string): void {
    this.actualizarLado(lado, { ticker });
    this.cargarLado(lado);
  }

  private async cargarLado(lado: Lado): Promise<void> {
    const ticker = (lado === 'izquierda' ? this.izquierda() : this.derecha()).ticker;
    this.actualizarLado(lado, { cargando: true, error: null, figuras: [] });
    try {
      const figuras = await this.comparativaService.obtenerGraficas(ticker, this.categoria());
      this.actualizarLado(lado, { cargando: false, figuras });
    } catch {
      this.actualizarLado(lado, {
        cargando: false,
        error: 'No fue posible cargar las gráficas de esta compañía. Intente nuevamente.',
      });
    }
  }

  private actualizarLado(lado: Lado, cambios: Partial<EstadoLado>): void {
    const senal = lado === 'izquierda' ? this.izquierda : this.derecha;
    senal.update((actual) => ({ ...actual, ...cambios }));
  }

  private estadoInicial(ticker: string): EstadoLado {
    return { ticker, cargando: false, error: null, figuras: [] };
  }
}
