import React, { useState } from 'react';
import { 
  Database, 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle, 
  Cpu, 
  Globe2, 
  MessageSquare, 
  Newspaper,
  Layers
} from 'lucide-react';
import { api } from '../services/api';
import { SystemStatus } from '../types/api';

interface Props {
  status: SystemStatus | null;
  onRefreshAll: () => void;
}

export const OperationsPage: React.FC<Props> = ({ status, onRefreshAll }) => {
  const [runningAction, setRunningAction] = useState<string | null>(null);
  const [adminKeyInput, setAdminKeyInput] = useState<string>(() => api.getAdminKey() || '');
  const [isKeySaved, setIsKeySaved] = useState<boolean>(() => Boolean(api.getAdminKey()));
  const [consoleLogs, setConsoleLogs] = useState<string[]>([
    '[SYSTEM] Sentinel AI Data Operations Console initialized.',
    status 
      ? `[TELEMETRY] Connected to SQLite database (${(status.historical_bars_count ?? 0).toLocaleString()} market bars, ${status.news_articles_count ?? 0} news articles, ${status.discourse_posts_count ?? 0} social posts).`
      : '[TELEMETRY] Connected to SQLite database store.',
    status
      ? `[FinBERT] Local ProsusAI/finbert status: ${status.finbert_status || 'UNKNOWN'}.`
      : '[FinBERT] Checking local ProsusAI/finbert status...',
  ]);

  const addLog = (msg: string) => {
    setConsoleLogs(prev => [msg, ...prev.slice(0, 49)]);
  };

  const handleSaveKey = () => {
    api.setAdminKey(adminKeyInput.trim() || null);
    setIsKeySaved(Boolean(adminKeyInput.trim()));
    addLog(adminKeyInput.trim() ? '[AUTH] Session operator key stored.' : '[AUTH] Session operator key cleared.');
  };

  const handleTrigger = async (name: string, fn: () => Promise<any>) => {
    setRunningAction(name);
    addLog(`[ACTION] Initiating ${name}...`);
    try {
      const res = await fn();
      addLog(`[SUCCESS] ${name} completed: ${JSON.stringify(res).slice(0, 120)}...`);
      onRefreshAll();
    } catch (err: any) {
      addLog(`[ERROR] ${name} failed: ${err.message}`);
    } finally {
      setRunningAction(null);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-[#1b263b] gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <Database className="w-5 h-5 text-[#00b0ff]" />
            <h1 className="text-xl font-bold tracking-tight text-white">
              Data Operations & Pipeline Management
            </h1>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
              status?.database_connected 
                ? 'bg-[#00e676]/10 text-[#00e676] border-[#00e676]/30' 
                : 'bg-[#ffd600]/10 text-[#ffd600] border-[#ffd600]/30'
            }`}>
              {status?.database_connected ? 'OPERATIONAL' : 'SYSTEM STANDBY'}
            </span>
          </div>
          <p className="text-xs text-[#94a3b8] mt-1">
            Trigger live ingestion tasks, invoke NLP sentiment recalculations, and retrain quantitative prediction models.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono">
          <span className="px-3 py-1.5 rounded bg-[#0d1522] border border-[#1d2b3f] text-[#00e676] flex items-center space-x-1.5">
            <span className={`w-2 h-2 rounded-full ${status?.database_connected ? 'bg-[#00e676] animate-pulse' : 'bg-[#ffd600]'}`} />
            <span>{status?.database_connected ? 'SQLite Engine Online' : 'Connecting to DB...'}</span>
          </span>
        </div>
      </div>

      {/* Operator Session Authentication Banner */}
      <div className="bg-[#0b1320] border border-[#1c2a40] rounded p-4 flex flex-col md:flex-row items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className={`w-2 h-2 rounded-full ${isKeySaved ? 'bg-[#00e676]' : 'bg-[#ffd600]'}`} />
            <h4 className="text-xs font-mono font-bold uppercase text-white">Operator Access Control</h4>
          </div>
          <p className="text-[11px] text-[#94a3b8] mt-0.5">
            Privileged pipeline operations require the operator access key configured on the server.
          </p>
        </div>
        <div className="flex items-center space-x-2 w-full md:w-auto">
          <input
            type="password"
            value={adminKeyInput}
            onChange={(e) => setAdminKeyInput(e.target.value)}
            placeholder="Enter operator key..."
            className="bg-[#070b12] border border-[#1b263b] text-white text-xs px-3 py-1.5 rounded focus:outline-none focus:border-[#00b0ff] font-mono w-full md:w-64"
          />
          <button
            onClick={handleSaveKey}
            className="px-3 py-1.5 bg-[#1b263b] hover:bg-[#253550] text-[#00b0ff] text-xs font-mono rounded transition shrink-0"
          >
            {isKeySaved ? 'Update' : 'Authorize'}
          </button>
        </div>
      </div>

      {/* Control Actions Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#0e1626] border border-[#1c2a40] rounded p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 text-[#00b0ff] mb-2">
              <Globe2 className="w-4 h-4" />
              <h3 className="font-mono text-xs font-bold uppercase text-white">Market OHLCV Feed</h3>
            </div>
            <p className="text-[11px] text-[#94a3b8]">
              Collect historical bars and spot prices across all 10 HKEX and KRX tracked assets.
            </p>
          </div>
          <button
            onClick={() => handleTrigger('Market Ingestion', () => api.triggerMarketCollection())}
            disabled={runningAction !== null}
            className="mt-4 w-full py-2 bg-[#141e30] hover:bg-[#1a2842] border border-[#213452] text-[#00b0ff] font-mono text-xs rounded transition disabled:opacity-50"
          >
            {runningAction === 'Market Ingestion' ? 'Ingesting...' : 'Collect Market Bars'}
          </button>
        </div>

        <div className="bg-[#0e1626] border border-[#1c2a40] rounded p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 text-[#ffd600] mb-2">
              <Newspaper className="w-4 h-4" />
              <h3 className="font-mono text-xs font-bold uppercase text-white">Curated Financial News</h3>
            </div>
            <p className="text-[11px] text-[#94a3b8]">
              Execute Exa API and verified financial wire collection with publisher de-duplication.
            </p>
          </div>
          <button
            onClick={() => handleTrigger('News Ingestion', () => api.triggerNewsCollection())}
            disabled={runningAction !== null}
            className="mt-4 w-full py-2 bg-[#141e30] hover:bg-[#1a2842] border border-[#213452] text-[#ffd600] font-mono text-xs rounded transition disabled:opacity-50"
          >
            {runningAction === 'News Ingestion' ? 'Ingesting...' : 'Ingest Real News'}
          </button>
        </div>

        <div className="bg-[#0e1626] border border-[#1c2a40] rounded p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 text-[#00e676] mb-2">
              <MessageSquare className="w-4 h-4" />
              <h3 className="font-mono text-xs font-bold uppercase text-white">Discourse Scraper</h3>
            </div>
            <p className="text-[11px] text-[#94a3b8]">
              Scrape authentic posts and cashtag mentions across market forums and StockTwits.
            </p>
          </div>
          <button
            onClick={() => handleTrigger('Social Ingestion', () => api.triggerSocialCollection())}
            disabled={runningAction !== null}
            className="mt-4 w-full py-2 bg-[#141e30] hover:bg-[#1a2842] border border-[#213452] text-[#00e676] font-mono text-xs rounded transition disabled:opacity-50"
          >
            {runningAction === 'Social Ingestion' ? 'Scraping...' : 'Collect Social Discourse'}
          </button>
        </div>

        <div className="bg-[#0e1626] border border-[#1c2a40] rounded p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 text-[#a855f7] mb-2">
              <Cpu className="w-4 h-4" />
              <h3 className="font-mono text-xs font-bold uppercase text-white">Retrain ML Suite</h3>
            </div>
            <p className="text-[11px] text-[#94a3b8]">
              Execute full chronological walk-forward retraining across all 4 architectures and 10 assets.
            </p>
          </div>
          <button
            onClick={() => handleTrigger('ML Retraining', () => api.triggerModelTraining())}
            disabled={runningAction !== null}
            className="mt-4 w-full py-2 bg-[#1b1730] hover:bg-[#251e44] border border-[#3b2b64] text-[#c084fc] font-mono text-xs rounded transition disabled:opacity-50"
          >
            {runningAction === 'ML Retraining' ? 'Training...' : 'Retrain All 40 Models'}
          </button>
        </div>
      </div>

      {/* Operational Console Telemetry Output */}
      <div className="bg-[#0a0e17] border border-[#1c2a40] rounded p-4 font-mono text-xs">
        <div className="flex items-center justify-between pb-2 border-b border-[#1b263b] mb-3">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-[#00e676]" />
            <span className="font-bold text-white uppercase text-[11px]">Pipeline Operations Log</span>
          </div>
          <span className="text-[10px] text-[#64748b]">AUTO-SCROLLING</span>
        </div>

        <div className="h-64 overflow-y-auto space-y-1 text-[11px]">
          {consoleLogs.map((log, i) => (
            <div 
              key={i} 
              className={`leading-relaxed ${
                log.includes('[ERROR]') ? 'text-[#ff3d57]' : 
                log.includes('[SUCCESS]') ? 'text-[#00e676]' : 
                log.includes('[ACTION]') ? 'text-[#00b0ff]' : 'text-[#94a3b8]'
              }`}
            >
              <span className="text-[#475569] mr-2">[{new Date().toLocaleTimeString()}]</span>
              <span>{log}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
