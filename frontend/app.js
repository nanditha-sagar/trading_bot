'use strict';

const API = '';
const state = {
  mode: 'paper',
  symbol: 'BTCUSDT',
  interval: '15m',
  side: 'BUY',
  orderType: 'MARKET',
  marketPrice: null,
  priceChange: 0.0,
  priceChangePercent: 0.0,
  submitting: false,
  chartData: [],         
  activeTab: 'positions', 
  ws: null,
  wsReconnectTimer: null,
};
const $ = id => document.getElementById(id);

const dom = {
  btnLogout:         $('btn-logout'),
  linkLogin:         $('link-login'),
  userProfileBadge:  $('user-profile-badge'),
  navUserAvatar:     $('nav-user-avatar'),
  navUserName:       $('nav-user-name'),
  btnModePaper:      $('btn-mode-paper'),
  btnModeTestnet:    $('btn-mode-testnet'),
  navStatusDot:      $('nav-status-dot'),
  navStatusText:     $('nav-status-text'),
  metricBalance:     $('metric-balance'),
  metricEquity:      $('metric-equity'),
  metricAvailMargin: $('metric-avail-margin'),
  metricUnrealized:  $('metric-unrealized-pnl'),
  metricRealized:    $('metric-realized-pnl'),
  btnResetPortfolio: $('btn-reset-portfolio'),
  inputSymbolSearch: $('input-symbol-search'),
  symbolPills:       document.querySelectorAll('.symbol-pill'),
  tfButtons:         document.querySelectorAll('.tf-btn'),
  chartPriceCurrent: $('chart-price-current'),
  chartPriceChange:  $('chart-price-change'),
  chart24hHigh:      $('chart-24h-high'),
  chart24hLow:       $('chart-24h-low'),
  chart24hVol:       $('chart-24h-vol'),
  chartStreamDot:    $('chart-stream-dot'),
  chartStreamStatus: $('chart-stream-status'),
  chartViewport:     $('chart-viewport'),
  canvas:            $('candlestick-canvas'),
  chartLoader:       $('chart-loader'),
  badgeOrderSim:     $('badge-order-sim'),
  tabBuy:            $('tab-buy'),
  tabSell:           $('tab-sell'),
  selectOrderType:   $('select-order-type'),
  inputQty:          $('input-qty'),
  groupLimitPrice:   $('group-limit-price'),
  inputLimitPrice:   $('input-limit-price'),
  btnUseMarketPrice: $('btn-use-market-price'),
  errQtyMsg:         $('err-qty-msg'),
  errPriceMsg:       $('err-price-msg'),
  revSymbol:         $('rev-symbol'),
  revType:           $('rev-type'),
  revEstValue:       $('rev-est-value'),
  revMargin:         $('rev-margin'),
  btnSubmitOrder:    $('btn-submit-order'),
  orderResultToast:  $('order-result-toast'),
  tabBtnPositions:   $('tab-btn-positions'),
  tabBtnOrders:      $('tab-btn-orders'),
  tabBtnTrades:      $('tab-btn-trades'),
  btnRefreshTables:  $('btn-refresh-tables'),
  viewPositions:     $('view-positions'),
  viewOrders:        $('view-orders'),
  viewTrades:        $('view-trades'),
  tbodyPositions:    $('tbody-positions'),
  tbodyOrders:       $('tbody-orders'),
  tbodyTrades:       $('tbody-trades'),
  countPositions:    $('count-positions'),
  countOrders:       $('count-orders'),
  confirmModal:      $('confirm-modal'),
  modalTitle:        $('modal-title'),
  modalModeBadge:    $('modal-mode-badge'),
  modalProduct:      $('modal-product'),
  modalSide:         $('modal-side'),
  modalType:         $('modal-type'),
  modalQty:          $('modal-qty'),
  modalPriceRow:     $('modal-price-row'),
  modalPrice:        $('modal-price'),
  modalValue:        $('modal-value'),
  modalExecType:     $('modal-exec-type'),
  modalBtnCancel:    $('modal-btn-cancel'),
  modalBtnConfirm:   $('modal-btn-confirm'),
};

dom.btnModePaper.addEventListener('click', () => setMode('paper'));
dom.btnModeTestnet.addEventListener('click', () => setMode('testnet'));

