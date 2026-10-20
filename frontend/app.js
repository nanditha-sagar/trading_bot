/* ================================================================
   app.js — Binance Futures Testnet Trading Bot UI
   Pure vanilla JS. No libraries, no build step.
   ================================================================ */

'use strict';

// ── API base (same origin — Flask serves both) ───────────────────
const API = '';

// ── State ────────────────────────────────────────────────────────
const state = {
  side: 'BUY',
  submitting: false,
};

// ── DOM refs ─────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const dom = {
  statusDot:    $('status-dot'),
  statusText:   $('status-text'),
  // Form
  fSymbol:      $('f-symbol'),
  fOrderType:   $('f-order-type'),
  fQty:         $('f-qty'),
  fPrice:       $('f-price'),
  fPriceGroup:  $('f-price-group'),
  btnBuy:       $('btn-buy'),
  btnSell:      $('btn-sell'),
  btnSubmit:    $('btn-submit'),
  // Errors
  errSymbol:    $('err-symbol'),
  errQty:       $('err-qty'),
  errPrice:     $('err-price'),
  // Summary
  summary:      $('order-summary'),
  sumSide:      $('sum-side'),
  sumSymbol:    $('sum-symbol'),
  sumType:      $('sum-type'),
  sumQty:       $('sum-qty'),
  sumPrice:     $('sum-price'),
  sumPriceRow:  $('sum-price-row'),
  // Result banner
  resultBanner: $('result-banner'),
  // Modal
  modal:        $('confirm-modal'),
  mSide:        $('m-side'),
  mSymbol:      $('m-symbol'),
  mType:        $('m-type'),
  mQty:         $('m-qty'),
  mPrice:       $('m-price'),
  mPriceRow:    $('m-price-row'),
  mCancel:      $('m-cancel'),
  mConfirm:     $('m-confirm'),
  // Orders table
  ordersBody:   $('orders-body'),
};

// ── Side toggle ──────────────────────────────────────────────────
dom.btnBuy.addEventListener('click', () => setSide('BUY'));
dom.btnSell.addEventListener('click', () => setSide('SELL'));

function setSide(side) {
  state.side = side;
  dom.btnBuy.className  = 'side-btn' + (side === 'BUY'  ? ' active-buy'  : '');
  dom.btnSell.className = 'side-btn' + (side === 'SELL' ? ' active-sell' : '');
  dom.btnSubmit.className = 'btn-submit ' + (side === 'BUY' ? 'buy-mode' : 'sell-mode');
  dom.btnSubmit.textContent = side === 'BUY' ? 'Buy / Long' : 'Sell / Short';
  updateSummary();
}

// ── Order type toggle — show/hide limit price ────────────────────
dom.fOrderType.addEventListener('change', () => {
  const isLimit = dom.fOrderType.value === 'LIMIT';
  dom.fPriceGroup.classList.toggle('hidden', !isLimit);
  if (!isLimit) {
    dom.fPrice.value = '';
    clearFieldError(dom.fPrice, dom.errPrice);
  }
  updateSummary();
});

// ── Live summary update ──────────────────────────────────────────
[dom.fSymbol, dom.fQty, dom.fPrice, dom.fOrderType].forEach(el => {
  el.addEventListener('input', updateSummary);
});

function updateSummary() {
  const symbol = dom.fSymbol.value.trim().toUpperCase();
  const qty    = dom.fQty.value.trim();
  const price  = dom.fPrice.value.trim();
  const type   = dom.fOrderType.value;

  if (!symbol || !qty || parseFloat(qty) <= 0) {
    dom.summary.classList.remove('visible');
    return;
  }
  if (type === 'LIMIT' && (!price || parseFloat(price) <= 0)) {
    dom.summary.classList.remove('visible');
    return;
  }

  dom.summary.classList.add('visible');
  dom.sumSide.textContent   = state.side;
  dom.sumSide.className     = 'summary-val ' + state.side.toLowerCase();
  dom.sumSymbol.textContent = symbol;
  dom.sumType.textContent   = type;
  dom.sumQty.textContent    = qty;

  if (type === 'LIMIT' && price) {
    dom.sumPriceRow.classList.remove('hidden');
    dom.sumPrice.textContent = parseFloat(price).toLocaleString('en-US', { minimumFractionDigits: 2 }) + ' USDT';
  } else {
    dom.sumPriceRow.classList.add('hidden');
  }

  // Update submit button label
  const sideLabel = state.side === 'BUY' ? 'Buy / Long' : 'Sell / Short';
  dom.btnSubmit.textContent = `${sideLabel}  ${symbol}`;
}

