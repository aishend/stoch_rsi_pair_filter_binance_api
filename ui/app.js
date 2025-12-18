const API = 'http://localhost:8000';

let state = {
  symbols: [],
  timeframes: [],
  tableData: {},
  lastUpdate: null,
  autoRefreshInterval: null,
  filtered: false
};

document.addEventListener('DOMContentLoaded', init);

async function init() {
  try {
    // Verificar se API está disponível
    await fetch(`${API}/health`);
    
    // Aplicar filtro padrão (oversold + 1h,4h) automaticamente
    await applyFilter();
    
    startAutoRefresh();
  } catch (err) {
    console.error('Erro de conexão:', err);
  }
}

async function loadTableData() {
  try {
    setStatus('Carregando...', false);
    
    const res = await fetch(`${API}/api/table`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    
    const data = await res.json();
    
    // Verificar se há erro na resposta
    if (data.error) {
      console.warn('Aviso:', data.error);
      // Usar dados vazios em vez de falhar completamente
      state.timeframes = data.timeframes || ['15m', '1h', '4h', '1d'];
      state.tableData = {};
      state.symbols = [];
    } else {
      // Estruturar dados em formato de cache
      state.timeframes = data.timeframes || [];
      state.tableData = {};
      state.lastUpdate = data.timestamp;
      
      if (data.rows && data.rows.length > 0) {
        for (const row of data.rows) {
          state.tableData[row.symbol] = row.timeframes;
        }
        state.symbols = data.rows.map(r => r.symbol);
      }
    }
    
    renderTable();
    updateStats();
    setStatus('Pronto', true);
    
  } catch (err) {
    console.error('Erro ao carregar tabela:', err);
    setStatus('Erro ao carregar', false);
  }
}

function renderTable() {
  const tbody = document.getElementById('tableBody');
  tbody.innerHTML = '';
  
  if (state.symbols.length === 0) {
    tbody.innerHTML = '<tr class="loading-row"><td colspan="5">Nenhum símbolo encontrado</td></tr>';
    return;
  }
  
  // Usar DocumentFragment para melhor performance
  const fragment = document.createDocumentFragment();
  
  state.symbols.forEach(symbol => {
    const tr = document.createElement('tr');
    tr.className = 'data-row';
    tr.dataset.symbol = symbol;
    
    // Coluna de símbolo
    const symbolCell = document.createElement('td');
    symbolCell.className = 'symbol-col';
    symbolCell.textContent = symbol;
    tr.appendChild(symbolCell);
    
    // Colunas de timeframe
    state.timeframes.forEach(timeframe => {
      const cell = document.createElement('td');
      cell.className = 'timeframe-col';
      
      const data = state.tableData[symbol][timeframe];
      if (data) {
        const k = data.k || 0;
        const status = data.status || 'neutral';
        
        cell.className += ` status-${status}`;
        cell.innerHTML = `<div class="cell-content"><span class="value">${k.toFixed(2)}</span></div>`;
      } else {
        cell.textContent = '-';
        cell.className += ' status-neutral';
      }
      
      tr.appendChild(cell);
    });
    
    fragment.appendChild(tr);
  });
  
  tbody.appendChild(fragment);
}

function updateStats() {
  let oversoldCount = 0, overboughtCount = 0, neutralCount = 0;
  let latestTimestamp = null;
  
  // Buscar timestamp do banco mesmo se não há pares filtrados
  if (state.lastUpdate) {
    latestTimestamp = new Date(state.lastUpdate);
  }
  
  state.symbols.forEach(symbol => {
    state.timeframes.forEach(timeframe => {
      const data = state.tableData[symbol][timeframe];
      if (data) {
        if (data.status === 'oversold') oversoldCount++;
        else if (data.status === 'overbought') overboughtCount++;
        else neutralCount++;
        
        // Guardar timestamp mais recente
        if (data.timestamp) {
          const ts = new Date(data.timestamp);
          if (!latestTimestamp || ts > latestTimestamp) {
            latestTimestamp = ts;
          }
        }
      }
    });
  });
  
  document.getElementById('totalPairs').textContent = state.symbols.length;
  document.getElementById('oversoldCount').textContent = oversoldCount;
  document.getElementById('overboughtCount').textContent = overboughtCount;
  document.getElementById('neutralCount').textContent = neutralCount;
  
  // Sempre atualizar timestamp (mesmo com 0 pares)
  if (latestTimestamp) {
    document.getElementById('lastUpdate').textContent = `Atualizado em ${latestTimestamp.toLocaleTimeString('pt-BR')}`;
  }
}

function setStatus(msg, ready) {
  // Status removido, sem necessidade
}

async function applyFilter() {
  try {
    // Pegar status ativo (apenas um, radio button)
    const activeStatus = document.querySelector('.filter-radio.active');
    const status = activeStatus ? activeStatus.dataset.status : 'oversold';
    
    // Pegar timeframes ativos
    const activeTimeframes = Array.from(document.querySelectorAll('.filter-btn[data-timeframe].active'))
      .map(el => el.dataset.timeframe)
      .join(',');
    
    // Usar "all" para match simultâneo
    const url = `${API}/api/filter?status=${status}&timeframes=${activeTimeframes}&match=all`;
    const res = await fetch(url);
    const data = await res.json();
    
    // Atualizar estado com dados filtrados
    state.timeframes = data.timeframes;
    state.tableData = {};
    state.lastUpdate = data.timestamp;
    state.filtered = true;
    
    if (data.rows && data.rows.length > 0) {
      for (const row of data.rows) {
        state.tableData[row.symbol] = row.timeframes;
      }
      state.symbols = data.rows.map(r => r.symbol);
    } else {
      state.symbols = [];
    }
    
    renderTable();
    updateStats();
    
  } catch (err) {
    console.error('Erro ao filtrar:', err);
  }
}

function startAutoRefresh() {
  // Recarregar página a cada 1 minuto
  setInterval(() => {
    location.reload();
  }, 60000);
}

function clearFilter() {
  // Reset status para oversold
  document.querySelectorAll('.filter-radio').forEach(el => el.classList.remove('active'));
  document.querySelector('.filter-radio[data-status="oversold"]').classList.add('active');
  
  // Reset timeframes para 1h e 4h
  document.querySelectorAll('.filter-btn[data-timeframe]').forEach(el => el.classList.remove('active'));
  document.querySelector('.filter-btn[data-timeframe="1h"]').classList.add('active');
  document.querySelector('.filter-btn[data-timeframe="4h"]').classList.add('active');
  
  state.filtered = false;
  applyFilter();
}

function setStatus(msg, ready) {
  const status = document.getElementById('status');
  status.textContent = msg;
  status.className = ready ? 'status ready' : 'status error';
}

// Event listeners
document.getElementById('resetBtn').addEventListener('click', clearFilter);

// Filtro - radio status (apenas um)
document.querySelectorAll('.filter-radio[data-status]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-radio[data-status]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    applyFilter();
  });
});

// Filtro - toggle timeframe (múltiplos)
document.querySelectorAll('.filter-btn[data-timeframe]').forEach(btn => {
  btn.addEventListener('click', () => {
    // Verificar se é o último ativo
    const activeCount = document.querySelectorAll('.filter-btn[data-timeframe].active').length;
    
    // Se é o último ativo, não deixar desselecionar
    if (btn.classList.contains('active') && activeCount === 1) {
      return;
    }
    
    btn.classList.toggle('active');
    applyFilter();
  });
});

document.addEventListener('visibilitychange', () => {
  if (!document.hidden && state.symbols.length > 0) {
    applyFilter(); // Reaplicar filtro quando aba volta ao foco
  }
});