function setMode(newMode) {
  state.mode = newMode;
  const isPaper = newMode === 'paper';

  dom.btnModePaper.className = 'mode-btn' + (isPaper ? ' active-paper' : '');
  dom.btnModePaper.setAttribute('aria-selected', isPaper ? 'true' : 'false');
  dom.btnModeTestnet.className = 'mode-btn' + (!isPaper ? ' active-testnet' : '');
  dom.btnModeTestnet.setAttribute('aria-selected', !isPaper ? 'true' : 'false');

  if (isPaper) {
    dom.badgeOrderSim.textContent = 'SIMULATED';
    dom.badgeOrderSim.className = 'badge-simulated-tag';
    dom.navStatusDot.className = 'status-dot active';
    dom.navStatusText.textContent = 'Market Live (Paper Engine)';
    dom.modalModeBadge.textContent = 'SIMULATED';
    dom.modalModeBadge.className = 'badge-simulated-tag';
    dom.modalExecType.textContent = 'Paper Simulation (Zero Risk)';
    dom.modalExecType.style.color = 'var(--green)';
  } else {
    dom.badgeOrderSim.textContent = 'TESTNET';
    dom.badgeOrderSim.className = 'badge-simulated-tag testnet';
    dom.navStatusDot.className = 'status-dot testnet';
    dom.navStatusText.textContent = 'Binance Testnet Connected';
    dom.modalModeBadge.textContent = 'TESTNET';
    dom.modalModeBadge.className = 'badge-simulated-tag testnet';
    dom.modalExecType.textContent = 'Binance Futures Testnet API';
    dom.modalExecType.style.color = 'var(--amber)';
  }

  updateSubmitButton();
  loadAccount();
  loadOrders();
}

dom.symbolPills.forEach(pill => {
  pill.addEventListener('click', () => {
    dom.symbolPills.forEach(p => p.classList.remove('active'));
    pill.classList.add('active');
    setSymbol(pill.dataset.symbol);
  });
});

dom.inputSymbolSearch.addEventListener('change', () => {
  const sym = dom.inputSymbolSearch.value.trim().toUpperCase();
  if (sym) {
    dom.symbolPills.forEach(p => {
      p.classList.toggle('active', p.dataset.symbol === sym);
    });
    setSymbol(sym);
  }
});

function setSymbol(sym) {
  state.symbol = sym;
  dom.inputSymbolSearch.value = sym;
  dom.revSymbol.textContent = sym;
  updateSubmitButton();

  // Reload historical candles and switch live stream
  fetchMarketInfo();
  loadHistoricalCandlesAndConnectStream();
}

dom.tfButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    dom.tfButtons.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.interval = btn.dataset.interval;

    // Reload historical candles and switch live stream to selected interval
    loadHistoricalCandlesAndConnectStream();
  });
});

// ── 3. Market Info & 24hr Stats Fetching ──────────────────────────
async function fetchMarketInfo() {
  try {
    const res = await fetch(`${API}/api/market-info?symbol=${encodeURIComponent(state.symbol)}`);
    if (res.ok) {
      const data = await res.json();
      if (data.price) {
        state.marketPrice = Number(data.price);
        state.priceChange = Number(data.priceChange) || 0.0;
        state.priceChangePercent = Number(data.priceChangePercent) || 0.0;

        // Update Ticker UI
        updatePriceDisplay(state.marketPrice, state.priceChange, state.priceChangePercent);

        dom.chart24hHigh.textContent = formatMoney(data.highPrice);
        dom.chart24hLow.textContent  = formatMoney(data.lowPrice);
        dom.chart24hVol.textContent  = Number(data.volume).toLocaleString('en-US', { maximumFractionDigits: 0 });

        updateOrderReview();
      }
    }
  } catch (err) {
    console.warn('Market info fetch failed', err);
  }
}

function updatePriceDisplay(currentPrice, changeVal, changePct) {
  dom.chartPriceCurrent.textContent = formatMoney(currentPrice) + ' USDT';
  const isUp = changePct >= 0;
  dom.chartPriceChange.className = 'price-change ' + (isUp ? 'up' : 'down');
  dom.chartPriceChange.textContent = `${isUp ? '+' : ''}${changeVal.toFixed(2)} (${isUp ? '+' : ''}${changePct.toFixed(2)}%)`;
}

// ── 4. Historical Candles & WebSocket Live Stream ────────────────
async function loadHistoricalCandlesAndConnectStream() {
  // 1. Clean up old WebSocket connection before switching
  cleanupWebSocket();

  // 2. Fetch historical candles
  dom.chartLoader.classList.add('visible');
  updateStreamStatus('connecting');

  try {
    const res = await fetch(`${API}/api/klines?symbol=${encodeURIComponent(state.symbol)}&interval=${encodeURIComponent(state.interval)}&limit=70`);
    if (res.ok) {
      const data = await res.json();
      state.chartData = data.candles || [];
      if (state.chartData.length > 0) {
        const latest = state.chartData[state.chartData.length - 1];
        state.marketPrice = latest.close;
        updateOrderReview();
      }
      renderChart();
    } else {
      showChartError(`Real market data unavailable for ${state.symbol}`);
    }
  } catch (err) {
    showChartError(`Network error loading ${state.symbol} candles`);
  } finally {
    dom.chartLoader.classList.remove('visible');
  }

  // 3. Connect to Binance Futures Public WebSocket Kline Stream
  connectKlineWebSocket();
}

