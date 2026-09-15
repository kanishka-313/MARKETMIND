import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ResearchFormComponent } from './components/research-form/research-form.component';
import { AgentProgressComponent } from './components/agent-progress/agent-progress.component';
import { ReportViewComponent } from './components/report-view/report-view.component';
import { HistoryListComponent } from './components/history-list/history-list.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    ResearchFormComponent,
    AgentProgressComponent,
    ReportViewComponent,
    HistoryListComponent,
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent {
  activeRunId = signal<string | null>(null);
  refreshToken = signal(0);

  onRunStarted(id: string) {
    this.activeRunId.set(id);
    this.bumpRefresh();
  }

  onHistoryPicked(id: string) {
    this.activeRunId.set(id);
  }

  onStreamEnded() {
    // Refresh report panel + history when stream finishes
    this.bumpRefresh();
  }

  private bumpRefresh() {
    this.refreshToken.update(v => v + 1);
  }
}
