import { TestBed } from '@angular/core/testing';

import { Markdown, markdownAHtml } from './markdown';

async function renderizar(contenido: string): Promise<HTMLElement> {
  await TestBed.configureTestingModule({ imports: [Markdown] }).compileComponents();
  const fixture = TestBed.createComponent(Markdown);
  fixture.componentRef.setInput('contenido', contenido);
  await fixture.whenStable();
  return fixture.nativeElement as HTMLElement;
}

describe('markdownAHtml', () => {
  it('convierte encabezados, negritas, cursivas y listas', () => {
    const html = markdownAHtml('## Título\n\n**fuerte** y *suave*\n\n- uno\n- dos');

    expect(html).toContain('<h2>Título</h2>');
    expect(html).toContain('<strong>fuerte</strong>');
    expect(html).toContain('<em>suave</em>');
    expect(html).toContain('<li>uno</li>');
  });

  it('conserva los emojis, también junto a negritas y en encabezados', () => {
    const html = markdownAHtml('## 📌 ROIC\n\n💼✨ **Rol** 📈**pegado**a emoji\n\n- ✅ listo\n- ⚠️ ojo');

    expect(html).toContain('<h2>📌 ROIC</h2>');
    expect(html).toContain('💼✨ <strong>Rol</strong>');
    expect(html).toContain('📈<strong>pegado</strong>a emoji');
    expect(html).toContain('<li>✅ listo</li>');
    expect(html).toContain('<li>⚠️ ojo</li>');
  });

  it('renderiza tablas GFM', () => {
    const html = markdownAHtml('| Empresa | ROIC |\n|---|---|\n| AAPL 🍎 | 45% |');

    expect(html).toContain('<table>');
    expect(html).toContain('<th>Empresa</th>');
    expect(html).toContain('<td>AAPL 🍎</td>');
  });

  it('trata un salto de línea simple como salto visible (estilo chat)', () => {
    expect(markdownAHtml('línea uno\nlínea dos')).toContain('<br>');
  });

  it('muestra el HTML crudo como texto en vez de interpretarlo', () => {
    const html = markdownAHtml('<script>alert(1)</script> y <img src=x onerror=alert(2)>');

    expect(html).not.toContain('<script');
    expect(html).not.toContain('<img');
    expect(html).toContain('&lt;script&gt;');
  });

  it('solo enlaza URLs http(s) y mailto, y las abre en pestaña nueva', () => {
    const bien = markdownAHtml('[sitio](https://example.com)');
    expect(bien).toContain('href="https://example.com"');
    expect(bien).toContain('target="_blank"');
    expect(bien).toContain('rel="noopener noreferrer"');

    const mal = markdownAHtml('[peligro](javascript:alert(1))');
    expect(mal).not.toContain('<a');
    expect(mal).toContain('peligro');
  });

  it('no carga imágenes remotas: deja solo el texto alternativo', () => {
    const html = markdownAHtml('![logo](https://ejemplo.com/pixel.png)');

    expect(html).not.toContain('<img');
    expect(html).toContain('logo');
  });

  it('muestra las listas de tareas como símbolos de texto', () => {
    const html = markdownAHtml('- [x] hecho\n- [ ] pendiente');

    expect(html).toContain('☑');
    expect(html).toContain('☐');
    expect(html).not.toContain('<input');
  });
});

describe('Markdown (componente)', () => {
  it('pinta el contenido dentro de .markdown', async () => {
    const el = await renderizar('## 📌 Título\n\nHola **mundo** 💰');

    expect(el.querySelector('.markdown h2')?.textContent).toBe('📌 Título');
    expect(el.querySelector('.markdown strong')?.textContent).toBe('mundo');
    expect(el.textContent).toContain('💰');
  });

  it('no deja scripts ni manejadores de eventos en el DOM', async () => {
    const el = await renderizar('<script>window.__xss = 1</script>\n\n<img src=x onerror="window.__xss = 2">');

    expect(el.querySelector('script')).toBeNull();
    expect(el.querySelector('img')).toBeNull();
    // El código aparece como texto visible, pero ningún elemento lleva manejadores de eventos.
    expect(el.querySelector('[onerror]')).toBeNull();
    expect(el.textContent).toContain('<script>');
    expect((window as unknown as Record<string, unknown>)['__xss']).toBeUndefined();
  });

  it('renderiza una tabla como elemento <table>', async () => {
    const el = await renderizar('| A | B |\n|---|---|\n| 1 | 2 |');

    expect(el.querySelectorAll('.markdown table th').length).toBe(2);
    expect(el.querySelectorAll('.markdown table td').length).toBe(2);
  });
});
