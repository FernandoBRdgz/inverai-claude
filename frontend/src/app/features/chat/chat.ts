import { Component, ElementRef, inject, signal, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

import { Markdown } from '../../shared/components/markdown/markdown';
import { HistorialService } from '../../core/services/historial';
import { ChatService } from './services/chat';

type Voto = 'positivo' | 'negativo' | null;

interface MensajeChat {
  id: number;
  autor: 'usuario' | 'asistente';
  texto: string;
  // Solo aplica a mensajes del asistente: calificación 👍/👎
  voto?: Voto;
  mostrandoCaja?: boolean;
  confirmado?: boolean;
}

let contadorId = 0;

@Component({
  imports: [FormsModule, Markdown],
  selector: 'app-chat',
  styleUrl: './chat.css',
  templateUrl: './chat.html',
})
export class Chat {
  private readonly chatService = inject(ChatService);
  private readonly historial = inject(HistorialService);
  private readonly ruta = inject(ActivatedRoute);
  private readonly mensajesEl = viewChild<ElementRef<HTMLDivElement>>('mensajesEl');

  // Id de la conversación en el historial. Null hasta el primer mensaje real (se crea
  // de forma perezosa), salvo que se haya entrado a retomar una ya existente (?id=).
  private conversacionId: string | null = null;

  protected readonly mensajes = signal<MensajeChat[]>(this.mensajesIniciales());
  protected readonly escribiendo = signal(false);
  protected entrada = '';

  async enviar(): Promise<void> {
    const texto = this.entrada.trim();
    if (!texto) return; // ignora mensajes vacíos

    if (!this.conversacionId) {
      // Primer mensaje real de esta sesión de chat: recién aquí nace en el historial.
      this.conversacionId = this.historial.iniciarConversacion(texto);
    }
    this.historial.registrarMensaje(this.conversacionId, { autor: 'usuario', texto });

    this.agregarMensaje({ id: contadorId++, autor: 'usuario', texto });
    this.entrada = '';
    this.escribiendo.set(true);
    this.bajarScroll();

    try {
      // Llamada real al backend: la respuesta ya no se genera en el cliente.
      const respuesta = await this.chatService.enviarMensaje(texto);
      this.escribiendo.set(false);
      this.agregarMensaje({ id: contadorId++, autor: 'asistente', texto: respuesta, voto: null });
      this.historial.registrarMensaje(this.conversacionId, { autor: 'asistente', texto: respuesta });
    } catch {
      this.escribiendo.set(false);
      // El error de conexión no se guarda en el historial: no es una respuesta real.
      this.agregarMensaje({
        id: contadorId++,
        autor: 'asistente',
        texto: 'No fue posible contactar al servidor. Intente nuevamente en unos minutos.',
        voto: null,
      });
    }
  }

  // Alterna el voto de una respuesta; volver a pulsar el mismo botón lo anula (cambiar de opinión)
  seleccionarVoto(mensaje: MensajeChat, tipo: 'positivo' | 'negativo'): void {
    if (mensaje.voto === tipo) {
      mensaje.voto = null;
      mensaje.mostrandoCaja = false;
      mensaje.confirmado = false;
    } else {
      mensaje.voto = tipo;
      mensaje.confirmado = tipo === 'positivo';
      mensaje.mostrandoCaja = tipo === 'negativo';
    }
    this.mensajes.update((lista) => [...lista]);
  }

  finalizarRetroalimentacion(mensaje: MensajeChat): void {
    mensaje.mostrandoCaja = false;
    mensaje.confirmado = true;
    this.mensajes.update((lista) => [...lista]);
    this.bajarScroll();
  }

  private agregarMensaje(mensaje: MensajeChat): void {
    this.mensajes.update((lista) => [...lista, mensaje]);
    this.bajarScroll();
  }

  // Si la URL trae ?id= de una conversación guardada, la carga en vez del saludo de
  // bienvenida y sigue agregando a esa misma entrada del historial. Entrar por
  // "Asistente" en el menú (sin id) siempre arranca en blanco.
  private mensajesIniciales(): MensajeChat[] {
    const idParam = this.ruta.snapshot.queryParamMap.get('id');
    const conversacion = idParam ? this.historial.obtener(idParam) : undefined;

    if (conversacion) {
      this.conversacionId = conversacion.id;
      return conversacion.mensajes.map((m) => ({
        id: contadorId++,
        autor: m.autor,
        texto: m.texto,
        voto: m.autor === 'asistente' ? null : undefined,
      }));
    }

    return [
      {
        id: contadorId++,
        autor: 'asistente',
        texto: 'Bienvenido a Inver-AI. Soy su asistente financiero, escríbame lo que necesite.',
        voto: null,
      },
    ];
  }

  private bajarScroll(): void {
    setTimeout(() => {
      const el = this.mensajesEl()?.nativeElement;
      if (el) el.scrollTop = el.scrollHeight;
    });
  }
}
