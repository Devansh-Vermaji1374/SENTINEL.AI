export interface OHLCVBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IndicatorPoint {
  time: string;
  value: number;
}

export interface MACDPoint {
  time: string;
  macd: number;
  signal: number;
  histogram: number;
}

export interface BollingerPoint {
  time: string;
  upper: number;
  middle: number;
  lower: number;
}

export function calculateSMA(data: OHLCVBar[], period: number): IndicatorPoint[] {
  const result: IndicatorPoint[] = [];
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) continue;
    let sum = 0;
    for (let j = 0; j < period; j++) {
      sum += data[i - j].close;
    }
    result.push({
      time: data[i].date.split('T')[0],
      value: Number((sum / period).toFixed(2))
    });
  }
  return result;
}

export function calculateEMA(data: OHLCVBar[], period: number): IndicatorPoint[] {
  const result: IndicatorPoint[] = [];
  if (data.length < period) return result;
  
  const k = 2 / (period + 1);
  let sum = 0;
  for (let i = 0; i < period; i++) {
    sum += data[i].close;
  }
  let prevEMA = sum / period;
  result.push({
    time: data[period - 1].date.split('T')[0],
    value: Number(prevEMA.toFixed(2))
  });

  for (let i = period; i < data.length; i++) {
    const currentEMA = (data[i].close - prevEMA) * k + prevEMA;
    result.push({
      time: data[i].date.split('T')[0],
      value: Number(currentEMA.toFixed(2))
    });
    prevEMA = currentEMA;
  }
  return result;
}

export function calculateRSI(data: OHLCVBar[], period: number = 14): IndicatorPoint[] {
  const result: IndicatorPoint[] = [];
  if (data.length <= period) return result;

  let gains = 0;
  let losses = 0;

  for (let i = 1; i <= period; i++) {
    const change = data[i].close - data[i - 1].close;
    if (change >= 0) gains += change;
    else losses += Math.abs(change);
  }

  let avgGain = gains / period;
  let avgLoss = losses / period;

  let rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
  let rsi = 100 - (100 / (1 + rs));
  result.push({
    time: data[period].date.split('T')[0],
    value: Number(rsi.toFixed(2))
  });

  for (let i = period + 1; i < data.length; i++) {
    const change = data[i].close - data[i - 1].close;
    const gain = change >= 0 ? change : 0;
    const loss = change < 0 ? Math.abs(change) : 0;

    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;

    rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
    rsi = 100 - (100 / (1 + rs));
    result.push({
      time: data[i].date.split('T')[0],
      value: Number(rsi.toFixed(2))
    });
  }
  return result;
}

export function calculateBollingerBands(data: OHLCVBar[], period: number = 20, multiplier: number = 2): BollingerPoint[] {
  const result: BollingerPoint[] = [];
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) continue;
    let sum = 0;
    for (let j = 0; j < period; j++) {
      sum += data[i - j].close;
    }
    const middle = sum / period;
    let varianceSum = 0;
    for (let j = 0; j < period; j++) {
      varianceSum += Math.pow(data[i - j].close - middle, 2);
    }
    const stdDev = Math.sqrt(varianceSum / period);
    result.push({
      time: data[i].date.split('T')[0],
      middle: Number(middle.toFixed(2)),
      upper: Number((middle + multiplier * stdDev).toFixed(2)),
      lower: Number((middle - multiplier * stdDev).toFixed(2))
    });
  }
  return result;
}
