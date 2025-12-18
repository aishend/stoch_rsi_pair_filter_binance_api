# 📊 Stochastic RSI Dashboard

Dashboard em tempo real para análise de Stochastic RSI de pares cripto na Binance. Otimizado para Raspberry Pi.

## 🎯 Características

- ✅ **Atualização contínua em ciclo** - Processa pares sequencialmente, um de cada vez
- ✅ **Filtros inteligentes** - Status (Oversold/Overbought/Both) + Timeframes (15m, 1h, 4h, 1d)
- ✅ **Ordenação por volume** - Pares organizados por volume de 24h descrescente
- ✅ **Auto-refresh** - Página recarrega a cada 1 minuto
- ✅ **Banco de dados SQLite** - Armazenamento persistente e eficiente
- ✅ **RPi Optimizado** - Uso mínimo de recursos, processamento sequencial

## 🚀 Instalação Rápida (Raspberry Pi)

```bash
chmod +x start_rpi.sh
./start_rpi.sh
```

Dashboard: `http://192.168.1.XXX:8000`

## 📊 Como funciona

Sistema processa dados **sequencialmente** (um par de cada vez):

1. **Loop contínuo** (`update_loop.py`)
2. **Para cada timeframe** (15m, 1h, 4h, 1d)
3. **Para cada par** - busca, processa, salva
4. **Espera 5 minutos** → próximo ciclo

Sem paralelismo = RPi não sobrecarrega ✓

## 📁 Arquivos Principais

| Arquivo | Função |
|---------|--------|
| `start_rpi.sh` | 🚀 Inicialização automática |
| `update_loop.py` | 🔄 Loop de atualização contínua |
| `api_server.py` | 🌐 API Flask + Cache |
| `main.py` | 📊 Script único (sem ciclo) |
| `config.py` | ⚙️ Configurações |

## 🔧 Controle

```bash
# Ver logs
tail -f logs/api_server.log
tail -f logs/update_loop.log

# Parar
ps aux | grep python
kill PID_API PID_LOOP
```

## ⚙️ Configuração

**Intervalo de ciclo** (`update_loop.py` ~linha 85):
```python
time.sleep(300)  # 5 minutos (em segundos)
```

**Timeframes** (`config.py`):
```python
TIMEFRAMES = ['15m', '1h', '4h', '1d']
```

**Refresh página** (`ui/app.js` ~linha 65):
```javascript
setInterval(() => location.reload(), 60000);  // 1 minuto
```

## 🎨 Filtros

- **Status**: Oversold (padrão) / Overbought / Both
- **Timeframes**: 1h, 4h (padrão) - múltipla seleção (min. 1)
- **Match**: "all" = deve estar em TODOS os timeframes selecionados
- **Ordenação**: Por volume descrescente

## 📊 Dados Armazenados

```
Símbolo + Volume 24h + Por timeframe:
  - %K (Estocástico K)
  - %D (Estocástico D)
  - RSI (Índice Força Relativa)
```

## 📝 Monitoramento

```bash
# Saúde do sistema
tail -5 logs/*.log

# Registros no banco
sqlite3 data/stoch_rsi.db "SELECT COUNT(*) FROM stoch_rsi_data;"

# Último update
sqlite3 data/stoch_rsi.db "SELECT timestamp FROM stoch_rsi_data ORDER BY timestamp DESC LIMIT 1;"
```

## 🐛 Troubleshooting

| Problema | Solução |
|----------|---------|
| Connection refused | `ps aux \| grep api_server` → reiniciar |
| Port 8000 in use | `sudo lsof -i :8000` → `kill -9 PID` |
| RPi lento | Aumentar intervalo em `update_loop.py` |

## 📈 Performance Esperada

| Hardware | Ciclo Completo* |
|----------|-----------------|
| RPi 3 | ~8-12 min |
| RPi 4 | ~4-6 min |

*5 pares × 4 timeframes, com 0.1s delay entre pares

## 📄 Licença

MIT

---

**Monitoramento Stochastic RSI em tempo real com recursos limitados** 🚀
