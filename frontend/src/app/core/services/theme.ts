import { Service, signal, effect } from '@angular/core';

export type Tema = 'claro' | 'oscuro';

const CLAVE_TEMA = 'tema';

/**
 * Centraliza el tema claro/oscuro compartido por toda la app (landing, chat, etc.).
 * El valor inicial ya fue aplicado por el script anti-parpadeo en src/index.html;
 * este servicio solo lo lee y mantiene sincronizados el atributo data-tema y localStorage.
 */
@Service()
export class Theme {
  readonly tema = signal<Tema>(this.leerTemaInicial());

  constructor() {
    effect(() => {
      document.documentElement.setAttribute('data-tema', this.tema());
      localStorage.setItem(CLAVE_TEMA, this.tema());
    });
  }

  alternar(): void {
    this.tema.set(this.tema() === 'oscuro' ? 'claro' : 'oscuro');
  }

  private leerTemaInicial(): Tema {
    const guardado = localStorage.getItem(CLAVE_TEMA) as Tema | null;
    if (guardado) return guardado;
    const prefiereOscuro = window.matchMedia?.('(prefers-color-scheme: dark)').matches;
    return prefiereOscuro ? 'oscuro' : 'claro';
  }
}