// ── Validation ───────────────────────────────────────────────────
function setFieldError(field, errEl, msg) {
  field.classList.add('error-field');
  errEl.textContent = msg;
  errEl.classList.add('visible');
}

function clearFieldError(field, errEl) {
  field.classList.remove('error-field');
  errEl.classList.remove('visible');
}

function validateForm() {
  let valid = true;

  const symbol = dom.fSymbol.value.trim();
  if (!symbol) {
    setFieldError(dom.fSymbol, dom.errSymbol, 'Symbol is required (e.g. BTCUSDT)');
    valid = false;
  } else {
    clearFieldError(dom.fSymbol, dom.errSymbol);
  }

  const qty = parseFloat(dom.fQty.value);
  if (!dom.fQty.value.trim() || isNaN(qty) || qty <= 0) {
    setFieldError(dom.fQty, dom.errQty, 'Enter a positive quantity');
    valid = false;
  } else {
    clearFieldError(dom.fQty, dom.errQty);
  }

  if (dom.fOrderType.value === 'LIMIT') {
    const price = parseFloat(dom.fPrice.value);
    if (!dom.fPrice.value.trim() || isNaN(price) || price <= 0) {
      setFieldError(dom.fPrice, dom.errPrice, 'Enter a positive limit price');
      valid = false;
    } else {
      clearFieldError(dom.fPrice, dom.errPrice);
    }
  }

  return valid;
}

// ── Show confirmation modal ──────────────────────────────────────
dom.btnSubmit.addEventListener('click', () => {
  hideBanner();
  if (!validateForm()) return;
  openModal();
});

function openModal() {
  const symbol = dom.fSymbol.value.trim().toUpperCase();
  const type   = dom.fOrderType.value;
  const price  = dom.fPrice.value.trim();

  dom.mSide.textContent   = state.side;
  dom.mSide.className     = 'modal-val ' + state.side.toLowerCase();
  dom.mSymbol.textContent = symbol;
  dom.mType.textContent   = type;
  dom.mQty.textContent    = dom.fQty.value.trim();
  dom.mConfirm.className  = 'btn-confirm ' + state.side.toLowerCase();

  if (type === 'LIMIT' && price) {
    dom.mPriceRow.classList.remove('hidden');
    dom.mPrice.textContent = parseFloat(price).toLocaleString('en-US', { minimumFractionDigits: 2 }) + ' USDT';
  } else {
    dom.mPriceRow.classList.add('hidden');
  }

  dom.modal.classList.add('visible');
}

dom.mCancel.addEventListener('click', closeModal);
dom.modal.addEventListener('click', e => { if (e.target === dom.modal) closeModal(); });

function closeModal() {
  dom.modal.classList.remove('visible');
  dom.mConfirm.disabled = false;
  dom.mConfirm.textContent = 'Place Order';
}

// ── Submit order ─────────────────────────────────────────────────
dom.mConfirm.addEventListener('click', submitOrder);

async function submitOrder() {
  if (state.submitting) return;
  state.submitting = true;
  dom.mConfirm.disabled = true;
  dom.mConfirm.innerHTML = '<span class="spinner"></span> Placing…';

  const symbol    = dom.fSymbol.value.trim().toUpperCase();
  const type      = dom.fOrderType.value;
  const qty       = parseFloat(dom.fQty.value);
  const priceRaw  = dom.fPrice.value.trim();
  const price     = type === 'LIMIT' && priceRaw ? parseFloat(priceRaw) : null;

  const payload = {
    symbol,
    side:       state.side,
    order_type: type,
    quantity:   qty,
    price,
  };

  closeModal();
  showBanner('loading', '');

  try {
    const res  = await fetch(`${API}/api/order`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      showBanner('error', data.error || `HTTP ${res.status}`);
    } else {
      const o = data.order;
      showBanner('success', o);
      loadOrders();
    }
  } catch (err) {
    showBanner('error', 'Network error — is the server running?');
  } finally {
    state.submitting = false;
  }
}

