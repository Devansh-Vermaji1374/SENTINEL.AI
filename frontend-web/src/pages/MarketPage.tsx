import React from 'react';
import { 
  Globe2, 
  ArrowUpRight, 
  ArrowDownRight, 
  TrendingUp, 
  ExternalLink,
  Shield,
  Layers
} from 'lucide-react';
import { AssetSignal } from '../types/api';

interface Props {
  exchange: 'HKEX' | 'KRX';
  signals: AssetSignal[];
  onSelectTicker: (ticker: string) => void;
  onNavigatePage: (page: any) => void;
}

export const MarketPage: React.FC<Props> = ({ exchange, signals, onSelectTicker, onNavigatePage }) => {
  const filtered = signals.filter(s => s.exchange === exchange);

  const marketName = exchange === 'HKEX' ? 'Hong Kong Stock Exchange' : 'Korea Exchange';
  const flag = exchange === 'HKEX' ? '🇭🇰' : '🇰🇷';
  const currency = exchange === 'HKEX' ? 'HKD' : 'KRW';

  const avgReturn = filtered.length 
    ? filtered.reduce((acc, s) => acc + s.predicted_return_pct, 0) / filtered.length 
    : 0;

  const totalMentions = filtered.reduce((acc, s) => acc + s.social_mentions + s.news_count, 0);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Exchange Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-[#1b263b] gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <span className="text-2xl">{flag}</span>
            <h1 className="text-xl font-bold tracking-tight text-white">{marketName} ({exchange})</h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#00b0ff]/10 text-[#00b0ff] border border-[#00b0ff]/30">
              {filtered.length} MONITORED EQUITIES
            </span>
          </div>
          <p className="text-xs text-[#94a3b8] mt-1">
            Exchange-specific market microstructure, social sentiment aggregation, and quantitative return predictions.
          </p>
        </div>

        <div className="flex items-center space-x-3 font-mono text-xs">
          <div className="bg-[#0f172a] border border-[#1e293b] rounded px-3 py-2 text-right">
            <div className="text-[10px] uppercase text-[#64748b]">Exchange Avg Forecast</div>
            <div className={`text-base font-bold ${avgReturn >= 0 ? 'text-[#00e676]' : 'text-[#ff3d57]'}`}>
              {avgReturn >= 0 ? '+' : ''}{avgReturn.toFixed(2)}%
            </div>
          </div>
          <div className="bg-[#0f172a] border border-[#1e293b] rounded px-3 py-2 text-right">
            <div className="text-[10px] uppercase text-[#64748b]">Discourse Depth</div>
            <div className="text-base font-bold text-[#00b0ff]">{totalMentions} Items</div>
          </div>
        </div>
      </div>

      {/* Asset Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filtered.map(asset => {
          const isBullish = asset.predicted_return_pct > 0.2;
          const isBearish = asset.predicted_return_pct < -0.2;

          return (
            <div 
              key={asset.ticker}
              className="bg-[#0e1626] border border-[#1c2a40] rounded p-5 hover:border-[#2b4061] transition flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-base font-bold text-white">{asset.ticker}</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#162032] text-[#94a3b8]">
                        {asset.sector}
                      </span>
                    </div>
                    <div className="text-xs text-[#94a3b8] mt-0.5 font-medium">{asset.asset_name}</div>
                  </div>

                  <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-mono font-bold ${
                    asset.direction === 'Bullish'
                      ? 'bg-[#00e676]/10 text-[#00e676] border border-[#00e676]/30'
                      : asset.direction === 'Bearish'
                      ? 'bg-[#ff3d57]/10 text-[#ff3d57] border border-[#ff3d57]/30'
                      : 'bg-[#00b0ff]/10 text-[#00b0ff] border border-[#00b0ff]/30'
                  }`}>
                    {asset.direction}
                  </span>
                </div>

                {/* Price and ML Prediction Section */}
                <div className="mt-4 pt-3 border-t border-[#172236] grid grid-cols-2 gap-2">
                  <div>
                    <span className="text-[10px] uppercase font-mono text-[#64748b]">Latest Close</span>
                    <div className="font-mono text-sm font-bold text-white">
                      {asset.latest_price.toLocaleString()} {asset.currency}
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] uppercase font-mono text-[#64748b]">Predicted Return</span>
                    <div className={`font-mono text-sm font-bold ${
                      isBullish ? 'text-[#00e676]' : isBearish ? 'text-[#ff3d57]' : 'text-[#94a3b8]'
                    }`}>
                      {asset.predicted_return_pct > 0 ? '+' : ''}{asset.predicted_return_pct.toFixed(2)}%
                    </div>
                  </div>
                </div>

                {/* Target Price & FinBERT Indicator */}
                <div className="mt-3 p-2.5 rounded bg-[#121b2d] border border-[#1b283d] space-y-1.5 text-xs font-mono">
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-[#64748b]">Consensus Target:</span>
                    <span className="text-[#00b0ff] font-bold">
                      {asset.predicted_price.toLocaleString()} {asset.currency}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-[#64748b]">FinBERT Score:</span>
                    <span className="text-white font-medium">
                      {asset.sentiment_score > 0 ? '+' : ''}{asset.sentiment_score.toFixed(3)} ({asset.overall_sentiment})
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-[#64748b]">Signal Strength:</span>
                    <span className="text-[#ffd600] font-bold">{asset.signal_strength} / 100</span>
                  </div>
                </div>
              </div>

              {/* Action Footer */}
              <div className="mt-4 pt-3 border-t border-[#172236] flex items-center justify-between">
                <div className="text-[10px] font-mono text-[#64748b]">
                  {asset.social_mentions} Social &middot; {asset.news_count} News
                </div>
                <button
                  onClick={() => {
                    onSelectTicker(asset.ticker);
                    onNavigatePage('asset');
                  }}
                  className="flex items-center space-x-1 text-xs font-mono text-[#00b0ff] hover:text-[#38bdf8] transition"
                >
                  <span>MICRO ANALYSIS</span>
                  <ExternalLink className="w-3 h-3" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
