"""
API Server otimizado para Raspberry Pi 3
Retorna dados em formato tabular para display rápido
"""

from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
import json
import threading
import time
import os
import sys
from datetime import datetime
from config import TIMEFRAMES
from src.api.binance import BinanceClient
from src.core.calculator import StochRSICalculatorCore
from src.db.database import StochRSIDatabase

app = Flask(__name__, static_folder='ui', static_url_path='')
CORS(app)

# Lock para thread-safety com SQLite
db_lock = threading.Lock()

# Cache em memória para reduzir I/O no Raspberry Pi
cache = {
    'data': {},
    'timestamp': 0,
    'refresh_interval': 60  # 1 minuto (antes era 300 = 5 minutos)
}

# Instâncias globais
db = None
calculator = None
client = None


def init_backend():
    """Inicializa o backend"""
    global db, calculator, client
    try:
        db = StochRSIDatabase()
        client = BinanceClient()
        calculator = StochRSICalculatorCore(client, db)
        print("✓ Backend inicializado com sucesso")
    except Exception as e:
        print(f"✗ Erro ao inicializar backend: {e}")


def get_symbol_volume(symbol: str) -> float:
    """Obtém volume de um símbolo do banco de dados"""
    if not db:
        return 0
    try:
        with db_lock:
            cursor = db.connection.cursor()
            cursor.execute('SELECT volume FROM symbols WHERE symbol = ?', (symbol,))
            result = cursor.fetchone()
            return float(result[0]) if result and result[0] else 0
    except Exception:
        return 0


def sort_rows_by_volume(rows: list) -> list:
    """Ordena linhas de resultado por volume decrescente"""
    return sorted(rows, key=lambda r: get_symbol_volume(r.get('symbol', '')), reverse=True)


def refresh_cache(symbols: list):
    """
    Atualiza cache com dados dos últimos valores para todos os timeframes.
    Rodado em thread para não bloquear as requisições.
    """
    try:
        new_data = {}
        
        for symbol in symbols:
            new_data[symbol] = {}
            
            for timeframe in TIMEFRAMES:
                try:
                    # Usar lock para acesso thread-safe ao banco
                    with db_lock:
                        last_value = db.get_latest_stoch_rsi(symbol, timeframe)
                    
                    if last_value and last_value.get('k') is not None:
                        k_val = last_value.get('k', 0)
                        new_data[symbol][timeframe] = {
                            'k': round(float(k_val), 4) if k_val else 0,
                            'd': round(float(last_value.get('d', 0)), 4) if last_value.get('d') else 0,
                            'rsi': round(float(last_value.get('rsi', 0)), 4) if last_value.get('rsi') else 0,
                            'timestamp': str(last_value.get('timestamp', '')),
                            'status': get_status(float(k_val) if k_val else 0)
                        }
                    else:
                        new_data[symbol][timeframe] = None
                        
                except Exception as e:
                    print(f"Erro ao carregar {symbol} {timeframe}: {e}")
                    new_data[symbol][timeframe] = None
        
        cache['data'] = new_data
        cache['timestamp'] = time.time()
        print(f"✓ Cache atualizado em {datetime.now().strftime('%H:%M:%S')}")
        
    except Exception as e:
        print(f"✗ Erro ao atualizar cache: {e}")


def get_status(k_value):
    """Determina status baseado no valor de %K"""
    if k_value < 20:
        return 'oversold'
    elif k_value > 80:
        return 'overbought'
    else:
        return 'neutral'


def background_refresh_thread(symbols: list):
    """Thread que atualiza cache periodicamente"""
    while True:
        try:
            refresh_cache(symbols)
            time.sleep(cache['refresh_interval'])
        except Exception as e:
            print(f"Erro em background thread: {e}")
            time.sleep(60)


