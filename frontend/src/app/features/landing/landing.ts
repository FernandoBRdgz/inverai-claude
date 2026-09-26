import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Theme } from '../../core/services/theme';

@Component({
  imports: [RouterLink],
  selector: 'app-landing',
  styleUrl: './landing.css',
  templateUrl: './landing.html',
})
export class Landing {
  protected readonly theme = inject(Theme);
}
