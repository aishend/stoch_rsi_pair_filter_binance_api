"""
Dashboard Streamlit para teste - Mostra 5 pares com Stoch RSI em todos os timeframes
"""

import streamlit as st
import pandas as pd
from src.api.binance import BinanceClient
from src.indicators import calculate_stoch_rsi
from config import TIMEFRAMES

st.set_page_config(page_title="Stoch RSI Debug", layout="wide")

st.title("🧪 Debug Dashboard - Stochastic RSI")
st.markdown("Teste rápido com 5 pares principais")

# Inicializar cliente
@st.cache_resource
def init_client():
    return BinanceClient()

client = init_client()

# Botão para executar cálculo
if st.button("▶️ Processar 5 Pares (Teste)", key="process"):
    st.info("Buscando dados...")
    
    pairs = client.get_trading_pairs()
    symbols = [p['symbol'] for p in pairs[:5]]
    
    st.write(f"📊 Processando: {', '.join(symbols)}")
    
    # Placeholder para progresso
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = {}
    total_steps = len(TIMEFRAMES) * len(symbols)
    step = 0
    
    for timeframe in TIMEFRAMES:
        status_text.write(f"⏳ Processando timeframe: {timeframe}")
        results[timeframe] = {}
        
        for symbol in symbols:
            # Buscar dados
            closes = client.get_klines(symbol, timeframe, 100)
            
            if closes and len(closes) > 0:
                # Calcular Stoch RSI
                stoch_rsi_values = calculate_stoch_rsi(closes)
                current = stoch_rsi_values[-1] if stoch_rsi_values else None
                
                if current:
                    result = {
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'total_candles': len(closes),
                        'k': round(current.k, 4) if current.k else None,
                        'd': round(current.d, 4) if current.d else None,
                        'rsi': round(current.rsi, 4) if current.rsi else None
                    }
                else:
                    result = {'symbol': symbol, 'error': 'Sem dados válidos'}
            else:
                result = {'symbol': symbol, 'error': 'Sem dados'}
            
            results[timeframe][symbol] = result
            step += 1
            progress_bar.progress(step / total_steps)
    
    st.success("✓ Processamento concluído!")
    
    # Exibir dados por timeframe
    for timeframe in TIMEFRAMES:
        st.subheader(f"📈 Timeframe: {timeframe}")
        
        data = []
        for symbol in symbols:
            result = results[timeframe][symbol]
            if 'error' not in result:
                data.append({
                    'Símbolo': result['symbol'],
                    '%K': result['k'],
                    '%D': result['d'],
                    'RSI': result['rsi'],
                    'Velas': result['total_candles']
                })
        
        if data:
            df = pd.DataFrame(data)
            
            # Colorir valores
            def color_k_d(val):
                if val is None:
                    return 'background-color: #cccccc'
                if val < 20:
                    return 'background-color: #90EE90'  # Verde (oversold)
                if val > 80:
                    return 'background-color: #FFB6C1'  # Vermelho (overbought)
                return ''
            
            styled_df = df.style.map(color_k_d, subset=['%K', '%D'])
            st.dataframe(styled_df, width='stretch')
        else:
            st.warning("Sem dados disponíveis")