function showChartError(msg) {
  const canvas = dom.canvas;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const rect = dom.chartViewport.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, rect.width, rect.height);
  ctx.fillStyle = '#eb5b3c';
  ctx.font = '13px Inter, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(`⚠️ ${msg}`, rect.width / 2, rect.height / 2);
  updateStreamStatus('error');
}

function updateStreamStatus(status) {
  if (status === 'live') {
    dom.chartStreamDot.style.background = 'var(--green)';
    dom.chartStreamStatus.textContent = 'LIVE STREAM';
    dom.chartStreamStatus.style.color = 'var(--green)';
  } else if (status === 'connecting') {
    dom.chartStreamDot.style.background = 'var(--amber)';
    dom.chartStreamStatus.textContent = 'CONNECTING';
    dom.chartStreamStatus.style.color = 'var(--amber)';
  } else {
    dom.chartStreamDot.style.background = 'var(--red)';
    dom.chartStreamStatus.textContent = 'STREAM OFFLINE';
    dom.chartStreamStatus.style.color = 'var(--red)';
  }
}

function cleanupWebSocket() {
  if (state.wsReconnectTimer) {
    clearTimeout(state.wsReconnectTimer);
    state.wsReconnectTimer = null;
  }
  if (state.ws) {
    try {
      state.ws.onclose = null;
      state.ws.onerror = null;
      state.ws.onmessage = null;
      state.ws.close();
    } catch (_) {}
    state.ws = null;
  }
}

function connectKlineWebSocket() {
  const symLower = state.symbol.toLowerCase();
  const interval = state.interval;
  const targetSymbol = state.symbol;
  const targetInterval = state.interval;

  // Binance Futures Public Combined/Kline Stream (Zero API credentials required)
  const wsUrl = `wss://fstream.binance.com/ws/${symLower}@kline_${interval}`;

  try {
    const ws = new WebSocket(wsUrl);
    state.ws = ws;

    ws.onopen = () => {
      // Ensure this connection still matches current selected symbol/interval
      if (state.symbol === targetSymbol && state.interval === targetInterval) {
        updateStreamStatus('live');
      }
    };

    ws.onmessage = (event) => {
      // Guard against stale streams
      if (state.symbol !== targetSymbol || state.interval !== targetInterval) {
        ws.close();
        return;
      }

      try {
        const msg = JSON.parse(event.data);
        if (msg && msg.e === 'kline' && msg.k) {
          const k = msg.k;
          handleLiveKlineUpdate({
            time:   k.t,
            open:   parseFloat(k.o),
            high:   parseFloat(k.h),
            low:    parseFloat(k.l),
            close:  parseFloat(k.c),
            volume: parseFloat(k.v),
            isClosed: k.x,
          });
        }
      } catch (e) {
        console.warn('Error parsing live kline frame', e);
      }
    };

    ws.onerror = () => {
      updateStreamStatus('error');
    };

    ws.onclose = () => {
      // Automatic reconnection handling if this is still the active symbol
      if (state.symbol === targetSymbol && state.interval === targetInterval) {
        updateStreamStatus('connecting');
        state.wsReconnectTimer = setTimeout(() => {
          connectKlineWebSocket();
        }, 3000);
      }
    };
  } catch (err) {
    console.warn('WebSocket connection init failed', err);
    updateStreamStatus('error');
  }
}

/**
 * Updates the current candle's open, high, low, close, and volume
 * without refetching or rebuilding the whole dataset.
 */
function handleLiveKlineUpdate(liveCandle) {
  const candles = state.chartData;
  if (!candles || candles.length === 0) {
    state.chartData = [liveCandle];
  } else {
    const lastIndex = candles.length - 1;
    const lastCandle = candles[lastIndex];

    if (lastCandle.time === liveCandle.time) {
      // Same candle in-progress: update OHLCV in place
      lastCandle.high = Math.max(lastCandle.high, liveCandle.high);
      lastCandle.low  = Math.min(lastCandle.low, liveCandle.low);
      lastCandle.close = liveCandle.close;
      lastCandle.volume = liveCandle.volume;
    } else if (liveCandle.time > lastCandle.time) {
      // New candle interval started: append new candle and maintain window size
      candles.push(liveCandle);
      if (candles.length > 80) {
        candles.shift();
      }
    }
  }

  // Update live market price
  state.marketPrice = liveCandle.close;
  dom.chartPriceCurrent.textContent = formatMoney(state.marketPrice) + ' USDT';

  // Compute live change from the 24h baseline or first candle
  if (state.chartData.length > 1) {
    const baseline = state.chartData[0].open;
    const diff = state.marketPrice - baseline;
    const pct = (diff / baseline) * 100;
    updatePriceDisplay(state.marketPrice, diff, pct);
  }

  updateOrderReview();

  // Fast canvas repaint with updated candle values (no full dataset recreation)
  renderChart();
}

