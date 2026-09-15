import { Component, EventEmitter, Input, OnChanges, OnDestroy, Output, SimpleChanges, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { ResearchService, StreamEvent } from '../../services/research.service';

interface LogEntry {
  agent: string;
  status: string;
  message: string;
  ts: string;
}

@Component({
  selector: 'app-agent-progress',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './agent-progress.component.html',
  styleUrls: ['./agent-progress.component.scss'],
})
export class AgentProgressComponent implements OnChanges, OnDestroy {
  @Input() runId: string | null = null;
  @Output() streamEnded = new EventEmitter<void>();

  logs = signal<LogEntry[]>([]);
  streaming = signal(false);
  private sub?: Subscription;

  // Agent registry for the rail
  agents = ['News Agent', 'Fundamentals Agent', 'Technical Agent', 'Report Compiler'];
  agentState = signal<Record<string, 'idle' | 'running' | 'done' | 'failed'>>({});

  constructor(private research: ResearchService) {}

  ngOnChanges(changes: SimpleChanges) {
    if (changes['runId']) {
      this.reset();
      if (this.runId) this.connect(this.runId);
    }
  }

  private reset() {
    this.sub?.unsubscribe();
    this.logs.set([]);
    this.streaming.set(false);
    const fresh: Record<string, 'idle'> = {};
    this.agents.forEach(a => fresh[a] = 'idle');
    this.agentState.set(fresh);
  }

  private connect(id: string) {
    this.streaming.set(true);
    this.sub = this.research.streamRun(id).subscribe({
      next: (ev: StreamEvent) => this.handle(ev),
      complete: () => { this.streaming.set(false); this.streamEnded.emit(); },
      error: () => { this.streaming.set(false); this.streamEnded.emit(); },
    });
  }

  private handle(ev: StreamEvent) {
    if (ev.type === 'agent_log' && ev.agent) {
      this.logs.update(arr => [...arr, {
        agent: ev.agent!, status: ev.status || '', message: ev.message || '', ts: ev.ts || '',
      }]);
      const next = { ...this.agentState() };
      if (ev.status === 'started' || ev.status === 'progress') next[ev.agent] = 'running';
      else if (ev.status === 'completed') next[ev.agent] = 'done';
      else if (ev.status === 'failed') next[ev.agent] = 'failed';
      this.agentState.set(next);
    } else if (ev.type === 'end') {
      this.streaming.set(false);
    }
  }

  trackIdx(i: number) { return i; }

  ngOnDestroy() { this.sub?.unsubscribe(); }

  formatTime(iso: string): string {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleTimeString('en-GB', { hour12: false });
  }
}
