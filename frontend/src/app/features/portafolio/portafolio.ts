import { Component, computed, inject, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { EMPRESAS_SP500 } from '../../core/data/empresas-sp500';
import { CotizacionService } from '../../core/services/cotizacion';
import { POSICIONES_EJEMPLO, PortfolioService, Posicion } from '../../core/services/portfolio';

interface FilaPortafolio extends Posicion {
  valor: number;
  peso: number; // 0..1
}

interface SegmentoDona {
  id: string;
  etiqueta: string;
  peso: number; // 0..1
  valor: number;
  color: string;
  dasharray: string;
  dashoffset: number;
}

// Ring de la dona: radio y grosor del trazo en unidades del viewBox (≈ px).
const RADIO = 86;
const GROSOR = 24;
const CIRCUNFERENCIA = 2 * Math.PI * RADIO;
const HUECO = 2; // separación entre arcos (mark spec: 2px de superficie)
const MAX_SEGMENTOS_PROPIOS = 5; // el resto se pliega en "Otras" (dona: máx. 6 segmentos)

// Colores categóricos (ver src/styles.css): orden fijo, nunca reordenar.
const COLORES_SERIE = [
  'var(--serie-1)',
  'var(--serie-2)',
  'var(--serie-3)',
  'var(--serie-4)',
  'var(--serie-5)',
];
const COLOR_OTRAS = 'var(--texto-suave)';

@Component({
  imports: [FormsModule, DecimalPipe],
  selector: 'app-portafolio',
  styleUrl: './portafolio.css',
  templateUrl: './portafolio.html',
})
export class Portafolio {
  private readonly portfolio = inject(PortfolioService);
  private readonly cotizacionService = inject(CotizacionService);

  protected readonly radio = RADIO;
  protected readonly grosor = GROSOR;
  protected readonly circunferencia = CIRCUNFERENCIA;

  // Sin posiciones propias, se muestra el ejemplo simulado como referencia visual.
  protected readonly usandoEjemplo = computed(() => this.portfolio.posiciones().length === 0);
  private readonly posicionesAMostrar = computed<Posicion[]>(() =>
    this.usandoEjemplo() ? POSICIONES_EJEMPLO : this.portfolio.posiciones()
  );

  protected readonly valorTotal = computed(() =>
    this.posicionesAMostrar().reduce((total, p) => total + p.acciones * p.precio, 0)
  );

  // Todas las posiciones (no solo las de la dona), ordenadas de mayor a menor peso.
  protected readonly filas = computed<FilaPortafolio[]>(() => {
    const total = this.valorTotal() || 1;
    return this.posicionesAMostrar()
      .map((p) => {
        const valor = p.acciones * p.precio;
        return { ...p, valor, peso: valor / total };
      })
      .sort((a, b) => b.valor - a.valor);
  });

  protected readonly mayorPosicion = computed(() => this.filas()[0] ?? null);

  // Color de swatch por fila: las primeras MAX_SEGMENTOS_PROPIOS tienen su propio tono;
  // el resto comparte el gris de "Otras" (coincide con lo que se ve en la dona).
  protected colorDeFila(indice: number): string {
    return indice < MAX_SEGMENTOS_PROPIOS ? COLORES_SERIE[indice] : COLOR_OTRAS;
  }

  protected readonly segmentos = computed<SegmentoDona[]>(() => {
    const filas = this.filas();
    const propias = filas.slice(0, MAX_SEGMENTOS_PROPIOS);
    const resto = filas.slice(MAX_SEGMENTOS_PROPIOS);
    const total = this.valorTotal() || 1;

    const items = propias.map((f, indice) => ({
      id: f.id,
      etiqueta: f.ticker,
      peso: f.peso,
      valor: f.valor,
      color: COLORES_SERIE[indice],
    }));

    if (resto.length > 0) {
      const valorResto = resto.reduce((suma, f) => suma + f.valor, 0);
      items.push({
        id: '__otras__',
        etiqueta: `Otras (${resto.length})`,
        peso: valorResto / total,
        valor: valorResto,
        color: COLOR_OTRAS,
      });
    }

    let acumulado = 0;
    return items.map((item) => {
      const longitud = Math.max(item.peso * CIRCUNFERENCIA - HUECO, 0);
      const dashoffset = -(acumulado * CIRCUNFERENCIA);
      acumulado += item.peso;
      return { ...item, dasharray: `${longitud} ${CIRCUNFERENCIA - longitud}`, dashoffset };
    });
  });

  // Segmento bajo el mouse/foco: el centro de la dona muestra su detalle en vez del total.
  protected readonly segmentoActivo = signal<SegmentoDona | null>(null);

  // --- Formulario "Dar de alta" ---------------------------------------------------
  // El usuario solo elige la empresa (mismo listado que Comparativa) y las acciones;
  // ticker y precio se completan solos con GET /api/v1/cotizacion (AlphaVantage).
  protected readonly empresas = EMPRESAS_SP500;
  // Señales (no propiedades planas): la app es zoneless (sin zone.js), y el precio
  // llega tras un `await` que ocurre fuera de cualquier evento rastreado por Angular,
  // así que sin señal la vista se queda congelada en "Consultando…" al resolver.
  protected readonly tickerSeleccionado = signal('');
  protected readonly acciones = signal<number | null>(null);
  protected readonly precioAutomatico = signal<number | null>(null);
  protected readonly precioCargando = signal(false);
  protected readonly precioError = signal('');
  protected readonly error = signal('');

  async seleccionarEmpresa(ticker: string): Promise<void> {
    this.tickerSeleccionado.set(ticker);
    this.precioAutomatico.set(null);
    this.precioError.set('');
    this.error.set('');
    if (!ticker) return;

    this.precioCargando.set(true);
    try {
      this.precioAutomatico.set(await this.cotizacionService.obtenerPrecio(ticker));
    } catch {
      this.precioError.set('No fue posible obtener el precio actual. Vuelve a intentarlo.');
    } finally {
      this.precioCargando.set(false);
    }
  }

  agregarPosicion(): void {
    const ticker = this.tickerSeleccionado();
    const acciones = this.acciones();
    const precio = this.precioAutomatico();

    if (!ticker) {
      this.error.set('Selecciona una empresa.');
      return;
    }
    if (!acciones || acciones <= 0) {
      this.error.set('Ingresa una cantidad de acciones mayor a 0.');
      return;
    }
    if (this.precioCargando()) {
      this.error.set('Espera a que se obtenga el precio actual.');
      return;
    }
    if (precio === null) {
      this.error.set('No se pudo obtener el precio de esta empresa; vuelve a seleccionarla.');
      return;
    }

    const empresa = this.empresas.find((e) => e.ticker === ticker);
    this.portfolio.agregarPosicion({
      ticker,
      nombre: empresa?.nombre ?? ticker,
      acciones,
      precio,
    });

    this.error.set('');
    this.tickerSeleccionado.set('');
    this.acciones.set(null);
    this.precioAutomatico.set(null);
  }

  // --- Dar de baja una posición (con confirmación, es irreversible) --------------
  // id de la fila que está mostrando "¿Eliminar? Sí / Cancelar" en vez del botón 🗑️.
  protected readonly confirmandoId = signal<string | null>(null);

  pedirConfirmacion(id: string): void {
    this.confirmandoId.set(id);
  }

  cancelarEliminacion(): void {
    this.confirmandoId.set(null);
  }

  confirmarEliminacion(id: string): void {
    this.portfolio.eliminarPosicion(id);
    this.confirmandoId.set(null);
  }
}