// ── 5. Canvas Candlestick Rendering ──────────────────────────────
function renderChart() {
  const canvas = dom.canvas;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const rect = dom.chartViewport.getBoundingClientRect();

  // Resize canvas according to display DPI
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  const w = rect.width;
  const h = rect.height;

  ctx.clearRect(0, 0, w, h);

  const candles = state.chartData;
  if (!candles || candles.length === 0) {
    ctx.fillStyle = '#8a94a6';
    ctx.font = '13px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Loading live candlestick data…', w / 2, h / 2);
    return;
  }

  // Margins for axes
  const margin = { top: 20, right: 75, bottom: 35, left: 10 };
  const plotW = w - margin.left - margin.right;
  const plotH = h - margin.top - margin.bottom;

  // Find min/max price for scaling
  let minP = Infinity;
  let maxP = -Infinity;
  let maxVol = 0;

  for (const c of candles) {
    if (c.low < minP) minP = c.low;
    if (c.high > maxP) maxP = c.high;
    if (c.volume > maxVol) maxVol = c.volume;
  }

  // Pad price range by 5%
  const pDiff = maxP - minP || 1;
  minP -= pDiff * 0.05;
  maxP += pDiff * 0.05;

  const priceToY = p => margin.top + plotH - ((p - minP) / (maxP - minP)) * plotH;

  // 1. Draw subtle horizontal grid lines & price labels (Angel One style)
  ctx.lineWidth = 1;
  ctx.strokeStyle = '#f1f5f9';
  ctx.fillStyle = '#8a94a6';
  ctx.font = '10.5px JetBrains Mono, monospace';
  ctx.textAlign = 'left';

  const gridSteps = 5;
  for (let i = 0; i <= gridSteps; i++) {
    const p = minP + (i / gridSteps) * (maxP - minP);
    const y = priceToY(p);
    ctx.beginPath();
    ctx.moveTo(margin.left, y);
    ctx.lineTo(margin.left + plotW, y);
    ctx.stroke();

    // Price label on right axis
    ctx.fillText(p.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 2 }), margin.left + plotW + 6, y + 4);
  }

  // 2. Draw Candlesticks & Volume Bars
  const n = candles.length;
  const candleGap = plotW / n;
  const candleW = Math.max(2, candleGap * 0.72);

  candles.forEach((c, i) => {
    const x = margin.left + i * candleGap + candleGap / 2;
    const isBullish = c.close >= c.open;
    const color = isBullish ? '#00b386' : '#eb5b3c';

    // Volume bar at bottom (subtle 20% height)
    const volH = maxVol > 0 ? (c.volume / maxVol) * (plotH * 0.22) : 0;
    const volY = margin.top + plotH - volH;
    ctx.fillStyle = isBullish ? 'rgba(0, 179, 134, 0.16)' : 'rgba(235, 91, 60, 0.16)';
    ctx.fillRect(x - candleW / 2, volY, candleW, volH);

    // Candlestick Wick
    ctx.strokeStyle = color;
    ctx.beginPath();
    ctx.moveTo(x, priceToY(c.high));
    ctx.lineTo(x, priceToY(c.low));
    ctx.stroke();

    // Candlestick Body
    const yOpen = priceToY(c.open);
    const yClose = priceToY(c.close);
    const bodyTop = Math.min(yOpen, yClose);
    const bodyH = Math.max(2, Math.abs(yClose - yOpen));

    ctx.fillStyle = color;
    ctx.fillRect(x - candleW / 2, bodyTop, candleW, bodyH);
  });

  // 3. Draw Latest Live Price Dashed Line across chart
  const latestClose = candles[candles.length - 1].close;
  const latestY = priceToY(latestClose);
  const isLatestBullish = candles[candles.length - 1].close >= candles[candles.length - 1].open;
  const lineColor = isLatestBullish ? '#00b386' : '#eb5b3c';

  ctx.setLineDash([4, 4]);
  ctx.strokeStyle = lineColor;
  ctx.beginPath();
  ctx.moveTo(margin.left, latestY);
  ctx.lineTo(margin.left + plotW, latestY);
  ctx.stroke();
  ctx.setLineDash([]);

  // Latest live price badge pill on axis
  ctx.fillStyle = lineColor;
  ctx.fillRect(margin.left + plotW + 2, latestY - 9, margin.right - 4, 18);
  ctx.fillStyle = '#ffffff';
  ctx.font = '10px JetBrains Mono, monospace';
  ctx.fillText(latestClose.toFixed(2), margin.left + plotW + 6, latestY + 3.5);
}

