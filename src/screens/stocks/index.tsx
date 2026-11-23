// Stocks workspace (R05). Owned by T07-stocks-files.
// Contract: export `stocksScreen` = { Sidebar, Main } (see src/screens.ts).
import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowUp, Globe, MoreHorizontal, Search, TrendingUp } from "lucide-react";
import { ICON, IconButton, ImageCard, SearchField, SidebarHeader } from "../../ui";
import { watchlist, defaultStock, indices, newsItems, logoColor, type Stock } from "./data";
import { useLiveQuotes } from "./live";
import s from "./stocks.module.css";

type Range = "1D" | "1W" | "1M" | "3M" | "1Y" | "MAX";
type Tab = "overview" | "chart" | "financials" | "news" | "analysis" | "peers";

/* ---- sparkline SVG ---- */
function Sparkline({ data, up }: { data: number[]; up: boolean }) {
  const w = 60, h = 28;
  const min = Math.min(...data), max = Math.max(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`).join(" ");
  const areaPts = `0,${h} ${pts} ${w},${h}`;
  const color = up ? "var(--success)" : "var(--danger)";
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className={s.sparklineSvg} width={w} height={h}>
      <polygon points={areaPts} fill={color} opacity={0.1} />
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/* ---- area chart (hand-written SVG) ---- */
function AreaChart({ data, range }: { data: number[]; range: Range }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ w: 600, h: 240 });
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observe = new ResizeObserver((entries) => {
      const { width } = entries[0].contentRect;
      setDims({ w: width, h: 240 });
    });
    observe.observe(el);
    return () => observe.disconnect();
  }, []);

  const min = Math.min(...data), max = Math.max(...data);
  const rangeVal = max - min || 1;
  const pad = 10;
  const chartW = dims.w - pad * 2;
  const chartH = dims.h - pad * 2;

  const pts = data.map((v, i) => ({
    x: pad + (i / (data.length - 1)) * chartW,
    y: pad + chartH - ((v - min) / rangeVal) * chartH,
  }));

  const linePath = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
  const areaPath = `${linePath} L${pts[pts.length - 1].x},${pad + chartH} L${pts[0].x},${pad + chartH} Z`;

  const isUp = data[data.length - 1] >= data[0];
  const color = isUp ? "var(--success)" : "var(--danger)";

  const hovered = hoverIdx !== null ? pts[hoverIdx] : null;
  const hoveredPrice = hoverIdx !== null ? data[hoverIdx] : null;

  return (
    <div ref={containerRef} className={s.chartSvg} onMouseLeave={() => setHoverIdx(null)}>
      <svg width="100%" height="100%" viewBox={`0 0 ${dims.w} ${dims.h}`} preserveAspectRatio="none">
        {/* grid lines */}
        {[0.25, 0.5, 0.75].map((f) => (
          <line key={f} x1={pad} y1={pad + chartH * f} x2={dims.w - pad} y2={pad + chartH * f}
            stroke="var(--border)" strokeWidth={1} />
        ))}
        {/* area */}
        <path d={areaPath} fill={color} opacity={0.08} />
        {/* line */}
        <path d={linePath} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
        {/* crosshair */}
        {hovered && (
          <>
            <line x1={hovered.x} y1={pad} x2={hovered.x} y2={pad + chartH} className={s.crosshairLine} />
            <circle cx={hovered.x} cy={hovered.y} r={4} fill={color} stroke="var(--surface-solid)" strokeWidth={2} />
          </>
        )}
        {/* price label on hover */}
        {hoveredPrice !== null && (
          <g>
            <rect x={Math.min(hovered!.x + 8, dims.w - 60)} y={Math.max(hovered!.y - 18, 2)} width={52} height={16} rx={4} className={s.priceLabelBg} />
            <text x={Math.min(hovered!.x + 34, dims.w - 34)} y={hovered!.y - 7} className={s.priceLabelText}>
              ${hoveredPrice.toFixed(2)}
            </text>
          </g>
        )}
      </svg>
      {/* hover targets */}
      <div style={{ position: "relative", height: 0 }}>
        {pts.map((p, i) => (
          <div key={i}
            style={{ position: "absolute", left: `${(p.x / dims.w) * 100}%`, top: 0, width: 1, height: dims.h, cursor: "crosshair" }}
            onMouseEnter={() => setHoverIdx(i)}
          />
        ))}
      </div>
    </div>
  );
}

/* generate fake series per range — smooth random walk, rescaled so min/max span ~8% around base, last point = base */
const generateSeries = (base: number, range: Range): number[] => {
  const points = { "1D": 24, "1W": 7 * 4, "1M": 30, "3M": 90, "1Y": 252, "MAX": 500 }[range];
  const vol = base * 0.002;
  const drift = (Math.random() - 0.5) * vol * 0.2;
  const pts: number[] = [];
  let v = base * (0.98 + Math.random() * 0.02);
  for (let i = 0; i < points - 1; i++) {
    v += (Math.random() - 0.48) * vol + drift;
    pts.push(v);
  }
  if (pts.length === 0) return [base];
  const rawMin = Math.min(...pts);
  const rawMax = Math.max(...pts);
  const rawRange = rawMax - rawMin || 1;
  // map to [base*0.96, base*1.04] so the full 8% band is used symmetrically
  const targetLo = base * 0.96;
  const targetHi = base * 1.04;
  const targetRange = targetHi - targetLo;
  const scaled = pts.map((p) => targetLo + ((p - rawMin) / rawRange) * targetRange);
  // snap last point to base exactly — no jump
  scaled[scaled.length - 1] = base;
  return scaled;
};

/* ---- Sidebar ---- */
function StocksSidebar() {
  const [selected, setSelected] = useState("AAPL");
  useLiveQuotes();

  return (
    <div className={s.sidebar}>
      <SidebarHeader title="Stocks & Markets">
        <IconButton icon={Search} label="Search" />
      </SidebarHeader>

      {/* Market Overview */}
      <div className={s.marketCard}>
        <div className={s.marketCardTitle}>Market Overview</div>
        {indices.map((idx) => (
          <div key={idx.ticker} className={s.marketRow}>
            <span className={s.marketName}>{idx.name}</span>
            <span className={s.marketValue}>{idx.value}</span>
            <span className={`${s.marketChange} ${idx.positive ? s.marketChangeUp : s.marketChangeDown}`}>
              {idx.change}
            </span>
          </div>
        ))}
      </div>

      {/* Watchlist */}
      <div className={s.watchlistSection}>
        <div className={s.watchlistLabel}>My Watchlist</div>
        {watchlist.map((stk) => (
          <div key={stk.ticker}
            className={`${s.watchlistItem} ${selected === stk.ticker ? s.watchlistItemActive : ""}`}
            onClick={() => setSelected(stk.ticker)}
          >
            <div className={s.logoInitials} style={{ background: logoColor(stk.ticker) }}>{stk.ticker}</div>
            <div className={s.watchlistBody}>
              <div className={s.watchlistTicker}>{stk.ticker}</div>
              <div className={s.watchlistName}>{stk.name}</div>
            </div>
            <div className={s.watchlistTrail}>
              <div className={s.watchlistPrice}>${stk.price.toFixed(2)}</div>
              <div className={`${s.watchlistChange} ${stk.change >= 0 ? s.watchlistChangeUp : s.watchlistChangeDown}`}>
                {stk.change >= 0 ? "+" : ""}{stk.changePct.toFixed(2)}%
              </div>
            </div>
            <Sparkline data={stk.sparkline} up={stk.change >= 0} />
          </div>
        ))}
      </div>

      {/* Popular indices */}
      <div className={s.popularSection}>
        <div className={s.popularLabel}>Popular Indices</div>
        {indices.slice(0, 3).map((idx) => (
          <div key={idx.ticker} className={s.popularItem}>
            <span className={s.popularName}>{idx.ticker}</span>
            <span className={s.popularVal}>{idx.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---- Main ---- */
function StocksMain() {
  const [selectedTicker, setSelectedTicker] = useState("AAPL");
  useLiveQuotes();
  const [range, setRange] = useState<Range>("1D");
  const [tab, setTab] = useState<Tab>("overview");
  const [toast, setToast] = useState<string | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stock = watchlist.find((s) => s.ticker === selectedTicker) ?? defaultStock;
  const activeSeries = generateSeries(stock.price, range);

  const showToast = (msg: string) => {
    setToast(msg);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 2500);
  };

  const handleBuy = () => showToast(`Buy order placed for ${selectedTicker}`);
  const handleSell = () => showToast(`Sell order placed for ${selectedTicker}`);

  const isUp = stock.change >= 0;

  return (
    <div className={s.main}>
      <div className={s.mainInner}>
        {/* Ask bar */}
        <div className={s.askBar}>
          <Globe size={16} strokeWidth={ICON.strokeWidth} color="var(--text-3)" />
          <input className={s.askInput} placeholder="Ask about any stock or market…" />
          <span className={s.marketTag}><TrendingUp size={12} strokeWidth={2} /> Markets</span>
        </div>

        {/* Tabs */}
        <div className={s.tabsRow}>
          {(["overview", "chart", "financials", "news", "analysis", "peers"] as const).map((t) => (
            <button key={t} className={`${s.tabBtn} ${tab === t ? s.tabBtnActive : ""}`}
              onClick={() => setTab(t)}>
              {t[0].toUpperCase() + t.slice(1)}
            </button>
          ))}
          <div className={s.spacer} />
          <IconButton icon={MoreHorizontal} label="More" />
        </div>

        {/* Stock header */}
        <div className={s.stockHeader}>
          <div className={s.stockHeaderLogo} style={{ background: logoColor(stock.ticker) }}>
            {stock.ticker}
          </div>
          <div className={s.stockHeaderInfo}>
            <div className={s.stockTicker}>{stock.ticker}</div>
            <div className={s.stockName}>{stock.name}</div>
          </div>
          <div className={s.stockPriceBlock}>
            <div className={s.stockPrice}>${stock.price.toFixed(2)}</div>
            <div className={`${s.stockChange} ${isUp ? s.stockChangeUp : s.stockChangeDown}`}>
              {isUp ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
              {isUp ? "+" : ""}{stock.change.toFixed(2)} ({isUp ? "+" : ""}{stock.changePct.toFixed(2)}%)
            </div>
          </div>
        </div>

        {/* Range buttons */}
        <div className={s.rangeBtns}>
          {(["1D", "1W", "1M", "3M", "1Y", "MAX"] as Range[]).map((r) => (
            <button key={r} className={`${s.rangeBtn} ${range === r ? s.rangeBtnActive : ""}`}
              onClick={() => setRange(r)}>{r}</button>
          ))}
        </div>

        {/* Index mini-cards */}
        <div className={s.indexMiniCards}>
          {indices.map((idx) => (
            <div key={idx.ticker} className={s.indexMiniCard}>
              <div>
                <div className={s.indexMiniName}>{idx.name}</div>
                <div className={s.indexMiniValue}>{idx.value}</div>
              </div>
              <span className={`${s.indexMiniChange} ${idx.positive ? s.indexMiniUp : s.indexMiniDown}`}>
                {idx.change}
              </span>
            </div>
          ))}
        </div>

        {/* Content */}
        <div className={s.contentArea}>
          {(tab === "overview" || tab === "chart") && (
            <>
              <div className={s.chartCard}>
                <div className={s.chartTitle}>Price Chart · {range}</div>
                <AreaChart data={activeSeries} range={range} />
              </div>

              {/* Two-column grid: left = stats + news, right = Trade/Rating/Target panel */}
              <div className={s.detailGrid}>
                <div className={s.detailLeft}>
                  <div className={s.statsGrid}>
                    <div className={s.statCard}>
                      <div className={s.statLabel}>Market Cap</div>
                      <div className={s.statValue}>2.98T</div>
                      <div className={s.statSub}>USD</div>
                    </div>
                    <div className={s.statCard}>
                      <div className={s.statLabel}>P/E Ratio</div>
                      <div className={s.statValue}>31.2</div>
                      <div className={s.statSub}>Trailing twelve months</div>
                    </div>
                    <div className={s.statCard}>
                      <div className={s.statLabel}>52-Week Range</div>
                      <div className={s.statValue}>$124 — $212</div>
                      <div className={s.statSub}>Current: {(stock.price / 212 * 100).toFixed(0)}% of range</div>
                    </div>
                    <div className={s.statCard}>
                      <div className={s.statLabel}>Volume</div>
                      <div className={s.statValue}>54.2M</div>
                      <div className={s.statSub}>Avg: 48.1M</div>
                    </div>
                    <div className={s.statCard}>
                      <div className={s.statLabel}>Dividend Yield</div>
                      <div className={s.statValue}>0.52%</div>
                      <div className={s.statSub}>Quarterly $0.24</div>
                    </div>
                    <div className={s.statCard}>
                      <div className={s.statLabel}>Beta</div>
                      <div className={s.statValue}>1.28</div>
                      <div className={s.statSub}>vs S&P 500</div>
                    </div>
                  </div>
                  <div style={{ marginTop: "var(--s-5)" }}>
                    <div className={s.sectionTitle}>Latest News</div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "var(--s-3)", marginTop: "var(--s-3)" }}>
                      {newsItems.map((item) => (
                        <ImageCard
                          key={item.id}
                          src={item.image}
                          title={item.title}
                          subtitle={`${item.source ?? "Market"} · ${item.time}`}
                          ratio={4 / 3}
                        />
                      ))}
                    </div>
                  </div>
                </div>

                <div className={s.detailRight}>
                  <div className={s.panelCard}>
                    <div className={s.panelTitle}>Trade</div>
                    <div className={s.buySellRow}>
                      <button className={s.buyBtn} onClick={handleBuy}>Buy</button>
                      <button className={s.sellBtn} onClick={handleSell}>Sell</button>
                    </div>
                  </div>
                  <div className={s.panelCard}>
                    <div className={s.panelTitle}>Analyst Rating</div>
                    <div className={s.ringWrap}>
                      <svg viewBox="0 0 36 36" className={s.ringSvg}>
                        <circle cx="18" cy="18" r="15.5" fill="none" stroke="var(--border)" strokeWidth="3" />
                        <circle cx="18" cy="18" r="15.5" fill="none" stroke="var(--success)" strokeWidth="3"
                          strokeDasharray={`${72 * 2 * Math.PI * 0.72} ${2 * Math.PI * 15.5}`}
                          strokeLinecap="round" transform="rotate(-90 18 18)" />
                        <text x="18" y="20" textAnchor="middle" fill="var(--text)" fontSize="7" fontWeight="700">72</text>
                      </svg>
                      <div>
                        <div className={s.ringScore}>Buy</div>
                        <div className={s.ringLabel}>Consensus · 18 analysts</div>
                      </div>
                    </div>
                  </div>
                  <div className={s.panelCard}>
                    <div className={s.panelTitle}>Price Target</div>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                      <span style={{ fontSize: "var(--fs-sm)", color: "var(--text-2)" }}>Low</span>
                      <span style={{ fontSize: "var(--fs-sm)", fontWeight: 600 }}>$175.00</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                      <span style={{ fontSize: "var(--fs-sm)", color: "var(--text-2)" }}>Average</span>
                      <span style={{ fontSize: "var(--fs-sm)", fontWeight: 600 }}>$225.00</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ fontSize: "var(--fs-sm)", color: "var(--text-2)" }}>High</span>
                      <span style={{ fontSize: "var(--fs-sm)", fontWeight: 600 }}>$260.00</span>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}

          {tab === "financials" && (
            <div className={s.chartCard}>
              <div className={s.chartTitle}>Financials</div>
              <div style={{ padding: "var(--s-6) 0", textAlign: "center", color: "var(--text-3)" }}>
                Financial data coming soon. <br />Historical income statement, balance sheet, and cash flow will appear here.
              </div>
            </div>
          )}

          {tab === "news" && (
            <div>
              <div className={s.sectionTitle} style={{ marginBottom: "var(--s-3)" }}>Latest News</div>
              <div className={s.newsList}>
                {newsItems.map((item) => (
                  <div key={item.id} className={s.newsItem}>
                    <div className={s.newsImg}>
                      <img src={item.image} alt={item.title} />
                    </div>
                    <div className={s.newsBody}>
                      <div className={s.newsTitle}>{item.title}</div>
                      <div className={s.newsSummary}>{item.summary}</div>
                      <div className={s.newsTime}>{item.time}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {tab === "analysis" && (
            <div className={s.chartCard}>
              <div className={s.chartTitle}>Technical Analysis</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--s-3)", marginTop: "var(--s-4)" }}>
                {[
                  { label: "RSI (14)", value: "62.4", signal: "Neutral" },
                  { label: "MACD", value: "1.82", signal: "Buy" },
                  { label: "MA (50)", value: "$192.30", signal: "Buy" },
                  { label: "MA (200)", value: "$178.50", signal: "Buy" },
                  { label: "Bollinger", value: "Upper band", signal: "Neutral" },
                  { label: "Stochastic", value: "78.1", signal: "Overbought" },
                ].map((ind) => (
                  <div key={ind.label} className={s.statCard}>
                    <div className={s.statLabel}>{ind.label}</div>
                    <div className={s.statValue}>{ind.value}</div>
                    <div className={s.statSub}>{ind.signal}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {tab === "peers" && (
            <div className={s.chartCard}>
              <div className={s.chartTitle}>Peers Comparison</div>
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--s-2)", marginTop: "var(--s-4)" }}>
                {watchlist.map((s2) => (
                  <div key={s2.ticker} className={s.listRow} style={{ cursor: "pointer" }}
                    onClick={() => { setSelectedTicker(s2.ticker); setTab("overview"); }}>
                    <div className={s.logoInitials} style={{ background: logoColor(s2.ticker), width: 32, height: 32, borderRadius: 8, display: "grid", placeItems: "center", fontSize: 10, fontWeight: 700, color: "var(--on-accent)" }}>
                      {s2.ticker}
                    </div>
                    <div className={s.listRowBody}>
                      <div className={s.listRowTitle}>{s2.ticker} · {s2.name}</div>
                    </div>
                    <div style={{ textAlign: "end" }}>
                      <div style={{ fontSize: "var(--fs-md)", fontWeight: 600 }}>${s2.price.toFixed(2)}</div>
                      <div style={{ fontSize: "var(--fs-xs)", color: s2.change >= 0 ? "var(--success)" : "var(--danger)" }}>
                        {s2.change >= 0 ? "+" : ""}{s2.changePct.toFixed(2)}%
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Toast */}
      {toast && <div className={s.toast}>{toast}</div>}
    </div>
  );
}

export const stocksScreen = { Sidebar: StocksSidebar, Main: StocksMain };