@app.route('/health', methods=['GET'])
def health():
    """Endpoint de saúde"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'cache_age': round(time.time() - cache['timestamp'], 1)
    })


@app.route('/', methods=['GET'])
def index():
    """Servir o dashboard HTML"""
    return send_from_directory('ui', 'index.html')


@app.route('/<path:path>', methods=['GET'])
def static_files(path):
    """Servir arquivos estáticos (CSS, JS)"""
    return send_from_directory('ui', path)


@app.route('/api/symbols', methods=['GET'])
def get_symbols():
    """Retorna lista de todos os pares disponíveis"""
    try:
        # Buscar pares ativos do banco com lock
        with db_lock:
            symbols = db.get_all_symbols()
        return jsonify({
            'symbols': symbols,
            'count': len(symbols)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/timeframes', methods=['GET'])
def get_timeframes():
    """Retorna lista de timeframes configurados"""
    return jsonify({
        'timeframes': TIMEFRAMES
    })


@app.route('/api/table', methods=['GET'])
def get_table():
    """
    Retorna tabela completa com todos os pares e timeframes.
    Formato otimizado para display rápido.
    """
    try:
        # Verificar se há dados em cache
        if not cache['data']:
            return jsonify({
                'error': 'Cache vazio. Execute python main.py primeiro',
                'timeframes': TIMEFRAMES,
                'rows': []
            }), 200
        
        symbols = request.args.get('symbols', '').split(',') if request.args.get('symbols') else None
        
        if not symbols or symbols == ['']:
            # Usar lock para acesso seguro ao banco
            with db_lock:
                symbols = db.get_all_symbols_by_volume() if db else []
        else:
            # Se símbolos foram passados, ordena por volume
            symbols = sorted(symbols, key=lambda s: get_symbol_volume(s), reverse=True)
        
        # Se cache expirou ou está vazio, atualizar
        if (not cache['data'] or time.time() - cache['timestamp'] > cache['refresh_interval']) and db:
            refresh_cache(symbols)
        
        table = {
            'timeframes': TIMEFRAMES,
            'rows': [],
            'timestamp': datetime.now().isoformat(),
            'cache_age': round(time.time() - cache['timestamp'], 1) if cache['timestamp'] > 0 else 0
        }
        
        for symbol in symbols:
            row = {
                'symbol': symbol,
                'timeframes': {}
            }
            
            for timeframe in TIMEFRAMES:
                row['timeframes'][timeframe] = cache['data'].get(symbol, {}).get(timeframe)
            
            table['rows'].append(row)
        
        return jsonify(table)
        
    except Exception as e:
        print(f"Erro em /api/table: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'type': type(e).__name__}), 500


@app.route('/api/filter', methods=['GET'])
def filter_data():
    """
    Filtra dados por status e timeframes.
    
    Parâmetros:
    - status: oversold, overbought, both
    - timeframes: 15m,1h,4h,1d (comma-separated)
    - match: all (todos os timeframes simultâneos)
    
    Exemplo: /api/filter?status=oversold&timeframes=1h,4h&match=all
    """
    try:
        # Parâmetros
        status_filter = request.args.get('status', 'oversold')
        timeframes_filter = request.args.get('timeframes', '1h,4h').split(',')
        match_type = request.args.get('match', 'all')  # sempre all para simultâneo
        
        # Limpar timeframes vazios
        timeframes_filter = [t.strip() for t in timeframes_filter if t.strip()]
        
        if not timeframes_filter:
            timeframes_filter = TIMEFRAMES
        
        filtered_rows = []
        
        for symbol in cache['data'].keys():
            symbol_data = cache['data'][symbol]
            
            matching_timeframes = []
            
            # Verificar cada timeframe
            for timeframe in timeframes_filter:
                tf_data = symbol_data.get(timeframe)
                if tf_data:
                    tf_status = tf_data.get('status')
                    
                    # Verificar se status match
                    if status_filter == 'both':
                        # Both = oversold OU overbought
                        if tf_status in ['oversold', 'overbought']:
                            matching_timeframes.append(timeframe)
                    else:
                        # Status específico
                        if tf_status == status_filter:
                            matching_timeframes.append(timeframe)
            
            # Deve ter em TODOS os timeframes selecionados
            if len(matching_timeframes) == len(timeframes_filter):
                row = {
                    'symbol': symbol,
                    'timeframes': {},
                    'matching': matching_timeframes
                }
                
                for timeframe in TIMEFRAMES:
                    row['timeframes'][timeframe] = cache['data'][symbol].get(timeframe)
                
                filtered_rows.append(row)
        
        # Ordenar por volume decrescente
        filtered_rows = sort_rows_by_volume(filtered_rows)
        
        return jsonify({
            'timeframes': TIMEFRAMES,
            'rows': filtered_rows,
            'count': len(filtered_rows),
            'filters': {
                'status': status_filter,
                'timeframes': timeframes_filter,
                'match': 'all (simultâneo)'
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Erro em /api/filter: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/refresh', methods=['POST'])
def manual_refresh():
    """Força atualização do cache (útil para dashboard em tempo real)"""
    try:
        with db_lock:
            symbols = db.get_all_symbols()
        threading.Thread(target=refresh_cache, args=(symbols,), daemon=True).start()
        return jsonify({'status': 'Refresh iniciado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/calculate', methods=['POST'])
def calculate_pair():
    """Calcula Stochastic RSI para um par específico"""
    data = request.get_json()
    symbol = data.get('symbol')
    timeframe = data.get('timeframe', '1d')
    
    if not symbol:
        return jsonify({'error': 'Symbol obrigatório'}), 400
    
    try:
        # Executar cálculo em thread para não bloquear
        def run_calc():
            with db_lock:
                result = calculator.calculate_pair(symbol, timeframe)
            # Atualizar cache após cálculo
            refresh_cache([symbol])
        
        threading.Thread(target=run_calc, daemon=True).start()
        
        return jsonify({'status': f'Cálculo iniciado para {symbol}', 'symbol': symbol})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    init_backend()
    
    if db is None:
        print("❌ Erro: Não foi possível inicializar o banco de dados")
        print("   Certifique-se de que o arquivo data/stoch_rsi.db existe")
        print("   Execute: python populate_test.py")
        sys.exit(1)
    
    # Obter lista de pares e inicializar cache
    try:
        symbols = db.get_all_symbols()
        
        if not symbols:
            print("⚠️  Nenhum símbolo no banco!")
            print("   Execute: python populate_test.py")
            symbols = []
        
        refresh_cache(symbols)
        
        # Iniciar thread de atualização automática
        refresh_thread = threading.Thread(
            target=background_refresh_thread,
            args=(symbols,),
            daemon=True
        )
        refresh_thread.start()
        
        print(f"\n🚀 API Server iniciado em http://localhost:8000")
        print(f"📊 Monitorando {len(symbols)} pares")
        print(f"⏱️  Timeframes: {', '.join(TIMEFRAMES)}")
        print(f"📋 Acesse: http://localhost:8000")
        
    except Exception as e:
        print(f"❌ Erro ao inicializar: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Usar servidor WSGI leve (melhor para Raspberry Pi)
    app.run(
        host='0.0.0.0',
        port=8000,
        debug=False,
        threaded=True,
        use_reloader=False
    )