window.addEventListener('resize', () => {
  if (state.chartData.length > 0) renderChart();
});

// ── 6. Order Panel Logic ─────────────────────────────────────────
dom.tabBuy.addEventListener('click', () => setSide('BUY'));
dom.tabSell.addEventListener('click', () => setSide('SELL'));

function setSide(side) {
  state.side = side;
  const isBuy = side === 'BUY';
  dom.tabBuy.className = 'side-tab' + (isBuy ? ' active-buy' : '');
  dom.tabSell.className = 'side-tab' + (!isBuy ? ' active-sell' : '');

  dom.btnSubmitOrder.className = 'btn-order-action ' + (isBuy ? 'buy' : 'sell');
  updateSubmitButton();
}

dom.selectOrderType.addEventListener('change', () => {
  state.orderType = dom.selectOrderType.value;
  dom.revType.textContent = state.orderType;
  const isLimit = state.orderType === 'LIMIT';
  dom.groupLimitPrice.classList.toggle('hidden', !isLimit);
  if (isLimit && !dom.inputLimitPrice.value && state.marketPrice) {
    dom.inputLimitPrice.value = state.marketPrice.toFixed(2);
  }
  updateOrderReview();
});

dom.btnUseMarketPrice.addEventListener('click', () => {
  if (state.marketPrice) {
    dom.inputLimitPrice.value = state.marketPrice.toFixed(2);
    updateOrderReview();
  }
});

[dom.inputQty, dom.inputLimitPrice].forEach(el => {
  el.addEventListener('input', updateOrderReview);
});

function updateSubmitButton() {
  const sym = state.symbol;
  const action = state.side === 'BUY' ? 'BUY' : 'SELL';
  dom.btnSubmitOrder.textContent = `${action} ${sym}`;
}

function updateOrderReview() {
  const qty = parseFloat(dom.inputQty.value) || 0;
  let price = state.marketPrice || 0;

  if (state.orderType === 'LIMIT') {
    const p = parseFloat(dom.inputLimitPrice.value);
    if (!isNaN(p) && p > 0) price = p;
  }

  const estVal = qty * price;
  dom.revEstValue.textContent = `~${formatMoney(estVal)} USDT`;
  dom.revMargin.textContent   = `~${formatMoney(estVal)} USDT`;
}

// ── 7. Order Submission & Confirmation Modal ─────────────────────
dom.btnSubmitOrder.addEventListener('click', () => {
  hideToast();
  if (!validateOrderInputs()) return;
  openConfirmModal();
});

function validateOrderInputs() {
  let valid = true;
  const qty = parseFloat(dom.inputQty.value);

  if (!dom.inputQty.value.trim() || isNaN(qty) || qty <= 0) {
    dom.inputQty.classList.add('has-error');
    dom.errQtyMsg.classList.add('visible');
    valid = false;
  } else {
    dom.inputQty.classList.remove('has-error');
    dom.errQtyMsg.classList.remove('visible');
  }

  if (state.orderType === 'LIMIT') {
    const pr = parseFloat(dom.inputLimitPrice.value);
    if (!dom.inputLimitPrice.value.trim() || isNaN(pr) || pr <= 0) {
      dom.inputLimitPrice.classList.add('has-error');
      dom.errPriceMsg.classList.add('visible');
      valid = false;
    } else {
      dom.inputLimitPrice.classList.remove('has-error');
      dom.errPriceMsg.classList.remove('visible');
    }
  }
  return valid;
}

function openConfirmModal() {
  const qty = parseFloat(dom.inputQty.value);
  const isLimit = state.orderType === 'LIMIT';
  const pr = isLimit ? parseFloat(dom.inputLimitPrice.value) : (state.marketPrice || 0);
  const estVal = qty * pr;

  dom.modalProduct.textContent = state.symbol;
  dom.modalSide.textContent    = state.side;
  dom.modalType.textContent    = state.orderType;
  dom.modalQty.textContent     = String(qty);
  dom.modalValue.textContent   = `~${formatMoney(estVal)} USDT`;

  if (isLimit) {
    dom.modalPriceRow.classList.remove('hidden');
    dom.modalPrice.textContent = `${formatMoney(pr)} USDT`;
  } else {
    dom.modalPriceRow.classList.add('hidden');
  }

  dom.modalBtnConfirm.className = 'btn-confirm ' + (state.side === 'BUY' ? 'buy' : 'sell');
  dom.modalBtnConfirm.disabled = false;
  dom.modalBtnConfirm.textContent = 'Confirm & Place';

  dom.confirmModal.classList.add('visible');
}

