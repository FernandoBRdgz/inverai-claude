export interface NavItem {
  ruta: string;
  etiqueta: string;
  icono: string;
  descripcion: string;
  seccion: 'Principal' | 'Gestión';
}

/**
 * Fuente única de verdad del menú lateral. El Sidebar lo dibuja y la vista
 * Placeholder toma de aquí su título, icono y descripción mientras una pantalla
 * no esté construida. Para agregar una vista: añadir un ítem aquí y su ruta en
 * app.routes.ts.
 */
export const NAV_ITEMS: NavItem[] = [
  {
    ruta: '/chat',
    etiqueta: 'Asistente',
    icono: '💬',
    descripcion: 'Conversa con el asistente financiero de Inver-AI.',
    seccion: 'Principal',
  },
  {
    ruta: '/comparativa',
    etiqueta: 'Comparativa de compañías',
    icono: '⚖️',
    descripcion: 'Compara compañías lado a lado: indicadores, desempeño y riesgo.',
    seccion: 'Principal',
  },
  {
    ruta: '/portafolio',
    etiqueta: 'Mi portafolio',
    icono: '📊',
    descripcion: 'Consulta la composición y el rendimiento de tus inversiones.',
    seccion: 'Principal',
  },
  {
    ruta: '/historial',
    etiqueta: 'Historial',
    icono: '🕘',
    descripcion: 'Revisa y retoma tus conversaciones anteriores con el asistente.',
    seccion: 'Principal',
  },
  {
    ruta: '/admin',
    etiqueta: 'Administración',
    icono: '🛡️',
    descripcion: 'Gestión de usuarios y del sistema, y configuración de la plataforma.',
    seccion: 'Gestión',
  },
];

export const SECCIONES: NavItem['seccion'][] = ['Principal', 'Gestión'];
