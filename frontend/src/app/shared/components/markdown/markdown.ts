import { Component, ViewEncapsulation, computed, input } from '@angular/core';
import { Marked } from 'marked';

const ENTIDADES: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
};
const escapar = (texto: string): string => texto.replace(/[&<>"']/g, (c) => ENTIDADES[c]);

// Solo se permiten enlaces web y de correo (nada de javascript:, data:, etc.).
const esUrlSegura = (href: string): boolean => /^(https?:|mailto:)/i.test(href.trim());

/**
 * Convierte el Markdown (GFM) que devuelve el asistente en HTML.
 * El contenido lo genera un modelo, así que se trata como no confiable:
 *  - el HTML crudo se muestra como texto, no se interpreta;
 *  - los enlaces se abren en pestaña nueva y solo si son http(s)/mailto;
 *  - las imágenes no se cargan (se muestra su texto alternativo), para que la
 *    respuesta no pueda disparar peticiones a servidores externos;
 *  - además, Angular vuelve a sanear el resultado al enlazarlo con [innerHTML].
 */
const conversor = new Marked({
  gfm: true, // tablas, tachado, listas de tareas
  breaks: true, // un salto de línea simple es un salto visible (estilo chat)
  renderer: {
    html: ({ text }) => escapar(text),
    image: ({ text }) => escapar(text),
    checkbox: ({ checked }) => (checked ? '☑ ' : '☐ '),
    link({ href, title, tokens }) {
      const texto = this.parser.parseInline(tokens);
      if (!esUrlSegura(href)) return texto;
      const atributoTitulo = title ? ` title="${escapar(title)}"` : '';
      return `<a href="${escapar(href)}"${atributoTitulo} target="_blank" rel="noopener noreferrer">${texto}</a>`;
    },
  },
});

/** Convierte Markdown a HTML (sin sanear: Angular lo hace al enlazarlo con [innerHTML]). */
export function markdownAHtml(markdown: string): string {
  return conversor.parse(markdown, { async: false });
}

/** Muestra texto en Markdown con el estilo de la app. Los emojis se conservan tal cual. */
@Component({
  selector: 'app-markdown',
  templateUrl: './markdown.html',
  styleUrl: './markdown.css',
  // El HTML se inserta dinámicamente y no lleva los atributos de encapsulación de Angular,
  // por eso los estilos son globales (siempre acotados bajo la clase .markdown).
  encapsulation: ViewEncapsulation.None,
})
export class Markdown {
  readonly contenido = input.required<string>();
  protected readonly html = computed(() => markdownAHtml(this.contenido()));
}
