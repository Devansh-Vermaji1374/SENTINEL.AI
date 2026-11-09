import React, { useEffect, useRef, useState, useMemo } from 'react';
import { 
  createChart, 
  IChartApi, 
  CandlestickSeries, 
  HistogramSeries, 
  LineSeries, 
  CandlestickData, 
  HistogramData, 
  Time 
} from 'lightweight-charts';
import { OHLCVBar, calculateSMA, calculateEMA, calculateRSI, calculateBollingerBands } from '../utils/indicators';
import { Sliders, HelpCircle, Layers, Eye, EyeOff } from 'lucide-react';

interface Props {
  data: OHLCVBar[];
  ticker: string;
  currency: string;
}

type Timeframe = '1D' | '5D' | '1M' | '3M' | '6M' | '1Y' | 'ALL';

export const CandlestickChart: React.FC<Props> = ({ data, ticker, currency }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<IChartApi | null>(null);

  const [timeframe, setTimeframe] = useState<Timeframe>('ALL');
  const [showSMA20, setShowSMA20] = useState(true);
  const [showSMA50, setShowSMA50] = useState(false);
  const [showEMA20, setShowEMA20] = useState(false);
  const [showBollinger, setShowBollinger] = useState(false);
  const [showRSI, setShowRSI] = useState(false);
  const [showGuide, setShowGuide] = useState(false);

  // Filter data by timeframe
  const filteredData = useMemo(() => {
    if (!data || data.length === 0) return [];
    // Ensure chronological ascending order
    const sorted = [...data].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
    if (timeframe === 'ALL') return sorted;
    if (timeframe === '1D') return sorted.slice(-1);
    if (timeframe === '5D') return sorted.slice(-5);
    if (timeframe === '1M') return sorted.slice(-22);
    if (timeframe === '3M') return sorted.slice(-66);
    if (timeframe === '6M') return sorted.slice(-132);
    if (timeframe === '1Y') return sorted.slice(-252);
    return sorted;
  }, [data, timeframe]);

  useEffect(() => {
    if (!chartContainerRef.current || filteredData.length === 0) return;

    chartContainerRef.current.innerHTML = '';

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 440,
      layout: {
        background: { color: '#090d16' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: '#141d2e' },
        horzLines: { color: '#141d2e' },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          color: '#00b0ff',
          width: 1,
          style: 2,
        },
        horzLine: {
          color: '#00b0ff',
          width: 1,
          style: 2,
        },
      },
      rightPriceScale: {
        borderColor: '#1e293b',
        scaleMargins: {
          top: 0.1,
          bottom: 0.25,
        },
      },
      timeScale: {
        borderColor: '#1e293b',
        timeVisible: true,
      },
    });

    chartInstance.current = chart;

    // 1. Candlestick series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#00e676',
      downColor: '#ff3d57',
      borderVisible: false,
      wickUpColor: '#00e676',
      wickDownColor: '#ff3d57',
    });

    const candleData: CandlestickData[] = filteredData.map(d => ({
      time: d.date.split('T')[0] as Time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));
    candleSeries.setData(candleData);

    // 2. Volume series
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '', // overlay
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });

    const volumeData: HistogramData[] = filteredData.map(d => ({
      time: d.date.split('T')[0] as Time,
      value: d.volume,
      color: d.close >= d.open ? 'rgba(0, 230, 118, 0.25)' : 'rgba(255, 61, 87, 0.25)',
    }));
    volumeSeries.setData(volumeData);

    // 3. Technical Indicator Overlays
    if (showSMA20) {
      const sma20 = calculateSMA(filteredData, 20);
      const smaSeries = chart.addSeries(LineSeries, {
        color: '#00b0ff',
        lineWidth: 2,
        title: 'SMA 20',
      });
      smaSeries.setData(sma20.map(p => ({ time: p.time as Time, value: p.value })));
    }

    if (showSMA50) {
      const sma50 = calculateSMA(filteredData, 50);
      const smaSeries = chart.addSeries(LineSeries, {
        color: '#ffd600',
        lineWidth: 2,
        title: 'SMA 50',
      });
      smaSeries.setData(sma50.map(p => ({ time: p.time as Time, value: p.value })));
    }

    if (showEMA20) {
      const ema20 = calculateEMA(filteredData, 20);
      const emaSeries = chart.addSeries(LineSeries, {
        color: '#a855f7',
        lineWidth: 2,
        title: 'EMA 20',
      });
      emaSeries.setData(ema20.map(p => ({ time: p.time as Time, value: p.value })));
    }

    if (showBollinger) {
      const bb = calculateBollingerBands(filteredData, 20, 2);
      const upperSeries = chart.addSeries(LineSeries, { color: 'rgba(56, 189, 248, 0.4)', lineWidth: 1, lineStyle: 2 });
      const lowerSeries = chart.addSeries(LineSeries, { color: 'rgba(56, 189, 248, 0.4)', lineWidth: 1, lineStyle: 2 });
      upperSeries.setData(bb.map(p => ({ time: p.time as Time, value: p.upper })));
      lowerSeries.setData(bb.map(p => ({ time: p.time as Time, value: p.lower })));
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [filteredData, showSMA20, showSMA50, showEMA20, showBollinger]);

  return (
    <div className="bg-[#0e1626] border border-[#1c2a40] rounded p-4 flex flex-col space-y-3 font-mono">
      {/* Header Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between pb-3 border-b border-[#1b263b] gap-3">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5">
            <span className="text-sm font-bold text-white uppercase">{ticker}</span>
            <span className="text-xs text-[#64748b]">&middot; Interactive OHLCV</span>
          </div>
          {/* Timeframe Bar */}
          <div className="flex items-center space-x-1 bg-[#121c2d] border border-[#1f2d42] p-1 rounded text-[11px]">
            {(['5D', '1M', '3M', '6M', '1Y', 'ALL'] as Timeframe[]).map(tf => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-2 py-0.5 rounded transition ${
                  timeframe === tf ? 'bg-[#00b0ff]/20 text-[#00b0ff] font-bold' : 'text-[#64748b] hover:text-white'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>

        {/* Technical Indicators Toggle Bar */}
        <div className="flex items-center space-x-2 text-xs flex-wrap gap-y-1">
          <span className="text-[10px] text-[#64748b] uppercase">Overlays:</span>
          <button
            onClick={() => setShowSMA20(!showSMA20)}
            className={`px-2 py-0.5 rounded text-[10px] border transition ${
              showSMA20 
                ? 'bg-[#00b0ff]/15 border-[#00b0ff] text-[#00b0ff] font-bold' 
                : 'bg-[#121c2d] border-[#1f2d42] text-[#64748b] hover:text-white'
            }`}
          >
            SMA 20
          </button>
          <button
            onClick={() => setShowSMA50(!showSMA50)}
            className={`px-2 py-0.5 rounded text-[10px] border transition ${
              showSMA50 
                ? 'bg-[#ffd600]/15 border-[#ffd600] text-[#ffd600] font-bold' 
                : 'bg-[#121c2d] border-[#1f2d42] text-[#64748b] hover:text-white'
            }`}
          >
            SMA 50
          </button>
          <button
            onClick={() => setShowEMA20(!showEMA20)}
            className={`px-2 py-0.5 rounded text-[10px] border transition ${
              showEMA20 
                ? 'bg-[#a855f7]/15 border-[#a855f7] text-[#c084fc] font-bold' 
                : 'bg-[#121c2d] border-[#1f2d42] text-[#64748b] hover:text-white'
            }`}
          >
            EMA 20
          </button>
          <button
            onClick={() => setShowBollinger(!showBollinger)}
            className={`px-2 py-0.5 rounded text-[10px] border transition ${
              showBollinger 
                ? 'bg-[#38bdf8]/15 border-[#38bdf8] text-[#38bdf8] font-bold' 
                : 'bg-[#121c2d] border-[#1f2d42] text-[#64748b] hover:text-white'
            }`}
          >
            Bollinger (20,2)
          </button>
          <button
            onClick={() => setShowGuide(!showGuide)}
            className="p-1 rounded text-[#64748b] hover:text-white transition"
            title="Technical Indicator Documentation"
          >
            <HelpCircle className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Indicator Documentation Drawer */}
      {showGuide && (
        <div className="p-3 bg-[#090d16] border border-[#1b273d] rounded text-[11px] text-[#94a3b8] leading-relaxed grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <strong className="text-white">SMA (Simple Moving Average):</strong> Unweighted average closing price over 20/50 bars, establishing support/resistance trend baselines.
          </div>
          <div>
            <strong className="text-white">EMA (Exponential Moving Average):</strong> Applies heavier weighting to recent bars, reacting faster to market inflection points.
          </div>
          <div>
            <strong className="text-white">Bollinger Bands:</strong> Volatility channels (2 standard deviations above and below 20-period SMA) defining overbought/oversold boundaries.
          </div>
        </div>
      )}

      {/* Chart Canvas */}
      <div ref={chartContainerRef} className="w-full rounded overflow-hidden min-h-[440px]" />

      <div className="flex justify-between items-center text-[10px] text-[#64748b] pt-2 border-t border-[#172236]">
        <span>Lightweight Charts &trade; High-DPI Canvas &middot; Crosshair & Pan Enabled</span>
        <span>Green = Bullish close &middot; Red = Bearish close &middot; Lower Panel = Verified Trading Volume</span>
      </div>
    </div>
  );
};
