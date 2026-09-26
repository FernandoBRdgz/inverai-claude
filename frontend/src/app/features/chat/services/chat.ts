import { Service, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../../environments/environment';

export interface RespuestaAsistente {
  respuesta: string;
}

/**
 * Habla con el backend de Inver-AI (FastAPI). Reemplaza la antigua función
 * saludoAleatorio() del cliente: la respuesta ya no vive en el navegador.
 */
@Service()
export class ChatService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/chat`;

  async enviarMensaje(mensaje: string): Promise<string> {
    const respuesta = await firstValueFrom(
      this.http.post<RespuestaAsistente>(this.baseUrl, { mensaje })
    );
    return respuesta.respuesta;
  }
}