// ── Result banner ────────────────────────────────────────────────
function hideBanner() {
  dom.resultBanner.className = 'result-banner';
  dom.resultBanner.innerHTML = '';
}

function showBanner(type, payload) {
  dom.resultBanner.className = 'result-banner visible';

  if (type === 'loading') {
    dom.resultBanner.classList.add('loading-banner');
    dom.resultBanner.innerHTML = '<span class="spinner"></span> Placing order on Binance Testnet…';
    return;
  }

  if (type === 'error') {
    dom.resultBanner.classList.add('error-banner');
    dom.resultBanner.innerHTML = `<div class="result-title">Order Failed</div>${escHtml(payload)}`;
    return;
  }

  // success
  dom.resultBanner.classList.add('success');
  const avgPrice = payload.avgPrice || payload.price || '—';
  dom.resultBanner.innerHTML = `
    <div class="result-title">✓ Order Placed</div>
    ${resultRow('Order ID',       payload.orderId       || '—')}
    ${resultRow('Status',         payload.status        || '—')}
    ${resultRow('Executed Qty',   payload.executedQty   || '—')}
    ${resultRow('Avg Price',      avgPrice)}
    ${resultRow('Client Order ID',payload.clientOrderId || '—')}
  `;
}

function resultRow(key, val) {
  return `<div class="result-row"><span class="result-key">${escHtml(key)}</span><span class="result-val">${escHtml(String(val))}</span></div>`;
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Orders table ─────────────────────────────────────────────────
async function loadOrders() {
  try {
    const res  = await fetch(`${API}/api/orders`);
    const data = await res.json();
    renderOrders(data.orders || []);
  } catch (_) {
    dom.ordersBody.innerHTML = `<tr><td colspan="8" class="table-empty">Could not load order history.</td></tr>`;
  }
}

function renderOrders(orders) {
  if (!orders.length) {
    dom.ordersBody.innerHTML = `<tr><td colspan="8" class="table-empty">No orders yet. Place your first order above.</td></tr>`;
    return;
  }

  dom.ordersBody.innerHTML = orders.map(o => {
    const time    = new Date(o.timestamp).toLocaleTimeString('en-US', { hour12: false });
    const sideClass = o.side === 'BUY' ? 'cell-buy' : 'cell-sell';
    const status  = (o.status || '').toUpperCase();
    const pillClass = status === 'FILLED' ? 'filled' : status === 'NEW' ? 'new' : status === 'CANCELED' ? 'canceled' : 'other';
    const avgPrice = o.avgPrice || o.price || '—';
    const price    = avgPrice !== '—' ? parseFloat(avgPrice).toLocaleString('en-US', { minimumFractionDigits: 2 }) : '—';

    return `<tr>
      <td>${escHtml(time)}</td>
      <td class="cell-symbol">${escHtml(o.symbol || '—')}</td>
      <td class="${sideClass}">${escHtml(o.side || '—')}</td>
      <td class="cell-type">${escHtml((o.order_type || o.type || '—').toLowerCase())}</td>
      <td>${escHtml(String(o.executedQty || o.quantity || '—'))}</td>
      <td>${escHtml(price)}</td>
      <td><span class="status-pill ${pillClass}">${escHtml(status || '—')}</span></td>
      <td>${escHtml(String(o.orderId || '—'))}</td>
    </tr>`;
  }).join('');
}

// ── Connection check ─────────────────────────────────────────────
async function checkConnection() {
  dom.statusDot.className  = 'status-dot checking';
  dom.statusText.textContent = 'Connecting…';
  try {
    const res = await fetch(`${API}/api/orders`, { signal: AbortSignal.timeout(4000) });
    if (res.ok) {
      dom.statusDot.className   = 'status-dot connected';
      dom.statusText.textContent = 'testnet.binancefuture.com';
    } else {
      throw new Error('non-ok');
    }
  } catch (_) {
    dom.statusDot.className   = 'status-dot error';
    dom.statusText.textContent = 'Server unreachable';
  }
}

// ── Init ─────────────────────────────────────────────────────────
(function init() {
  setSide('BUY');
  checkConnection();
  loadOrders();
  // Refresh order list every 30 s
  setInterval(loadOrders, 30_000);
})();
