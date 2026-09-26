import { Routes } from '@angular/router';

import { Shell } from './core/layout/shell/shell';
import { Landing } from './features/landing/landing';
import { Chat } from './features/chat/chat';
import { Portafolio } from './features/portafolio/portafolio';
import { Historial } from './features/historial/historial';
import { Admin } from './features/admin/admin';
import { Comparativa } from './features/comparativa/comparativa';
import { Placeholder } from './features/placeholder/placeholder';

export const routes: Routes = [
  { path: '', component: Landing, pathMatch: 'full' },
  {
    // Vistas internas: comparten el panel lateral del Shell.
    // Para agregar una vista: ítem en core/layout/nav-items.ts + ruta aquí.
    path: '',
    component: Shell,
    children: [
      { path: 'chat', component: Chat },
      { path: 'comparativa', component: Comparativa },
      { path: 'portafolio', component: Portafolio },
      { path: 'historial', component: Historial },
      { path: 'admin', component: Admin }, // administración + configuración
    ],
  },
  { path: '**', redirectTo: '' },
];
