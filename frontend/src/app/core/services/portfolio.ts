import { Service, computed, effect, signal } from '@angular/core';

export interface Posicion {
  id: string;
  ticker: string;
  nombre: string;
  acciones: number;
  precio: number; // precio por acción, ingresado a mano (sin cotización en vivo)
}

const CLAVE = 'portafolio-posiciones';

/** Cartera ilustrativa (top 10 del S&P 500 por capitalización, pesos de ejemplo que
 * suman 100% de una cartera hipotética de $100,000). NO es dato de mercado real: se
 * muestra solo cuando el usuario aún no dio de alta ninguna posición propia. */
export const POSICIONES_EJEMPLO: Posicion[] = [
  { id: 'ej-aapl', ticker: 'AAPL', nombre: 'Apple', acciones: 78, precio: 230.77 },
  { id: 'ej-msft', ticker: 'MSFT', nombre: 'Microsoft', acciones: 38, precio: 421.05 },
  { id: 'ej-nvda', ticker: 'NVDA', nombre: 'NVIDIA', acciones: 115, precio: 130.43 },
  { id: 'ej-googl', ticker: 'GOOGL', nombre: 'Alphabet', acciones: 63, precio: 174.6 },
  { id: 'ej-amzn', ticker: 'AMZN', nombre: 'Amazon', acciones: 54, precio: 185.19 },
  { id: 'ej-meta', ticker: 'META', nombre: 'Meta Platforms', acciones: 14, precio: 571.43 },
  { id: 'ej-brkb', ticker: 'BRK.B', nombre: 'Berkshire Hathaway', acciones: 16, precio: 437.5 },
  { id: 'ej-avgo', ticker: 'AVGO', nombre: 'Broadcom', acciones: 37, precio: 162.16 },
  { id: 'ej-tsla', ticker: 'TSLA', nombre: 'Tesla', acciones: 20, precio: 250 },
  { id: 'ej-lly', ticker: 'LLY', nombre: 'Eli Lilly', acciones: 5, precio: 800 },
];

function generarId(): string {
  return crypto.randomUUID?.() ?? `pos-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/** Cartera del usuario: posiciones dadas de alta a mano, persistidas en localStorage.
 * Sin posiciones reales, la vista de portafolio recurre a POSICIONES_EJEMPLO. */
@Service()
export class PortfolioService {
  readonly posiciones = signal<Posicion[]>(this.leerEstadoInicial());
  readonly valorTotal = computed(() =>
    this.posiciones().reduce((total, p) => total + p.acciones * p.precio, 0)
  );

  constructor() {
    effect(() => {
      try {
        localStorage.setItem(CLAVE, JSON.stringify(this.posiciones()));
      } catch {
        // localStorage no disponible (modo privado, etc.): el estado solo vive en memoria.
      }
    });
  }

  agregarPosicion(datos: { ticker: string; nombre: string; acciones: number; precio: number }): void {
    const posicion: Posicion = {
      id: generarId(),
      ticker: datos.ticker.trim().toUpperCase(),
      nombre: datos.nombre.trim(),
      acciones: datos.acciones,
      precio: datos.precio,
    };
    this.posiciones.update((lista) => [...lista, posicion]);
  }

  eliminarPosicion(id: string): void {
    this.posiciones.update((lista) => lista.filter((p) => p.id !== id));
  }

  /** Elimina todas las posiciones reales; la vista vuelve a mostrar el ejemplo simulado. */
  vaciarCartera(): void {
    this.posiciones.set([]);
  }

  private leerEstadoInicial(): Posicion[] {
    try {
      const guardado = localStorage.getItem(CLAVE);
      return guardado ? (JSON.parse(guardado) as Posicion[]) : [];
    } catch {
      return [];
    }
  }
}
