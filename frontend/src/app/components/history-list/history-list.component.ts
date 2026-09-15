import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ResearchService, ResearchRunSummary } from '../../services/research.service';

@Component({
  selector: 'app-history-list',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './history-list.component.html',
  styleUrls: ['./history-list.component.scss'],
})
export class HistoryListComponent implements OnChanges {
  @Input() activeId: string | null = null;
  @Input() refreshToken = 0;
  @Output() selected = new EventEmitter<string>();

  runs = signal<ResearchRunSummary[]>([]);

  constructor(private research: ResearchService) {
    this.load();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['refreshToken']) this.load();
  }

  load() {
    this.research.listRuns().subscribe(rs => this.runs.set(rs));
  }

  pick(id: string) {
    this.selected.emit(id);
  }

  formatRelative(iso: string): string {
    const d = new Date(iso);
    const diffMs = Date.now() - d.getTime();
    const m = Math.floor(diffMs / 60000);
    if (m < 1) return 'just now';
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    return d.toLocaleDateString();
  }
}
