import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, Subject } from 'rxjs';

export interface ResearchRunSummary {
  id: string;
  symbol: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  completed_at?: string | null;
}

export interface AgentLog {
  agent_name: string;
  status: 'started' | 'progress' | 'completed' | 'failed';
  message: string;
  payload?: any;
  created_at: string;
}

export interface ResearchRunDetail extends ResearchRunSummary {
  final_report?: string | null;
  error?: string | null;
  logs: AgentLog[];
}

export interface StreamEvent {
  type: 'agent_log' | 'run_completed' | 'run_failed' | 'end';
  agent?: string;
  status?: string;
  message?: string;
  payload?: any;
  report?: string;
  error?: string;
  ts?: string;
}

@Injectable({ providedIn: 'root' })
export class ResearchService {
  private readonly API = 'http://localhost:8000/api';

  constructor(private http: HttpClient) {}

  startResearch(symbol: string): Observable<ResearchRunSummary> {
    return this.http.post<ResearchRunSummary>(`${this.API}/research`, { symbol });
  }

  listRuns(): Observable<ResearchRunSummary[]> {
    return this.http.get<ResearchRunSummary[]>(`${this.API}/runs`);
  }

  getRun(id: string): Observable<ResearchRunDetail> {
    return this.http.get<ResearchRunDetail>(`${this.API}/runs/${id}`);
  }

  /** Subscribe to server-sent events for a run. */
  streamRun(id: string): Observable<StreamEvent> {
    const subject = new Subject<StreamEvent>();
    const es = new EventSource(`${this.API}/runs/${id}/stream`);

    const handle = (type: StreamEvent['type']) => (ev: MessageEvent) => {
      try {
        const data = JSON.parse(ev.data);
        subject.next({ ...data, type });
      } catch {
        subject.next({ type });
      }
    };

    es.addEventListener('agent_log', handle('agent_log') as EventListener);
    es.addEventListener('run_completed', handle('run_completed') as EventListener);
    es.addEventListener('run_failed', handle('run_failed') as EventListener);
    es.addEventListener('end', () => { subject.next({ type: 'end' }); es.close(); subject.complete(); });
    es.addEventListener('ping', () => { /* keepalive */ });
    es.onerror = () => { es.close(); subject.complete(); };

    return subject.asObservable();
  }
}
