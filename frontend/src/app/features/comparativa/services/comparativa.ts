import { Service, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { FiguraPlotly } from '../../../shared/components/plotly-chart/plotly-chart';

export type CategoriaGrafica = 'income' | 'fcf' | 'roic' | 'precio';

interface RespuestaGraficas {
  figuras: FiguraPlotly[];
}

/** Habla con GET /api/v1/comparativa/graficas (app/services/visualization.py en el backend). */
@Service()
export class ComparativaService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/comparativa`;

  async obtenerGraficas(ticker: string, categoria: CategoriaGrafica): Promise<FiguraPlotly[]> {
    const respuesta = await firstValueFrom(
      this.http.get<RespuestaGraficas>(`${this.baseUrl}/graficas`, { params: { ticker, categoria } })
    );
    return respuesta.figuras;
  }
}
