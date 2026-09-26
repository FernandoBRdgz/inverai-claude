import { Component, ElementRef, OnDestroy, effect, inject, input, viewChild } from '@angular/core';

import { Theme } from '../../../core/services/theme';

// Plotly.js se carga por CDN en src/index.html (ver ese archivo para el porqué).
declare const Plotly: any;

export interface FiguraPlotly {
  data: unknown[];
  layout?: Record<string, unknown>;
}

/**
 * Wrapper delgado sobre Plotly.js: recibe una figura ya generada por el backend
 * (app/services/visualization.py) y solo se encarga de dibujarla y de que respete
 * el tema claro/oscuro de la app (Plotly no sabe nada de nuestros temas).
 */
@Component({
  selector: 'app-plotly-chart',
  templateUrl: './plotly-chart.html',
  styleUrl: './plotly-chart.css',
})
export class PlotlyChart implements OnDestroy {
  readonly figura = input.required<FiguraPlotly>();

  private readonly theme = inject(Theme);
  private readonly contenedor = viewChild.required<ElementRef<HTMLDivElement>>('contenedor');
  private dibujado = false;

  constructor() {
    effect(() => {
      const fig = this.figura();
      this.theme.tema(); // se lee para que un cambio de tema vuelva a dibujar con los nuevos colores
      if (typeof Plotly === 'undefined') return; // el CDN aún no cargó o falló

      const colorTexto = getComputedStyle(document.documentElement).getPropertyValue('--texto').trim();
      const layout = {
        ...fig.layout,
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { color: colorTexto || '#1c2430', ...(fig.layout?.['font'] as object) },
        margin: fig.layout?.['margin'] ?? { t: 36, r: 16, b: 40, l: 50 },
      };

      Plotly.react(this.contenedor().nativeElement, fig.data, layout, {
        responsive: true,
        displaylogo: false,
      });
      this.dibujado = true;
    });
  }

  ngOnDestroy(): void {
    if (this.dibujado && typeof Plotly !== 'undefined') {
      Plotly.purge(this.contenedor().nativeElement);
    }
  }
}
