import { Component, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { NAV_ITEMS } from '../../core/layout/nav-items';

/**
 * Vista genérica "Próximamente" para las pantallas del menú que aún no existen.
 * Toma título, icono y descripción de NAV_ITEMS según la ruta actual. Cuando una
 * vista se construya, se reemplaza `component: Placeholder` por el componente real
 * en app.routes.ts.
 */
@Component({
  imports: [RouterLink],
  selector: 'app-placeholder',
  styleUrl: './placeholder.css',
  templateUrl: './placeholder.html',
})
export class Placeholder {
  private readonly ruta = inject(ActivatedRoute);

  protected readonly item = NAV_ITEMS.find(
    (nav) => nav.ruta === '/' + (this.ruta.snapshot.routeConfig?.path ?? ''),
  );
}