dom.modalBtnCancel.addEventListener('click', closeConfirmModal);
dom.confirmModal.addEventListener('click', e => {
  if (e.target === dom.confirmModal) closeConfirmModal();
});

function closeConfirmModal() {
  dom.confirmModal.classList.remove('visible');
}

dom.modalBtnConfirm.addEventListener('click', executeOrder);

async function executeOrder() {
  if (state.submitting) return;
  state.submitting = true;
  dom.modalBtnConfirm.disabled = true;
  dom.modalBtnConfirm.innerHTML = '<span class="spinner"></span> Placing…';

  const isLimit = state.orderType === 'LIMIT';
  const payload = {
    mode: state.mode,
    symbol: state.symbol,
    side: state.side,
    order_type: state.orderType,
    quantity: parseFloat(dom.inputQty.value),
    price: isLimit ? parseFloat(dom.inputLimitPrice.value) : null,
  };

  closeConfirmModal();
  showToast('loading', 'Submitting order to trading engine…');

  try {
    const res = await fetch(`${API}/api/order`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      showToast('error', data.error || 'Order placement failed');
    } else {
      const o = data.order;
      const fillMsg = `✓ ${o.side} ${o.executedQty || o.quantity} ${o.symbol} filled at ${o.avgPrice || o.price} USDT (ID: ${o.orderId})`;
      showToast('success', fillMsg);
      loadAccount();
      loadOrders();
    }
  } catch (err) {
    showToast('error', 'Network failure: unable to communicate with backend server.');
  } finally {
    state.submitting = false;
  }
}

function showToast(type, msg) {
  dom.orderResultToast.className = `result-toast visible ${type}`;
  dom.orderResultToast.innerHTML = (type === 'loading' ? '<span class="spinner"></span> ' : '') + escHtml(msg);
}

function hideToast() {
  dom.orderResultToast.className = 'result-toast';
  dom.orderResultToast.innerHTML = '';
}

// ── 8. Portfolio & Account Fetching ──────────────────────────────
async function loadAccount() {
  if (state.mode === 'testnet') {
    dom.metricBalance.textContent = 'Binance Testnet';
    dom.metricEquity.textContent  = '—';
    dom.metricAvailMargin.textContent = '—';
    dom.metricUnrealized.textContent  = '—';
    dom.metricRealized.textContent    = '—';
    return;
  }

  try {
    const res = await fetch(`${API}/api/paper/account`);
    if (res.ok) {
      const data = await res.json();
      dom.metricBalance.textContent = formatMoney(data.balance) + ' USDT';
      dom.metricEquity.textContent  = formatMoney(data.equity) + ' USDT';
      dom.metricAvailMargin.textContent = formatMoney(data.balance) + ' USDT';

      const upnl = Number(data.unrealized_pnl || 0);
      dom.metricUnrealized.textContent = (upnl >= 0 ? '+' : '') + formatMoney(upnl) + ' USDT';
      dom.metricUnrealized.className   = 'metric-val ' + (upnl > 0 ? 'green' : upnl < 0 ? 'red' : '');

      const rpnl = Number(data.realized_pnl || 0);
      dom.metricRealized.textContent = (rpnl >= 0 ? '+' : '') + formatMoney(rpnl) + ' USDT';
      dom.metricRealized.className   = 'metric-val ' + (rpnl > 0 ? 'green' : rpnl < 0 ? 'red' : '');

      renderPositions(data.positions || []);
    }
  } catch (err) {
    console.warn('Failed to load paper account', err);
  }
}

dom.btnResetPortfolio.addEventListener('click', async () => {
  if (!confirm('Are you sure you want to reset your virtual balance?')) return;
  try {
    const res = await fetch(`${API}/api/paper/reset`, { method: 'POST' });
    if (res.ok) {
      loadAccount();
      loadOrders();
      showToast('success', 'Virtual account balance reset successfully');
    }
  } catch (err) {
    alert('Failed to reset account');
  }
});


 // ── 9. Positions & Activity Tabs ────────────────────────────────

dom.tabBtnPositions.addEventListener('click', () =>
  switchActivityTab('positions')
);

dom.tabBtnOrders.addEventListener('click', () =>
  switchActivityTab('orders')
);

dom.tabBtnTrades.addEventListener('click', () =>
  switchActivityTab('trades')
);

