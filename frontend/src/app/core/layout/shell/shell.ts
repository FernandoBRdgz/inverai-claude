import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { Sidebar } from '../sidebar/sidebar';

/** Layout de las vistas internas: panel lateral colapsable + contenido de la ruta activa. */
@Component({
  imports: [RouterOutlet, Sidebar],
  selector: 'app-shell',
  styleUrl: './shell.css',
  templateUrl: './shell.html',
})
export class Shell {}
