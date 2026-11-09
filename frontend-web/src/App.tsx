import React, { useState, useEffect } from 'react';
import { TerminalShell, PageId } from './components/TerminalShell';
import { OverviewPage } from './pages/OverviewPage';
import { MarketHeatmapPage } from './pages/MarketHeatmapPage';
import { MarketPage } from './pages/MarketPage';
import { AssetIntelligencePage } from './pages/AssetIntelligencePage';
import { PredictionsPage } from './pages/PredictionsPage';
import { IntelligencePage } from './pages/IntelligencePage';
import { PerformancePage } from './pages/PerformancePage';
import { OperationsPage } from './pages/OperationsPage';
import { api } from './services/api';
import { SystemStatus, Asset, MarketOverview, AssetSignal } from './types/api';

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<PageId>('overview');
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [overview, setOverview] = useState<MarketOverview | null>(null);
  const [signals, setSignals] = useState<AssetSignal[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string>('0700.HK');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const loadData = async () => {
    setIsRefreshing(true);
    try {
      const [sysStatus, assetsList, mktOverview, sigs] = await Promise.all([
        api.getSystemStatus(),
        api.getAssets(),
        api.getMarketOverview(),
        api.getSignals()
      ]);
      setStatus(sysStatus);
      setAssets(assetsList);
      setOverview(mktOverview);
      setSignals(sigs);

      if (assetsList.length > 0 && !selectedTicker) {
        setSelectedTicker(assetsList[0].ticker);
      }
    } catch (err) {
      console.error('Failed to load Sentinel AI telemetry', err);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const currentSignal = signals.find(s => s.ticker === selectedTicker) || null;

  return (
    <TerminalShell
      currentPage={currentPage}
      onPageChange={setCurrentPage}
      status={status}
      assets={assets}
      selectedTicker={selectedTicker}
      onSelectTicker={setSelectedTicker}
      onRefreshData={loadData}
      isRefreshing={isRefreshing}
    >
      {currentPage === 'overview' && (
        <OverviewPage 
          overview={overview} 
          status={status}
          onSelectTicker={setSelectedTicker} 
          onNavigatePage={setCurrentPage} 
        />
      )}
      {currentPage === 'heatmap' && (
        <MarketHeatmapPage 
          signals={signals} 
          onSelectTicker={setSelectedTicker} 
          onNavigatePage={setCurrentPage} 
        />
      )}
      {currentPage === 'hkex' && (
        <MarketPage 
          exchange="HKEX" 
          signals={signals} 
          onSelectTicker={setSelectedTicker} 
          onNavigatePage={setCurrentPage} 
        />
      )}
      {currentPage === 'krx' && (
        <MarketPage 
          exchange="KRX" 
          signals={signals} 
          onSelectTicker={setSelectedTicker} 
          onNavigatePage={setCurrentPage} 
        />
      )}
      {currentPage === 'asset' && (
        <AssetIntelligencePage 
          selectedTicker={selectedTicker} 
          signal={currentSignal} 
        />
      )}
      {currentPage === 'predictions' && (
        <PredictionsPage 
          selectedTicker={selectedTicker} 
          signal={currentSignal} 
        />
      )}
      {currentPage === 'intelligence' && (
        <IntelligencePage 
          selectedTicker={selectedTicker} 
          signal={currentSignal} 
        />
      )}
      {currentPage === 'performance' && (
        <PerformancePage 
          selectedTicker={selectedTicker} 
          signals={signals} 
        />
      )}
      {currentPage === 'operations' && (
        <OperationsPage 
          status={status} 
          onRefreshAll={loadData} 
        />
      )}
    </TerminalShell>
  );
};

export default App;
