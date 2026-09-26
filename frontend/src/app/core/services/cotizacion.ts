import { Service, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';

interface RespuestaCotizacion {
  ticker: string;
  precio: number;
}

/** Habla con GET /api/v1/cotizacion (AlphaVantage GLOBAL_QUOTE vía app/services/alphavantage.py).
 * La usa Portafolio para autocompletar el precio por acción al dar de alta una posición. */
@Service()
export class CotizacionService {
  private readonly http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/cotizacion`;

  async obtenerPrecio(ticker: string): Promise<number> {
    const respuesta = await firstValueFrom(
      this.http.get<RespuestaCotizacion>(this.url, { params: { ticker } })
    );
    return respuesta.precio;
  }
}
