import React from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  Globe2, 
  Cpu, 
  FileText, 
  LineChart, 
  Activity, 
  Database,
  ChevronLeft,
  ChevronRight,
  Shield,
  Search,
  RefreshCw,
  SlidersHorizontal,
  LayoutGrid
} from 'lucide-react';
import { SystemStatus, Asset } from '../types/api';

export type PageId = 
  | 'overview' 
  | 'heatmap'
  | 'hkex' 
  | 'krx' 
  | 'asset' 
  | 'predictions' 
  | 'intelligence' 
  | 'performance' 
  | 'operations';

interface ShellProps {
  currentPage: PageId;
  onPageChange: (page: PageId) => void;
  status: SystemStatus | null;
  assets: Asset[];
  selectedTicker: string;
  onSelectTicker: (ticker: string) => void;
  onRefreshData: () => void;
  isRefreshing: boolean;
  children: React.ReactNode;
}

export const TerminalShell: React.FC<ShellProps> = ({
  currentPage,
  onPageChange,
  status,
  assets,
  selectedTicker,
  onSelectTicker,
  onRefreshData,
  isRefreshing,
  children
}) => {
  const [collapsed, setCollapsed] = React.useState(false);
  const [searchQuery, setSearchQuery] = React.useState('');
  const [searchOpen, setSearchOpen] = React.useState(false);

  const navItems: { id: PageId; label: string; icon: React.ReactNode; badge?: string }[] = [
    { id: 'overview', label: 'Executive Overview', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'heatmap', label: 'Market Treemap Heatmap', icon: <LayoutGrid className="w-4 h-4" />, badge: 'Dual-Ex' },
    { id: 'hkex', label: 'Hong Kong Market', icon: <Globe2 className="w-4 h-4" />, badge: '5 HK' },
    { id: 'krx', label: 'South Korea Market', icon: <TrendingUp className="w-4 h-4" />, badge: '5 KR' },
    { id: 'asset', label: 'Asset Micro-Intelligence', icon: <LineChart className="w-4 h-4" /> },
    { id: 'predictions', label: 'AI Multi-Model Forecast', icon: <Cpu className="w-4 h-4" />, badge: '4 Models' },
    { id: 'intelligence', label: 'Discourse & News Stream', icon: <FileText className="w-4 h-4" /> },
    { id: 'performance', label: 'Walk-Forward Validation', icon: <Activity className="w-4 h-4" /> },
    { id: 'operations', label: 'Data Ingestion & Ops', icon: <Database className="w-4 h-4" /> },
  ];

  const filteredAssets = assets.filter(a => 
    a.ticker.toLowerCase().includes(searchQuery.toLowerCase()) || 
    a.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#070a11] text-[#f3f4f6]">
      {/* Collapsible Sidebar */}
      <aside 
        className={`flex flex-col border-r border-[#1a2538] bg-[#0b101a] transition-all duration-300 z-30 select-none ${
          collapsed ? 'w-16' : 'w-64'
        }`}
      >
        {/* Terminal Logo Header */}
        <div className="h-14 flex items-center justify-between px-3 border-b border-[#1a2538]">
          {!collapsed && (
            <div className="flex items-center space-x-2.5 overflow-hidden">
              <div className="p-1.5 bg-[#00b0ff]/10 border border-[#00b0ff]/30 rounded text-[#00b0ff]">
                <Shield className="w-4 h-4" />
              </div>
              <div>
                <span className="font-mono text-sm font-bold tracking-wider text-white">
                  SENTINEL<span className="text-[#00b0ff]">.AI</span>
                </span>
                <span className="block text-[9px] uppercase tracking-widest text-[#64748b] font-mono">
                  QUANT TERMINAL v2.5
                </span>
              </div>
            </div>
          )}
          {collapsed && (
            <div className="mx-auto p-1.5 bg-[#00b0ff]/10 border border-[#00b0ff]/30 rounded text-[#00b0ff]">
              <Shield className="w-4 h-4" />
            </div>
          )}
          <button 
            onClick={() => setCollapsed(!collapsed)}
            className="p-1 text-[#64748b] hover:text-white hover:bg-[#131c2e] rounded transition"
            title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Navigation Items */}
        <div className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
          {navItems.map((item) => {
            const isActive = currentPage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onPageChange(item.id)}
                className={`w-full flex items-center justify-between px-2.5 py-2 rounded text-xs transition group ${
                  isActive 
                    ? 'bg-[#00b0ff]/15 text-[#00b0ff] font-medium border border-[#00b0ff]/30 shadow-[0_0_12px_rgba(0,176,255,0.15)]' 
                    : 'text-[#94a3b8] hover:bg-[#121927] hover:text-white'
                }`}
                title={collapsed ? item.label : undefined}
              >
                <div className="flex items-center space-x-2.5 min-w-0">
                  <span className={isActive ? 'text-[#00b0ff]' : 'text-[#64748b] group-hover:text-white'}>
                    {item.icon}
                  </span>
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </div>
                {!collapsed && item.badge && (
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#162032] border border-[#23334d] text-[#64748b]">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Active Asset Selector in Sidebar */}
        {!collapsed && (
          <div className="p-3 border-t border-[#1a2538] bg-[#080d15]">
            <div className="text-[10px] uppercase font-mono tracking-wider text-[#64748b] mb-1.5 flex items-center justify-between">
              <span>Active Target</span>
              <SlidersHorizontal className="w-3 h-3 text-[#64748b]" />
            </div>
            <select
              value={selectedTicker}
              onChange={(e) => onSelectTicker(e.target.value)}
              className="w-full bg-[#111724] border border-[#223048] rounded px-2.5 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-[#00b0ff]"
            >
              {assets.map((a) => (
                <option key={a.ticker} value={a.ticker}>
                  {a.ticker} - {a.name} ({a.exchange})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Pipeline Telemetry Footer */}
        <div className="p-2.5 border-t border-[#1a2538] bg-[#06080d] text-[10px] font-mono">
          {!collapsed ? (
            <div className="space-y-1 text-[#64748b]">
              <div className="flex items-center justify-between">
                <span>APIFY SCRAPER:</span>
                <span className={status?.apify_connected ? "text-[#00e676]" : "text-[#94a3b8]"}>
                  {status?.apify_status || (status?.apify_connected ? "CONFIGURED" : "NOT CONFIGURED")}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>EXA API:</span>
                <span className={status?.exa_connected ? "text-[#00e676]" : "text-[#94a3b8]"}>
                  {status?.exa_status || (status?.exa_connected ? "CONFIGURED" : "NOT CONFIGURED")}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>FinBERT NLP:</span>
                <span className={status?.finbert_ready ? "text-[#00e676]" : "text-[#ffd600]"}>
                  {status?.finbert_status || "INITIALIZING"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>MODEL REGISTRY:</span>
                <span className={status?.model_registry_ready ? "text-[#00e676]" : "text-[#ffd600]"}>
                  {status?.model_registry_status || "INITIALIZING"}
                </span>
              </div>
            </div>
          ) : (
            <div className="flex justify-center">
              <div className="w-2 h-2 rounded-full bg-[#00e676] animate-pulse" title="System Operational" />
            </div>
          )}
        </div>
      </aside>

      {/* Main Terminal Body */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Financial Header Bar */}
        <header className="h-14 border-b border-[#1a2538] bg-[#0a0f1a] px-4 flex items-center justify-between z-20">
          <div className="flex items-center space-x-4">
            {/* Asset Fast Search */}
            <div className="relative">
              <div className="flex items-center bg-[#101726] border border-[#1f2d42] rounded px-2.5 py-1.5 w-64 text-xs focus-within:border-[#00b0ff] transition">
                <Search className="w-3.5 h-3.5 text-[#64748b] mr-2 shrink-0" />
                <input
                  type="text"
                  placeholder="Quick Search Equities..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setSearchOpen(true);
                  }}
                  onFocus={() => setSearchOpen(true)}
                  className="bg-transparent border-none text-white focus:outline-none w-full font-mono placeholder-[#475569] text-xs"
                />
              </div>

              {/* Autocomplete Search Dropdown */}
              {searchOpen && searchQuery && (
                <div 
                  className="absolute top-full left-0 mt-1 w-80 bg-[#0e1625] border border-[#22334e] rounded shadow-xl py-1 z-50 max-h-60 overflow-y-auto"
                >
                  <div className="text-[10px] uppercase font-mono text-[#64748b] px-3 py-1 border-b border-[#1a2538]">
                    Matching Financial Assets
                  </div>
                  {filteredAssets.length === 0 ? (
                    <div className="px-3 py-2 text-xs text-[#64748b]">No assets found</div>
                  ) : (
                    filteredAssets.map(a => (
                      <button
                        key={a.ticker}
                        onClick={() => {
                          onSelectTicker(a.ticker);
                          onPageChange('asset');
                          setSearchOpen(false);
                          setSearchQuery('');
                        }}
                        className="w-full text-left px-3 py-2 text-xs hover:bg-[#162338] flex items-center justify-between group"
                      >
                        <div>
                          <span className="font-mono font-bold text-white group-hover:text-[#00b0ff] mr-2">
                            {a.ticker}
                          </span>
                          <span className="text-[#94a3b8]">{a.name}</span>
                        </div>
                        <span className="text-[10px] font-mono px-1 bg-[#192438] text-[#64748b] rounded">
                          {a.exchange}
                        </span>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* Market Ticker Chips */}
            <div className="hidden lg:flex items-center space-x-2 text-[11px] font-mono">
              <span className="text-[#64748b]">MARKETS:</span>
              <span className="px-2 py-0.5 rounded bg-[#101928] border border-[#1f2d42] text-[#94a3b8]">
                🇭🇰 HKEX: <strong className="text-white">5 Monitored</strong>
              </span>
              <span className="px-2 py-0.5 rounded bg-[#101928] border border-[#1f2d42] text-[#94a3b8]">
                🇰🇷 KRX: <strong className="text-white">5 Monitored</strong>
              </span>
            </div>
          </div>

          {/* Action Center & Status */}
          <div className="flex items-center space-x-3">
            <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded bg-[#0d1522] border border-[#1d2b3f] text-[11px] font-mono">
              <span className={`w-2 h-2 rounded-full ${status?.status === 'healthy' ? 'bg-[#00e676]' : 'bg-[#ffd600]'}`} />
              <span className="text-[#94a3b8]">DATA FEED:</span>
              <span className="text-white font-semibold">HISTORICAL INGESTION ({status?.historical_bars_count || 1245} BARS)</span>
            </div>

            <button
              onClick={onRefreshData}
              disabled={isRefreshing}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-[#141d2e] hover:bg-[#1b263b] border border-[#22334e] text-xs font-mono text-[#00b0ff] transition disabled:opacity-50"
              title="Refresh Terminal Telemetry"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span className="hidden md:inline">REFRESH</span>
            </button>
          </div>
        </header>

        {/* Viewport Content */}
        <main className="flex-1 overflow-y-auto p-5 bg-[#070a11]">
          {children}
        </main>
      </div>
    </div>
  );
};