dom.btnRefreshTables.addEventListener('click', () => {
  loadAccount();
  loadOrders();
});

function switchActivityTab(tab) {
  state.activeTab = tab;

  dom.tabBtnPositions.className =
    'activity-tab' + (tab === 'positions' ? ' active' : '');

  dom.tabBtnOrders.className =
    'activity-tab' + (tab === 'orders' ? ' active' : '');

  dom.tabBtnTrades.className =
    'activity-tab' + (tab === 'trades' ? ' active' : '');

  dom.viewPositions.classList.toggle('hidden', tab !== 'positions');
  dom.viewOrders.classList.toggle('hidden', tab !== 'orders');
  dom.viewTrades.classList.toggle('hidden', tab !== 'trades');
}


// ── Render Open Positions ────────────────────────────────────────

function renderPositions(positions) {
  dom.countPositions.textContent = String(positions.length);

  if (!positions.length) {
    dom.tbodyPositions.innerHTML = `
      <tr>
        <td colspan="7" class="empty-state">
          No open positions. Place an order to build your portfolio.
        </td>
      </tr>`;
    return;
  }

  dom.tbodyPositions.innerHTML = positions.map(p => {
    const isLong = p.side === 'LONG';
    const upnl = Number(p.unrealized_pnl || 0);

    return `
      <tr>
        <td class="td-symbol">${escHtml(p.symbol)}</td>
        <td>
          <span class="badge-side ${isLong ? 'buy' : 'sell'}">
            ${escHtml(p.side)}
          </span>
        </td>
        <td>${escHtml(String(p.size))}</td>
        <td>${formatMoney(p.entry_price)}</td>
        <td>${formatMoney(p.mark_price)}</td>
        <td>${formatMoney(p.notional)} USDT</td>
        <td class="${upnl > 0 ? 'pnl-positive' : upnl < 0 ? 'pnl-negative' : ''}">
          ${upnl > 0 ? '+' : ''}${formatMoney(upnl)} USDT
        </td>
      </tr>`;
  }).join('');
}


// ── Load Order History from Backend ──────────────────────────────

async function loadOrders() {
  dom.tbodyOrders.innerHTML = `
    <tr>
      <td colspan="9" class="empty-state">Loading order history...</td>
    </tr>`;

  try {
    const response = await fetch(
      `${API}/api/orders?mode=${encodeURIComponent(state.mode)}`,
      { cache: 'no-store' }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Unable to load order history.');
    }

    const orders = Array.isArray(data.orders) ? data.orders : [];
    renderOrdersAndTrades(orders);

  } catch (error) {
    console.error('Order history error:', error);

    dom.tbodyOrders.innerHTML = `
      <tr>
        <td colspan="9" class="empty-state">
          ${escHtml(error.message || 'Could not load order history.')}
        </td>
      </tr>`;

    dom.tbodyTrades.innerHTML = `
      <tr>
        <td colspan="7" class="empty-state">
          Trade history is unavailable.
        </td>
      </tr>`;

    dom.countOrders.textContent = '0';
  }
}


// ── Normalize Order Fields ───────────────────────────────────────

