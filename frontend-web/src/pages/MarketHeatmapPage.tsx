import React, { useState, useMemo } from 'react';
import { AssetSignal } from '../types/api';
import { LayoutGrid, Filter, RefreshCw, Info, ArrowUpRight, ArrowDownRight, Layers } from 'lucide-react';

interface Props {
  signals: AssetSignal[];
  onSelectTicker: (ticker: string) => void;
  onNavigatePage: (page: any) => void;
}

type HeatmapMode = 'predicted' | 'sentiment' | 'volume' | 'signal';

export const MarketHeatmapPage: React.FC<Props> = ({ signals, onSelectTicker, onNavigatePage }) => {
  const [exchangeFilter, setExchangeFilter] = useState<'ALL' | 'HKEX' | 'KRX'>('ALL');
  const [mode, setMode] = useState<HeatmapMode>('predicted');

  const filtered = useMemo(() => {
    return signals.filter(s => exchangeFilter === 'ALL' || s.exchange === exchangeFilter);
  }, [signals, exchangeFilter]);

  // Compute color based on mode and value
  const getTileStyle = (asset: AssetSignal) => {
    if (mode === 'predicted') {
      const val = asset.predicted_return_pct;
      if (val >= 2.0) return { bg: 'bg-[#00e676]/25 border-[#00e676]/60 text-[#00e676]', tag: '+>2%' };
      if (val > 0.0) return { bg: 'bg-[#00e676]/15 border-[#00e676]/40 text-[#00e676]', tag: 'Positive' };
      if (val === 0.0) return { bg: 'bg-[#1e293b]/50 border-[#334155] text-[#94a3b8]', tag: 'Flat' };
      if (val > -2.0) return { bg: 'bg-[#ff3d57]/15 border-[#ff3d57]/40 text-[#ff3d57]', tag: 'Negative' };
      return { bg: 'bg-[#ff3d57]/25 border-[#ff3d57]/60 text-[#ff3d57]', tag: '<-2%' };
    }
    if (mode === 'sentiment') {
      const score = asset.sentiment_score;
      if (score >= 0.1) return { bg: 'bg-[#00e676]/20 border-[#00e676]/50 text-[#00e676]', tag: 'Bullish' };
      if (score <= -0.1) return { bg: 'bg-[#ff3d57]/20 border-[#ff3d57]/50 text-[#ff3d57]', tag: 'Bearish' };
      return { bg: 'bg-[#00b0ff]/15 border-[#00b0ff]/40 text-[#00b0ff]', tag: 'Neutral' };
    }
    if (mode === 'volume') {
      const vol = asset.social_mentions + asset.news_count;
      if (vol >= 30) return { bg: 'bg-[#00b0ff]/25 border-[#00b0ff]/60 text-[#00b0ff]', tag: 'High Activity' };
      if (vol >= 10) return { bg: 'bg-[#00b0ff]/15 border-[#00b0ff]/40 text-[#38bdf8]', tag: 'Moderate' };
      return { bg: 'bg-[#1e293b]/50 border-[#334155] text-[#94a3b8]', tag: 'Low' };
    }
    // signal strength
    const sig = asset.signal_strength;
    if (sig >= 70) return { bg: 'bg-[#ffd600]/25 border-[#ffd600]/60 text-[#ffd600]', tag: 'High Conviction' };
    if (sig >= 50) return { bg: 'bg-[#ffd600]/15 border-[#ffd600]/40 text-[#fde047]', tag: 'Medium' };
    return { bg: 'bg-[#1e293b]/50 border-[#334155] text-[#94a3b8]', tag: 'Low' };
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-mono">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-[#1b263b] gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <LayoutGrid className="w-5 h-5 text-[#00b0ff]" />
            <h1 className="text-xl font-bold tracking-tight text-white">
              Market Heatmap Matrix
            </h1>
            <span className="text-[10px] px-2 py-0.5 rounded bg-[#00e676]/10 text-[#00e676] border border-[#00e676]/30">
              CROSS-SECTIONAL TILES
            </span>
          </div>
          <p className="text-xs text-[#94a3b8] mt-1">
            Equal-weight comparative matrix ranking all 10 monitored equities across predicted returns, FinBERT discourse scores, and density metrics.
          </p>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Mode Selector */}
          <div className="flex items-center space-x-1 bg-[#0e1626] border border-[#1c2a40] p-1 rounded text-xs">
            <button
              onClick={() => setMode('predicted')}
              className={`px-2.5 py-1 rounded transition ${mode === 'predicted' ? 'bg-[#00b0ff]/20 text-[#00b0ff] font-bold' : 'text-[#64748b] hover:text-white'}`}
            >
              Predicted Alpha
            </button>
            <button
              onClick={() => setMode('sentiment')}
              className={`px-2.5 py-1 rounded transition ${mode === 'sentiment' ? 'bg-[#00b0ff]/20 text-[#00b0ff] font-bold' : 'text-[#64748b] hover:text-white'}`}
            >
              FinBERT Sentiment
            </button>
            <button
              onClick={() => setMode('volume')}
              className={`px-2.5 py-1 rounded transition ${mode === 'volume' ? 'bg-[#00b0ff]/20 text-[#00b0ff] font-bold' : 'text-[#64748b] hover:text-white'}`}
            >
              Discourse Hits
            </button>
            <button
              onClick={() => setMode('signal')}
              className={`px-2.5 py-1 rounded transition ${mode === 'signal' ? 'bg-[#00b0ff]/20 text-[#00b0ff] font-bold' : 'text-[#64748b] hover:text-white'}`}
            >
              Conviction (0-100)
            </button>
          </div>

          {/* Exchange Filter */}
          <div className="flex items-center space-x-1 bg-[#0e1626] border border-[#1c2a40] p-1 rounded text-xs">
            {(['ALL', 'HKEX', 'KRX'] as const).map(ex => (
              <button
                key={ex}
                onClick={() => setExchangeFilter(ex)}
                className={`px-2 py-1 rounded transition ${exchangeFilter === ex ? 'bg-[#1b263b] text-white font-bold' : 'text-[#64748b] hover:text-white'}`}
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Heatmap Grid (Equal Tiles Layout, responsive 2 to 5 columns) */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {filtered.map(asset => {
          const style = getTileStyle(asset);
          return (
            <div
              key={asset.ticker}
              onClick={() => {
                onSelectTicker(asset.ticker);
                onNavigatePage('asset');
              }}
              className={`p-4 rounded border ${style.bg} hover:border-[#00b0ff] transition cursor-pointer flex flex-col justify-between h-44 group relative overflow-hidden`}
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-base font-bold text-white group-hover:text-[#00b0ff] transition">
                    {asset.ticker}
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#090d16] text-[#94a3b8] border border-[#1b273d]">
                    {asset.exchange}
                  </span>
                </div>
                <div className="text-xs text-[#94a3b8] truncate mt-0.5 font-medium">
                  {asset.asset_name}
                </div>
                <div className="text-[10px] text-[#64748b] mt-0.5">
                  {asset.sector}
                </div>
              </div>

              {/* Center Metric Display */}
              <div className="my-2">
                {mode === 'predicted' ? (
                  <div>
                    <div className="text-xl font-bold">
                      {asset.predicted_return_pct > 0 ? '+' : ''}{asset.predicted_return_pct.toFixed(2)}%
                    </div>
                    <div className="text-[10px] text-[#94a3b8]">Consensus Return</div>
                  </div>
                ) : mode === 'sentiment' ? (
                  <div>
                    <div className="text-xl font-bold">
                      {asset.sentiment_score > 0 ? '+' : ''}{asset.sentiment_score.toFixed(3)}
                    </div>
                    <div className="text-[10px] text-[#94a3b8]">FinBERT {asset.overall_sentiment}</div>
                  </div>
                ) : mode === 'volume' ? (
                  <div>
                    <div className="text-xl font-bold">
                      {asset.social_mentions + asset.news_count}
                    </div>
                    <div className="text-[10px] text-[#94a3b8]">Posts & Articles</div>
                  </div>
                ) : (
                  <div>
                    <div className="text-xl font-bold text-[#ffd600]">
                      {asset.signal_strength} / 100
                    </div>
                    <div className="text-[10px] text-[#94a3b8]">Signal Conviction</div>
                  </div>
                )}
              </div>

              {/* Bottom Row */}
              <div className="flex justify-between items-center text-[10px] pt-2 border-t border-white/10 text-[#cbd5e1]">
                <span>{asset.latest_price.toLocaleString()} {asset.currency}</span>
                <span className="uppercase font-semibold">{style.tag}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Heatmap Legend */}
      <div className="p-3 bg-[#0e1626] border border-[#1c2a40] rounded text-xs flex flex-col md:flex-row md:items-center justify-between text-[#94a3b8] gap-3">
        <div className="flex items-center space-x-2">
          <Info className="w-4 h-4 text-[#00b0ff]" />
          <span>Click any equity rectangle to inspect full quantitative micro-intelligence & historical indicators.</span>
        </div>
        <div className="flex items-center space-x-3 text-[11px]">
          <span className="flex items-center space-x-1">
            <span className="w-3 h-3 rounded bg-[#00e676]/40 border border-[#00e676]" />
            <span>Strong Bullish</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-3 h-3 rounded bg-[#00b0ff]/30 border border-[#00b0ff]" />
            <span>Neutral/Active</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-3 h-3 rounded bg-[#ff3d57]/40 border border-[#ff3d57]" />
            <span>Bearish Pressure</span>
          </span>
        </div>
      </div>
    </div>
  );
};
