import React, { useState, useMemo } from 'react';
import { 
  ResponsiveContainer, 
  ComposedChart, 
  BarChart, 
  Bar, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid, 
  Cell, 
  PieChart, 
  Pie, 
  Legend 
} from 'recharts';
import { 
  ArrowUpRight, 
  ArrowDownRight, 
  TrendingUp, 
  MessageSquare, 
  Newspaper, 
  ShieldCheck, 
  ExternalLink,
  Search,
  Filter,
  ArrowUpDown,
  SlidersHorizontal,
  Clock,
  Sparkles,
  BarChart3
} from 'lucide-react';
import { MarketOverview, AssetSignal } from '../types/api';

interface Props {
  overview: MarketOverview | null;
  status?: any;
  onSelectTicker: (ticker: string) => void;
  onNavigatePage: (page: any) => void;
}

type SortField = 'ticker' | 'asset_name' | 'latest_price' | 'predicted_return_pct' | 'sentiment_score' | 'social_mentions';
type SortOrder = 'asc' | 'desc';

export const OverviewPage: React.FC<Props> = ({ overview, status, onSelectTicker, onNavigatePage }) => {
  const [exchangeFilter, setExchangeFilter] = useState<'ALL' | 'HKEX' | 'KRX'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>('predicted_return_pct');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [chartView, setChartView] = useState<'returns' | 'volume' | 'sentiment'>('returns');

  const rawSignals: AssetSignal[] = overview?.signals || [];

  // Filter & Search
  const filteredSignals = useMemo(() => {
    return rawSignals.filter(s => {
      const matchEx = exchangeFilter === 'ALL' || s.exchange === exchangeFilter;
      const matchSearch = s.ticker.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          s.asset_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          s.sector.toLowerCase().includes(searchQuery.toLowerCase());
      return matchEx && matchSearch;
    });
  }, [rawSignals, exchangeFilter, searchQuery]);

  // Sort
  const sortedSignals = useMemo(() => {
    return [...filteredSignals].sort((a, b) => {
      let vA = a[sortField];
      let vB = b[sortField];
      if (typeof vA === 'string') {
        return sortOrder === 'asc' 
          ? (vA as string).localeCompare(vB as string) 
          : (vB as string).localeCompare(vA as string);
      }
      return sortOrder === 'asc' ? (Number(vA) - Number(vB)) : (Number(vB) - Number(vA));
    });
  }, [filteredSignals, sortField, sortOrder]);

  // Chart Series Data
  const chartData = useMemo(() => {
    return sortedSignals.map(s => ({
      ticker: s.ticker,
      name: s.asset_name,
      exchange: s.exchange,
      predictedReturn: Number(s.predicted_return_pct.toFixed(2)),
      spotPrice: s.latest_price,
      sentimentScore: Number((s.sentiment_score * 100).toFixed(1)),
      mentions: s.social_mentions + s.news_count,
      social: s.social_mentions,
      news: s.news_count
    }));
  }, [sortedSignals]);

  if (!overview) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-[#64748b] font-mono text-xs space-y-3">
        <div className="w-6 h-6 border-2 border-[#00b0ff] border-t-transparent rounded-full animate-spin" />
        <div>Connecting to Sentinel AI Quantitative Engine...</div>
      </div>
    );
  }

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const totalAssets = Number(overview.total_assets ?? rawSignals.length);
  const socialMentions = Number(overview.total_social_mentions ?? 0);
  const newsArticles = Number(overview.total_news_articles ?? 0);
  const totalItems = socialMentions + newsArticles;
  const posPct = Number(overview.overall_positive_pct ?? 0);
  const negPct = Number(overview.overall_negative_pct ?? 0);
  const bullishCount = Number(overview.bullish_assets_count ?? 0);
  const bearishCount = Number(overview.bearish_assets_count ?? 0);
  const neutralCount = Number(overview.neutral_assets_count ?? 0);

  const sentimentPie = [
    { name: 'Bullish Consensus', value: bullishCount, color: '#00e676' },
    { name: 'Bearish Pressure', value: bearishCount, color: '#ff3d57' },
    { name: 'Neutral / Rangebound', value: neutralCount, color: '#00b0ff' },
  ];

  // Session detection
  const now = new Date();
  const utcHours = now.getUTCHours();
  // HKEX: 09:30 - 16:00 HKT (01:30 - 08:00 UTC)
  // KRX: 09:00 - 15:30 KST (00:00 - 06:30 UTC)
  const hkexOpen = utcHours >= 1 && utcHours < 8;
  const krxOpen = utcHours >= 0 && utcHours < 7;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-8">
      {/* 1. INSTITUTIONAL PAGE HEADER */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-[#1b263b] gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <span className="font-mono text-xl font-bold tracking-tight text-white">
              SENTINEL<span className="text-[#00b0ff]">.AI</span>
            </span>
            <span className="text-[#475569] font-mono">|</span>
            <h1 className="text-xl font-bold tracking-tight text-white">
              Executive Market Intelligence
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#00b0ff]/10 text-[#00b0ff] border border-[#00b0ff]/30">
              HISTORICAL INGESTION MODE
            </span>
          </div>
          <div className="flex items-center space-x-3 text-xs text-[#94a3b8] mt-1.5 font-mono">
            <span className="flex items-center space-x-1">
              <Clock className="w-3.5 h-3.5 text-[#64748b]" />
              <span>Snapshot: {now.toUTCString().slice(0, 22)} UTC</span>
            </span>
            <span>&middot;</span>
            <span>
              Latest Ingest: {status?.latest_market_timestamp ? status.latest_market_timestamp.slice(0, 10) : 'Available'}
            </span>
            <span>&middot;</span>
            <span className="text-white">
              🇭🇰 HKEX: <strong className={hkexOpen ? "text-[#00e676]" : "text-[#ffd600]"}>{hkexOpen ? "SESSION OPEN" : "AFTER-HOURS"}</strong>
              &nbsp;|&nbsp;
              🇰🇷 KRX: <strong className={krxOpen ? "text-[#00e676]" : "text-[#ffd600]"}>{krxOpen ? "SESSION OPEN" : "AFTER-HOURS"}</strong>
            </span>
          </div>
        </div>

        {/* Quick Exchange Selector Tabs */}
        <div className="flex items-center space-x-1 bg-[#0e1626] border border-[#1c2a40] p-1 rounded font-mono text-xs">
          {(['ALL', 'HKEX', 'KRX'] as const).map(ex => (
            <button
              key={ex}
              onClick={() => setExchangeFilter(ex)}
              className={`px-3 py-1.5 rounded transition ${
                exchangeFilter === ex 
                  ? 'bg-[#00b0ff]/20 text-[#00b0ff] font-bold border border-[#00b0ff]/40 shadow-[0_0_10px_rgba(0,176,255,0.15)]' 
                  : 'text-[#94a3b8] hover:text-white'
              }`}
            >
              {ex === 'ALL' ? 'Dual Markets (10)' : ex === 'HKEX' ? '🇭🇰 HKEX (5)' : '🇰🇷 KRX (5)'}
            </button>
          ))}
        </div>
      </div>

      {/* 2. EXECUTIVE METRIC CARDS ROW */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#0e1626] border border-[#1c2a40] rounded p-4 relative overflow-hidden shadow-sm">
          <div className="text-[11px] font-mono uppercase text-[#64748b]">Market Bullish Consensus</div>
          <div className="text-2xl font-bold font-mono text-[#00e676] mt-2">
            {posPct.toFixed(1)}%
          </div>
          <div className="text-[11px] text-[#94a3b8] mt-1 flex items-center">
            <ArrowUpRight className="w-3.5 h-3.5 text-[#00e676] mr-1" />
            {bullishCount} of {totalAssets} Equities Projected Positive
          </div>
          <div className="absolute top-0 right-0 h-full w-1 bg-[#00e676]" />
        </div>

        <div className="bg-[#0e1626] border border-[#1c2a40] rounded p-4 relative overflow-hidden shadow-sm">
          <div className="text-[11px] font-mono uppercase text-[#64748b]">Market Bearish Pressure</div>
          <div className="text-2xl font-bold font-mono text-[#ff3d57] mt-2">
            {negPct.toFixed(1)}%
          </div>
          <div className="text-[11px] text-[#94a3b8] mt-1 flex items-center">
            <ArrowDownRight className="w-3.5 h-3.5 text-[#ff3d57] mr-1" />
            {bearishCount} of {totalAssets} Equities Projected Negative
          </div>
          <div className="absolute top-0 right-0 h-full w-1 bg-[#ff3d57]" />
        </div>

        <div className="bg-[#0e1626] border border-[#1c2a40] rounded p-4 relative overflow-hidden shadow-sm">
          <div className="text-[11px] font-mono uppercase text-[#64748b]">Discourse Volume</div>
          <div className="text-2xl font-bold font-mono text-white mt-2">
            {socialMentions} Posts
          </div>
          <div className="text-[11px] text-[#94a3b8] mt-1 flex items-center">
            <MessageSquare className="w-3.5 h-3.5 text-[#00b0ff] mr-1" />
            StockTwits & Financial Discourse
          </div>
          <div className="absolute top-0 right-0 h-full w-1 bg-[#00b0ff]" />
        </div>

        <div className="bg-[#0e1626] border border-[#1c2a40] rounded p-4 relative overflow-hidden shadow-sm">
          <div className="text-[11px] font-mono uppercase text-[#64748b]">Curated News Ingested</div>
          <div className="text-2xl font-bold font-mono text-white mt-2">
            {newsArticles} Articles
          </div>
          <div className="text-[11px] text-[#94a3b8] mt-1 flex items-center">
            <Newspaper className="w-3.5 h-3.5 text-[#ffd600] mr-1" />
            Financial News & Wires
          </div>
          <div className="absolute top-0 right-0 h-full w-1 bg-[#ffd600]" />
        </div>
      </div>

      {/* 3. SECTION A: INTERACTIVE CROSS-MARKET PREDICTIVE RETURN CHART */}
      <div className="bg-[#0e1626] border border-[#1c2a40] rounded p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#1b263b] mb-4 gap-3">
          <div>
            <div className="flex items-center space-x-2">
              <TrendingUp className="w-4 h-4 text-[#00b0ff]" />
              <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
                Cross-Market Quantitative Prediction & Discourse Telemetry
              </h2>
            </div>
            <p className="text-[11px] text-[#64748b] mt-0.5">
              Next-period percentage return forecast vs FinBERT multi-source sentiment & mention density.
            </p>
          </div>

          {/* Metric Selector for Chart */}
          <div className="flex items-center space-x-1 bg-[#121c2d] border border-[#1f2d42] p-1 rounded font-mono text-xs">
            <button
              onClick={() => setChartView('returns')}
              className={`px-2.5 py-1 rounded transition ${
                chartView === 'returns' ? 'bg-[#00b0ff]/20 text-[#00b0ff] font-bold' : 'text-[#64748b] hover:text-white'
              }`}
            >
              Predicted Alpha (%)
            </button>
            <button
              onClick={() => setChartView('volume')}
              className={`px-2.5 py-1 rounded transition ${
                chartView === 'volume' ? 'bg-[#00b0ff]/20 text-[#00b0ff] font-bold' : 'text-[#64748b] hover:text-white'
              }`}
            >
              Discourse vs News
            </button>
            <button
              onClick={() => setChartView('sentiment')}
              className={`px-2.5 py-1 rounded transition ${
                chartView === 'sentiment' ? 'bg-[#00b0ff]/20 text-[#00b0ff] font-bold' : 'text-[#64748b] hover:text-white'
              }`}
            >
              FinBERT Score
            </button>
          </div>
        </div>

        {/* The Responsive Chart */}
        <div className="h-72 w-full">
          {chartData.length === 0 ? (
            <div className="flex items-center justify-center h-full text-xs font-mono text-[#64748b]">
              No asset records match the current filter criteria.
            </div>
          ) : chartView === 'returns' ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                <CartesianGrid stroke="#162235" strokeDasharray="3 3" vertical={false} />
                <XAxis 
                  dataKey="ticker" 
                  stroke="#64748b" 
                  fontSize={10} 
                  fontFamily="monospace"
                  tickLine={false}
                />
                <YAxis 
                  stroke="#64748b" 
                  fontSize={10} 
                  fontFamily="monospace"
                  tickLine={false}
                  unit="%"
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0e1626', borderColor: '#1c2a40', color: '#fff', fontSize: '12px', fontFamily: 'monospace' }}
                  formatter={(val: any) => [`${val}%`, 'Next-Period Forecast']}
                  labelFormatter={(lbl) => {
                    const match = chartData.find(d => d.ticker === lbl);
                    return match ? `${lbl} - ${match.name} (${match.exchange})` : lbl;
                  }}
                />
                <Bar dataKey="predictedReturn" radius={[3, 3, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={entry.predictedReturn >= 0 ? '#00e676' : '#ff3d57'} 
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : chartView === 'volume' ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                <CartesianGrid stroke="#162235" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="ticker" stroke="#64748b" fontSize={10} fontFamily="monospace" tickLine={false} />
                <YAxis stroke="#64748b" fontSize={10} fontFamily="monospace" tickLine={false} />
                <Tooltip contentStyle={{ backgroundColor: '#0e1626', borderColor: '#1c2a40', color: '#fff', fontSize: '12px', fontFamily: 'monospace' }} />
                <Legend wrapperStyle={{ fontSize: '11px', fontFamily: 'monospace' }} />
                <Bar dataKey="social" name="Social Posts" fill="#00b0ff" radius={[2, 2, 0, 0]} />
                <Bar dataKey="news" name="Curated Articles" fill="#ffd600" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                <CartesianGrid stroke="#162235" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="ticker" stroke="#64748b" fontSize={10} fontFamily="monospace" tickLine={false} />
                <YAxis stroke="#64748b" fontSize={10} fontFamily="monospace" tickLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0e1626', borderColor: '#1c2a40', color: '#fff', fontSize: '12px', fontFamily: 'monospace' }}
                  formatter={(val: any) => [val, 'FinBERT Index (Normalized)']}
                />
                <Bar dataKey="sentimentScore" radius={[2, 2, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={entry.sentimentScore >= 0 ? '#00e676' : '#ff3d57'} 
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* 4. SECTION B & C: ASSET TABLE & MACRO SENTIMENT BREAKDOWN */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* SECTION B: COMPLETE ASSET INTELLIGENCE RANKING TABLE */}
        <div className="lg:col-span-2 bg-[#0e1626] border border-[#1c2a40] rounded p-5 flex flex-col justify-between">
          <div>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#1b263b] mb-3 gap-3">
              <div>
                <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
                  Asset Intelligence & Model Forecast Matrix
                </h2>
                <p className="text-[11px] text-[#64748b]">
                  Showing {sortedSignals.length} of {rawSignals.length} tracked equities across HKEX & KRX.
                </p>
              </div>

              {/* In-Table Search Input */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-[#64748b] absolute left-2.5 top-2.5" />
                <input
                  type="text"
                  placeholder="Filter table..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-[#121c2d] border border-[#202f47] rounded pl-8 pr-3 py-1.5 text-xs text-white placeholder-[#475569] font-mono focus:outline-none focus:border-[#00b0ff] w-48"
                />
              </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left font-mono text-xs">
                <thead>
                  <tr className="border-b border-[#1b263b] text-[#64748b] text-[10px] uppercase select-none">
                    <th 
                      onClick={() => handleSort('ticker')} 
                      className="py-2.5 px-3 cursor-pointer hover:text-white"
                    >
                      <div className="flex items-center space-x-1">
                        <span>Ticker</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th 
                      onClick={() => handleSort('asset_name')} 
                      className="py-2.5 px-3 cursor-pointer hover:text-white"
                    >
                      <div className="flex items-center space-x-1">
                        <span>Company</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th className="py-2.5 px-3">Market</th>
                    <th 
                      onClick={() => handleSort('latest_price')} 
                      className="py-2.5 px-3 text-right cursor-pointer hover:text-white"
                    >
                      <div className="flex items-center justify-end space-x-1">
                        <span>Latest Price</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th 
                      onClick={() => handleSort('predicted_return_pct')} 
                      className="py-2.5 px-3 text-right cursor-pointer hover:text-white"
                    >
                      <div className="flex items-center justify-end space-x-1">
                        <span>Pred Return</span>
                        <ArrowUpDown className="w-3 h-3" />
                      </div>
                    </th>
                    <th className="py-2.5 px-3 text-center">Consensus</th>
                    <th className="py-2.5 px-3 text-center">FinBERT</th>
                    <th className="py-2.5 px-3 text-right">Inspect</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#172236]">
                  {sortedSignals.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="py-8 text-center text-[#64748b] text-xs">
                        No asset records match the specified query.
                      </td>
                    </tr>
                  ) : (
                    sortedSignals.map(sig => {
                      const isBullish = sig.predicted_return_pct > 0.2;
                      const isBearish = sig.predicted_return_pct < -0.2;
                      return (
                        <tr 
                          key={sig.ticker}
                          onClick={() => {
                            onSelectTicker(sig.ticker);
                            onNavigatePage('asset');
                          }}
                          className="hover:bg-[#131f33] transition cursor-pointer group"
                        >
                          <td className="py-2.5 px-3 font-bold text-white group-hover:text-[#00b0ff]">
                            {sig.ticker}
                          </td>
                          <td className="py-2.5 px-3 text-[#cbd5e1] truncate max-w-[120px]">
                            {sig.asset_name}
                          </td>
                          <td className="py-2.5 px-3">
                            <span className="px-1.5 py-0.5 rounded text-[10px] bg-[#141e30] border border-[#202f4a] text-[#94a3b8]">
                              {sig.exchange}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-right text-white font-medium">
                            {sig.latest_price.toLocaleString()} {sig.currency}
                          </td>
                          <td className={`py-2.5 px-3 text-right font-bold ${
                            isBullish ? 'text-[#00e676]' : isBearish ? 'text-[#ff3d57]' : 'text-[#94a3b8]'
                          }`}>
                            {sig.predicted_return_pct > 0 ? '+' : ''}{sig.predicted_return_pct.toFixed(2)}%
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            <span className={`inline-block px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                              sig.direction === 'Bullish'
                                ? 'bg-[#00e676]/10 text-[#00e676] border border-[#00e676]/30'
                                : sig.direction === 'Bearish'
                                ? 'bg-[#ff3d57]/10 text-[#ff3d57] border border-[#ff3d57]/30'
                                : 'bg-[#00b0ff]/10 text-[#00b0ff] border border-[#00b0ff]/30'
                            }`}>
                              {sig.direction}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-center text-[#94a3b8] text-[11px]">
                            {sig.overall_sentiment}
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            <button 
                              className="p-1 rounded bg-[#162235] hover:bg-[#1f314d] text-[#00b0ff] transition"
                              title="Inspect Deep Dive"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* SECTION C: SENTIMENT DISTRIBUTION PIE & MOST DISCUSSED HOTSPOTS */}
        <div className="space-y-6">
          {/* Sentiment Distribution Card */}
          <div className="bg-[#0e1626] border border-[#1c2a40] rounded p-5">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono mb-2">
              Cross-Exchange Sentiment Profile
            </h3>
            <p className="text-[11px] text-[#64748b] mb-2 font-mono">
              Consensus distribution aggregated across all 10 assets.
            </p>

            <div className="h-44 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={sentimentPie}
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={65}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {sentimentPie.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0e1626', borderColor: '#1c2a40', color: '#fff', fontSize: '12px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="flex justify-around text-center text-xs font-mono pt-3 border-t border-[#1b263b]">
              <div>
                <span className="block text-[10px] text-[#64748b]">BULLISH</span>
                <span className="font-bold text-[#00e676]">{bullishCount} Assets</span>
              </div>
              <div>
                <span className="block text-[10px] text-[#64748b]">RANGEBOUND</span>
                <span className="font-bold text-[#00b0ff]">{neutralCount} Assets</span>
              </div>
              <div>
                <span className="block text-[10px] text-[#64748b]">BEARISH</span>
                <span className="font-bold text-[#ff3d57]">{bearishCount} Assets</span>
              </div>
            </div>
          </div>

          {/* Most Discussed Assets Card */}
          <div className="bg-[#0e1626] border border-[#1c2a40] rounded p-5 font-mono">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">
              Discourse Volume Leaders
            </h3>
            <p className="text-[11px] text-[#64748b] mb-3">
              Combined StockTwits & news article density.
            </p>

            <div className="space-y-2">
              {(overview.most_discussed || []).slice(0, 5).map(item => (
                <div
                  key={item.ticker}
                  onClick={() => {
                    onSelectTicker(item.ticker);
                    onNavigatePage('asset');
                  }}
                  className="flex items-center justify-between p-2.5 rounded bg-[#121c2d] hover:bg-[#18263d] cursor-pointer border border-[#1f2d42] transition"
                >
                  <div>
                    <span className="font-bold text-white text-xs mr-2">{item.ticker}</span>
                    <span className="text-[11px] text-[#94a3b8]">{item.asset_name}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-bold text-[#00b0ff]">
                      {item.social_mentions + item.news_count} Hits
                    </span>
                    <div className="text-[9px] text-[#64748b]">
                      {item.social_mentions}s / {item.news_count}n
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