function renderOrdersAndTrades(orders) {
  dom.countOrders.textContent = String(orders.length);

  if (!orders.length) {
    dom.tbodyOrders.innerHTML = `
      <tr>
        <td colspan="9" class="empty-state">
          No orders placed yet in ${escHtml(state.mode)} mode.
        </td>
      </tr>`;

    dom.tbodyTrades.innerHTML = `
      <tr>
        <td colspan="7" class="empty-state">
          No filled trades recorded yet.
        </td>
      </tr>`;

    return;
  }

  const normalized = orders.map(order => {
    const status = String(
      order.status ||
      (state.mode === 'paper' ? 'FILLED' : 'UNKNOWN')
    ).toUpperCase();

    const avgPrice = Number(
      order.avgPrice ?? order.avg_price ?? 0
    );

    const orderPrice = Number(order.price ?? 0);

    return {
      ...order,
      _id: order.orderId ?? order.exchange_order_id ?? order.id ?? '—',
      _time: order.timestamp ?? order.created_at ?? order.time ?? null,
      _quantity: order.origQty ?? order.quantity ?? order.qty ?? '—',
      _executed: Number(
        order.executedQty ?? order.executed_quantity ?? 0
      ),
      _price: avgPrice > 0 ? avgPrice : orderPrice,
      _type: order.order_type ?? order.type ?? 'MARKET',
      _status: status
    };
  });

  // Render Order History
  dom.tbodyOrders.innerHTML = normalized.map(order => {
    const time = order._time
      ? new Date(order._time).toLocaleString()
      : '—';

    const isBuy = String(order.side).toUpperCase() === 'BUY';

    const statusClass = order._status === 'FILLED'
      ? 'filled'
      : ['NEW', 'PARTIALLY_FILLED'].includes(order._status)
        ? 'new'
        : 'closed';

    const priceText = order._price > 0
      ? formatMoney(order._price)
      : '—';

    const execution = state.mode === 'paper'
      ? 'SIMULATED'
      : 'TESTNET';

    return `
      <tr>
        <td>${escHtml(time)}</td>
        <td>${escHtml(String(order._id))}</td>
        <td class="td-symbol">${escHtml(order.symbol || '—')}</td>
        <td>
          <span class="badge-side ${isBuy ? 'buy' : 'sell'}">
            ${escHtml(order.side || '—')}
          </span>
        </td>
        <td>${escHtml(order._type)}</td>
        <td>${escHtml(String(order._quantity))}</td>
        <td>${priceText}</td>
        <td>
          <span class="badge-status ${statusClass}">
            ${escHtml(order._status)}
          </span>
        </td>
        <td>
          <span class="badge-simulated-tag ${state.mode === 'testnet' ? 'testnet' : ''}">
            ${execution}
          </span>
        </td>
      </tr>`;
  }).join('');

  // Trade History shows orders marked FILLED.
  const trades = normalized.filter(
    order => order._status === 'FILLED'
  );

  if (!trades.length) {
    dom.tbodyTrades.innerHTML = `
      <tr>
        <td colspan="7" class="empty-state">
          No filled trades recorded yet.
        </td>
      </tr>`;
    return;
  }

  dom.tbodyTrades.innerHTML = trades.map(trade => {
    const time = trade._time
      ? new Date(trade._time).toLocaleString()
      : '—';

    const isBuy = String(trade.side).toUpperCase() === 'BUY';

    const executedQty = trade._executed > 0
      ? trade._executed
      : trade._quantity;

    const fillPrice = trade._price > 0
      ? `${formatMoney(trade._price)} USDT`
      : '—';

    return `
      <tr>
        <td>${escHtml(time)}</td>
        <td class="td-symbol">${escHtml(trade.symbol || '—')}</td>
        <td>
          <span class="badge-side ${isBuy ? 'buy' : 'sell'}">
            ${escHtml(trade.side || '—')}
          </span>
        </td>
        <td>${escHtml(String(executedQty))}</td>
        <td>${escHtml(fillPrice)}</td>
        <td>—</td>
        <td>
          <span class="badge-simulated-tag ${state.mode === 'testnet' ? 'testnet' : ''}">
            ${state.mode === 'testnet' ? 'TESTNET' : 'SIMULATED'}
          </span>
        </td>
      </tr>`;
  }).join('');
}


// ── Helpers ──────────────────────────────────────────────────────
function formatMoney(val) {
  const n = Number(val);
  if (isNaN(n)) return '0.00';
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

async function checkAuthUser() {
  try {
    const res = await fetch(`${API}/api/auth/me`);
    const data = await res.json();
    if (data.authenticated && data.user) {
      if (dom.linkLogin) dom.linkLogin.classList.add('hidden');
      if (dom.userProfileBadge) dom.userProfileBadge.classList.remove('hidden');
      if (dom.btnLogout) dom.btnLogout.classList.remove('hidden');
      if (dom.navUserName) dom.navUserName.textContent = data.user.username;
      if (dom.navUserAvatar) dom.navUserAvatar.textContent = data.user.username.charAt(0).toUpperCase();
    } else {
      if (dom.linkLogin) dom.linkLogin.classList.remove('hidden');
      if (dom.userProfileBadge) dom.userProfileBadge.classList.add('hidden');
      if (dom.btnLogout) dom.btnLogout.classList.add('hidden');
    }
  } catch (err) {
    console.debug('Auth check skipped:', err);
  }
}

async function handleLogout() {
  if (!confirm('Are you sure you want to log out of the trading terminal?')) {
    return;
  }

  try {
    const res = await fetch(`${API}/api/logout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await res.json().catch(() => ({}));
    sessionStorage.clear();
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_session');
    window.location.href = data.redirect_url || '/login';
  } catch (err) {
    console.error('Logout error:', err);
    sessionStorage.clear();
    window.location.href = '/login';
  }
}

if (dom.btnLogout) {
  dom.btnLogout.addEventListener('click', handleLogout);
}

(function init() {
  checkAuthUser();
  setMode('paper');
  fetchMarketInfo();
  loadHistoricalCandlesAndConnectStream();
  loadAccount();
  loadOrders();

  setInterval(() => {
    fetchMarketInfo();
    if (state.mode === 'paper') loadAccount();
  }, 10_000);
})();