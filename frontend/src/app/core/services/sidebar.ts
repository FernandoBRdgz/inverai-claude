import { Service, signal, effect } from '@angular/core';

const CLAVE = 'sidebar-colapsado';

/** Estado del panel lateral (colapsado/expandido), persistido en localStorage. */
@Service()
export class SidebarService {
  readonly colapsado = signal<boolean>(this.leerEstadoInicial());

  constructor() {
    effect(() => {
      try {
        localStorage.setItem(CLAVE, this.colapsado() ? '1' : '0');
      } catch {
        // localStorage no disponible (modo privado, etc.): el estado solo vive en memoria.
      }
    });
  }

  alternar(): void {
    this.colapsado.update((valor) => !valor);
  }

  private leerEstadoInicial(): boolean {
    try {
      const guardado = localStorage.getItem(CLAVE);
      if (guardado !== null) return guardado === '1';
    } catch {
      // ignorar: se usa el valor por defecto
    }
    // Sin preferencia guardada: colapsado en pantallas angostas.
    return window.matchMedia?.('(max-width: 900px)').matches ?? false;
  }
}
