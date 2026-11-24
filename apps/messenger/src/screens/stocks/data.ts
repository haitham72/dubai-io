// Stocks fake data. Photos verified: curl → 200 on 2026-10-04.
import { img } from "../../ui";

export interface Stock {
  ticker: string;
  name: string;
  price: number;
  change: number;       // absolute daily change
  changePct: number;    // percent
  sparkline: number[];  // 24 data points
  logo: string;         // initials bg color
}

export interface IndexItem {
  name: string;
  ticker: string;
  value: string;
  change: string;
  positive: boolean;
}

export interface NewsItem {
  id: string;
  title: string;
  summary: string;
  time: string;
  image: string;
  source?: string;
}

const makeSparkline = (base: number, vol: number, trend: number): number[] => {
  const pts: number[] = [];
  let v = base;
  for (let i = 0; i < 24; i++) {
    v += (Math.random() - 0.48 + trend) * vol;
    pts.push(Math.max(v, base * 0.85));
  }
  return pts;
};

export const watchlist: Stock[] = [
  {
    ticker: "AAPL", name: "Apple Inc.", price: 198.11, change: 2.34, changePct: 1.19,
    sparkline: makeSparkline(195, 1.2, 0.05), logo: "bg-blue",
  },
  {
    ticker: "TSLA", name: "Tesla Inc.", price: 248.42, change: -3.18, changePct: -1.26,
    sparkline: makeSparkline(252, 2.5, -0.08), logo: "bg-red",
  },
  {
    ticker: "NVDA", name: "NVIDIA Corp.", price: 875.28, change: 12.45, changePct: 1.44,
    sparkline: makeSparkline(860, 5, 0.12), logo: "bg-green",
  },
  {
    ticker: "MSFT", name: "Microsoft Corp.", price: 417.86, change: 1.02, changePct: 0.25,
    sparkline: makeSparkline(416, 1.0, 0.02), logo: "bg-purple",
  },
  {
    ticker: "AMZN", name: "Amazon.com Inc.", price: 186.49, change: -0.87, changePct: -0.46,
    sparkline: makeSparkline(187, 1.5, -0.03), logo: "bg-orange",
  },
];

export const defaultStock = watchlist[0];

export const indices: IndexItem[] = [
  { name: "S&P 500", ticker: ".INX", value: "5,432.18", change: "+0.87%", positive: true },
  { name: "NASDAQ", ticker: ".IXIC", value: "17,123.46", change: "+1.24%", positive: true },
  { name: "DOW Jones", ticker: ".DJI", value: "41,876.32", change: "+0.53%", positive: true },
  { name: "DAX", ticker: ".DAX", value: "18,456.77", change: "-0.31%", positive: false },
];

export const newsItems: NewsItem[] = [
  {
    id: "n1",
    title: "Fed signals potential rate cuts in 2025",
    summary: "Federal Reserve officials hinted at possible interest rate reductions next year as inflation shows signs of cooling.",
    time: "2h ago",
    image: img("photo-1542751371-adc38448a05e", 400),
    source: "Reuters",
  },
  {
    id: "n2",
    title: "AI chip demand drives NVIDIA revenue record",
    summary: "Data center revenue surged past expectations as cloud providers race to build out generative AI infrastructure.",
    time: "5h ago",
    image: img("photo-1522202176988-66273c2fd55f", 400),
    source: "Bloomberg",
  },
  {
    id: "n3",
    title: "UAE markets see record foreign inflows",
    summary: "Dubai and Abu Dhabi stock exchanges reported their highest monthly inflows as investors rebalance toward the region.",
    time: "8h ago",
    image: img("photo-1511895426328-dc8714191300", 400),
    source: "Gulf News",
  },
];

const LOGO_COLORS: Record<string, string> = {
  AAPL: "#333", TSLA: "#cc0000", NVDA: "#76b900", MSFT: "#00a4ef", AMZN: "#ff9900",
};

export function logoColor(ticker: string): string {
  return LOGO_COLORS[ticker] ?? "#667085";
}
