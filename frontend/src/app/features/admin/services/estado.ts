import { Service, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../../environments/environment';

export interface EstadoSistema {
  status: string;
  openai_configurado: boolean;
  alphavantage_configurado: boolean;
  modelo: string;
}

// /health vive en la raíz del backend, no bajo /api/v1 (es el chequeo operativo, no una
// ruta de negocio) — se deriva quitando el sufijo de environment.apiUrl.
const BASE_URL = environment.apiUrl.replace(/\/api\/v1\/?$/, '');

/** Consulta /health: da la base para el panel de estado de Administración. */
@Service()
export class EstadoService {
  private readonly http = inject(HttpClient);

  obtenerEstado(): Promise<EstadoSistema> {
    return firstValueFrom(this.http.get<EstadoSistema>(`${BASE_URL}/health`));
  }
}
