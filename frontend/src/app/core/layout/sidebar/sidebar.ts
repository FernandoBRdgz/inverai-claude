import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

import { SidebarService } from '../../services/sidebar';
import { Theme } from '../../services/theme';
import { NAV_ITEMS, SECCIONES } from '../nav-items';

@Component({
  imports: [RouterLink, RouterLinkActive],
  selector: 'app-sidebar',
  styleUrl: './sidebar.css',
  templateUrl: './sidebar.html',
})
export class Sidebar {
  protected readonly sidebar = inject(SidebarService);
  protected readonly theme = inject(Theme);

  protected readonly secciones = SECCIONES.map((nombre) => ({
    nombre,
    items: NAV_ITEMS.filter((item) => item.seccion === nombre),
  }));
}
