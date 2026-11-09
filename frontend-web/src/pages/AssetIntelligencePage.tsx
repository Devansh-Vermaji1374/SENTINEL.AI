import React, { useEffect, useState } from 'react';
import { 
  LineChart, 
  TrendingUp, 
  ShieldCheck, 
  Layers, 
  Sliders, 
  ExternalLink,
  Target,
  Activity,
  FileText,
  BarChart2,
  AlertTriangle,
  Info
} from 'lucide-react';
import { api } from '../services/api';
import { AssetSignal, MarketDataPoint, SentimentAnalysis, PredictionRecord } from '../types/api';
import { CandlestickChart } from '../components/CandlestickChart';
import { calculateRSI } from '../utils/indicators';

interface Props {
  selectedTicker: string;
  signal: AssetSignal | null;
}

export const AssetIntelligencePage: React.FC<Props> = ({ selectedTicker, signal }) => {
  const [history, setHistory] = useState<MarketDataPoint[]>([]);
  const [sentiment, setSentiment] = useState<SentimentAnalysis | null>(null);
  const [predictions, setPredictions] = useState<PredictionRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    Promise.all([
      api.getMarketData(selectedTicker, 120),
      api.getSentiment(selectedTicker),
      api.getPredictions(selectedTicker)
    ]).then(([histData, sentData, predData]) => {
      if (mounted) {
        setHistory(histData);
        setSentiment(sentData);
        setPredictions(predData);
        setLoading(false);
      }
    }).catch(() => {
      if (mounted) setLoading(false);
    });

    return () => { mounted = false; };
  }, [selectedTicker]);

  if (!signal) {
    return (
      <div className="flex items-center justify-center h-96 text-[#64748b] font-mono text-xs">
        Select an asset to view micro-intelligence.
      </div>
    );
  }

  const support = Number(signal.support_levels?.[0] ?? (signal.latest_price ? signal.latest_price * 0.95 : 100));
  const resistance = Number(signal.resistance_levels?.[0] ?? (signal.latest_price ? signal.latest_price * 1.05 : 110));
  const latestPrice = Number(signal.latest_price ?? 0);
  const predPrice = Number(signal.predicted_price ?? latestPrice);
  const predReturn = Number(signal.predicted_return_pct ?? 0);
  const sentScore = Number(signal.sentiment_score ?? 0);
  const newsSent = Number(signal.news_sentiment ?? 0);
  const socialSent = Number(signal.social_sentiment ?? 0);
  const sigStrength = Number(signal.signal_strength ?? 50);

  // Quantitative Stats Calculations from actual history
  const closes = history.map(h => h.close);
  const returns = closes.slice(1).map((c, i) => (c - closes[i]) / closes[i]);
  const avgReturn = returns.length ? returns.reduce((a, b) => a + b, 0) / returns.length : 0;
  const variance = returns.length ? returns.reduce((a, b) => a + Math.pow(b - avgReturn, 2), 0) / returns.length : 0;
  const dailyVolatility = Math.sqrt(variance) * 100;
  const annualizedVolatility = dailyVolatility * Math.sqrt(252);

  // Maximum Drawdown from history
  let maxDD = 0;
  let peak = -Infinity;
  for (const c of closes) {
    if (c > peak) peak = c;
    const dd = (peak - c) / peak;
    if (dd > maxDD) maxDD = dd;
  }

  // Calculate current RSI(14)
  const rsiSeries = calculateRSI(history, 14);
  const latestRSI = rsiSeries.length ? rsiSeries[rsiSeries.length - 1].value : 50;

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-mono">
      {/* Asset Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-[#1b263b] gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <span className="text-2xl font-bold text-white">{signal.ticker}</span>
            <span className="text-base text-[#94a3b8]">&middot; {signal.asset_name}</span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-[#162032] border border-[#23334d] text-[#94a3b8]">
              {signal.exchange} &middot; {signal.sector}
            </span>
          </div>
          <p className="text-xs text-[#94a3b8] mt-1">
            Complete institutional profile &middot; Interactive Lightweight Charts OHLCV &middot; Technical Overlays &middot; Microstructure Risk.
          </p>
        </div>

        <div className="flex items-center space-x-4">
          <div className="bg-[#0f172a] border border-[#1e293b] rounded px-4 py-2 text-right">
            <div className="text-[10px] uppercase text-[#64748b]">Spot Closing Price</div>
            <div className="text-xl font-bold text-white">
              {latestPrice.toLocaleString()} {signal.currency}
            </div>
          </div>
          <div className="bg-[#0f172a] border border-[#1e293b] rounded px-4 py-2 text-right">
            <div className="text-[10px] uppercase text-[#64748b]">Consensus Alpha</div>
            <div className={`text-xl font-bold ${
              predReturn >= 0 ? 'text-[#00e676]' : 'text-[#ff3d57]'
            }`}>
              {predReturn >= 0 ? '+' : ''}{predReturn.toFixed(2)}%
            </div>
          </div>
        </div>
      </div>

      {/* PHASE 1 & 5: REAL INTERACTIVE CANDLESTICK CHART */}
      <CandlestickChart 
        data={history} 
        ticker={signal.ticker} 
        currency={signal.currency} 
      />

      {/* PHASE 5: STRUCTURED INTELLIGENCE EXECUTIVE SUMMARY */}
      <div className="bg-[#0e1626] border border-[#1c2a40] rounded p-5 space-y-4">
        <div className="flex items-center space-x-2 pb-2 border-b border-[#1b263b]">
          <FileText className="w-4 h-4 text-[#00b0ff]" />
          <h2 className="text-sm font-bold text-white uppercase tracking-wider">
            Quantitative Intelligence Executive Summary
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
          <div className="p-3 bg-[#111928] border border-[#1b273b] rounded">
            <div className="text-[10px] text-[#00b0ff] uppercase font-bold mb-1">Price Microstructure</div>
            <p className="text-[#94a3b8] leading-relaxed text-[11px]">
              Asset is trading at <strong>{latestPrice.toFixed(2)} {signal.currency}</strong> with dynamic support identified at <strong>{support.toFixed(2)}</strong> and overhead resistance at <strong>{resistance.toFixed(2)}</strong>.
            </p>
          </div>

          <div className="p-3 bg-[#111928] border border-[#1b273b] rounded">
            <div className="text-[10px] text-[#00e676] uppercase font-bold mb-1">Model Consensus</div>
            <p className="text-[#94a3b8] leading-relaxed text-[11px]">
              Consensus projection indicates a <strong>{predReturn >= 0 ? '+' : ''}{predReturn.toFixed(2)}%</strong> return target ({predPrice.toFixed(2)} {signal.currency}) across 4 walk-forward validated algorithms.
            </p>
          </div>

          <div className="p-3 bg-[#111928] border border-[#1b273b] rounded">
            <div className="text-[10px] text-[#ffd600] uppercase font-bold mb-1">FinBERT Sentiment</div>
            <p className="text-[#94a3b8] leading-relaxed text-[11px]">
              Discourse score sits at <strong>{sentScore > 0 ? '+' : ''}{sentScore.toFixed(3)} ({signal.overall_sentiment})</strong> derived from {signal.social_mentions} social posts and {signal.news_count} verified news articles.
            </p>
          </div>

          <div className="p-3 bg-[#111928] border border-[#1b273b] rounded">
            <div className="text-[10px] text-[#ff3d57] uppercase font-bold mb-1">Risk Profile</div>
            <p className="text-[#94a3b8] leading-relaxed text-[11px]">
              Annualized historical volatility is <strong>{annualizedVolatility.toFixed(1)}%</strong> with a maximum historical drawdown of <strong>{(maxDD * 100).toFixed(1)}%</strong> across the monitored window.
            </p>
          </div>
        </div>
      </div>

      {/* PHASE 6: QUANTITATIVE RISK & RETURN METRICS MATRIX */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-xs">
        {/* Volatility & Momentum */}
        <div className="bg-[#0e1626] border border-[#1c2a40] rounded p-4 space-y-3">
          <div className="text-[10px] uppercase text-[#64748b] tracking-wider">Volatility & Momentum Risk</div>
          <div className="space-y-2">
            <div className="flex justify-between items-center py-1.5 border-b border-[#1b263b]">
              <span className="text-[#94a3b8]">Daily Volatility:</span>
              <span className="text-white font-bold">{dailyVolatility.toFixed(2)}%</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-[#1b263b]">
              <span className="text-[#94a3b8]">Annualized Volatility:</span>
              <span className="text-white font-bold">{annualizedVolatility.toFixed(2)}%</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-[#1b263b]">
              <span className="text-[#94a3b8]">RSI (14-period):</span>
              <span className={`font-bold ${latestRSI >= 70 ? 'text-[#ff3d57]' : latestRSI <= 30 ? 'text-[#00e676]' : 'text-[#00b0ff]'}`}>
                {latestRSI.toFixed(1)} ({latestRSI >= 70 ? 'Overbought' : latestRSI <= 30 ? 'Oversold' : 'Neutral'})
              </span>
            </div>
            <div className="flex justify-between items-center py-1.5">
              <span className="text-[#94a3b8]">Max Drawdown:</span>
              <span className="text-[#ff3d57] font-bold">{(maxDD * 100).toFixed(2)}%</span>
            </div>
          </div>
        </div>

        {/* Support & Resistance Floor / Ceilings */}
        <div className="bg-[#0e1626] border border-[#1c2a40] rounded p-4 space-y-3">
          <div className="text-[10px] uppercase text-[#64748b] tracking-wider">Dynamic Microstructure Levels</div>
          <div className="space-y-2.5">
            <div className="p-2.5 bg-[#111928] border border-[#1c2b42] rounded">
              <div className="text-[10px] text-[#00e676] font-bold uppercase">Primary Support Floor</div>
              <div className="text-base font-bold text-white mt-0.5">
                {support.toFixed(2)} {signal.currency}
              </div>
            </div>
            <div className="p-2.5 bg-[#111928] border border-[#1c2b42] rounded">
              <div className="text-[10px] text-[#ff3d57] font-bold uppercase">Overhead Resistance Ceiling</div>
              <div className="text-base font-bold text-white mt-0.5">
                {resistance.toFixed(2)} {signal.currency}
              </div>
            </div>
          </div>
        </div>

        {/* Prediction Consensus Breakdown */}
        <div className="bg-[#0e1626] border border-[#1c2a40] rounded p-4 space-y-3">
          <div className="text-[10px] uppercase text-[#64748b] tracking-wider">4-Model Consensus Distribution</div>
          <div className="space-y-2">
            {predictions.map(p => (
              <div key={p.model_name} className="flex justify-between items-center py-1 border-b border-[#1b263b] text-[11px]">
                <span className="text-[#94a3b8] capitalize">{p.model_name.replace(/_/g, ' ')}:</span>
                <span className={`font-bold ${p.predicted_return_pct >= 0 ? 'text-[#00e676]' : 'text-[#ff3d57]'}`}>
                  {p.predicted_return_pct >= 0 ? '+' : ''}{p.predicted_return_pct.toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
