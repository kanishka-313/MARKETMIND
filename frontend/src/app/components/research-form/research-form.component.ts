import { Component, EventEmitter, Output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ResearchService } from '../../services/research.service';

@Component({
  selector: 'app-research-form',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './research-form.component.html',
  styleUrls: ['./research-form.component.scss'],
})
export class ResearchFormComponent {
  @Output() runStarted = new EventEmitter<string>();

  symbol = '';
  submitting = signal(false);
  error = signal<string | null>(null);

  readonly samples = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'AMZN'];

  constructor(private research: ResearchService) {}

  pick(s: string) {
    this.symbol = s;
  }

  submit() {
    const s = this.symbol.trim().toUpperCase();
    if (!s) {
      this.error.set('Enter a ticker symbol');
      return;
    }
    this.error.set(null);
    this.submitting.set(true);
    this.research.startResearch(s).subscribe({
      next: run => {
        this.submitting.set(false);
        this.runStarted.emit(run.id);
        this.symbol = '';
      },
      error: err => {
        this.submitting.set(false);
        this.error.set(err?.error?.detail || 'Failed to start research');
      },
    });
  }
}
