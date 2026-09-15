import { Component, Input, OnChanges, SimpleChanges, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { marked } from 'marked';
import { ResearchService, ResearchRunDetail } from '../../services/research.service';

@Component({
  selector: 'app-report-view',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './report-view.component.html',
  styleUrls: ['./report-view.component.scss'],
})
export class ReportViewComponent implements OnChanges {
  @Input() runId: string | null = null;
  @Input() refreshToken = 0;     // bumped by parent when stream completes

  run = signal<ResearchRunDetail | null>(null);
  reportHtml = signal<string>('');
  loading = signal(false);

  constructor(private research: ResearchService) {}

  ngOnChanges(changes: SimpleChanges) {
    if ((changes['runId'] || changes['refreshToken']) && this.runId) {
      this.load(this.runId);
    } else if (!this.runId) {
      this.run.set(null);
      this.reportHtml.set('');
    }
  }

  private load(id: string) {
    this.loading.set(true);
    this.research.getRun(id).subscribe({
      next: data => {
        this.run.set(data);
        if (data.final_report) {
          this.reportHtml.set(marked.parse(data.final_report) as string);
        } else {
          this.reportHtml.set('');
        }
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  download() {
    const r = this.run();
    if (!r?.final_report) return;
    const blob = new Blob([r.final_report], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${r.symbol}_brief_${r.id.slice(0, 8)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }
}
