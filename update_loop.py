"""
Script de atualização contínua em ciclo
Processa um par de cada vez, sequencialmente, sem paralelo
Otimizado para Raspberry Pi
"""

import time
import sys
from datetime import datetime
from config import TIMEFRAMES
from src.api.binance import BinanceClient
from src.core.calculator import StochRSICalculatorCore
from src.db.database import StochRSIDatabase


def main():
    """Loop contínuo de atualização"""
    
    print("="*100)
    print("🔄 ATUALIZAÇÃO CONTÍNUA - Stochastic RSI")
    print("="*100)
    
    try:
        # Verificar parâmetros
        test_mode = '-test' in sys.argv
        
        # Inicializar
        db = StochRSIDatabase()
        client = BinanceClient()
        calculator = StochRSICalculatorCore(client, db)
        
        # Obter lista de pares uma vez
        print("\n📋 Buscando lista de pares...")
        pairs = client.get_trading_pairs()
        symbols = [p['symbol'] for p in pairs]  # Todos os pares, sem limite
        
        # Se modo teste, usar apenas 5 pares
        if test_mode:
            symbols = symbols[:5]
            print(f"⚠️  MODO TESTE ATIVADO - Processando apenas 5 pares")
        
        print(f"✓ Total de pares a processar: {len(symbols)}\n")
        
        # Obter volumes apenas UMA VEZ (primeira execução)
        print("📊 Verificando volumes no banco...")
        symbol_volumes = {}
        symbols_sem_volume = []
        
        # Verificar quais pares já têm volume no banco
        for symbol in symbols:
            cursor = db.connection.cursor()
            cursor.execute('SELECT volume FROM symbols WHERE symbol = ?', (symbol,))
            result = cursor.fetchone()
            
            if result and result[0] and result[0] > 0:
                symbol_volumes[symbol] = result[0]
            else:
                symbols_sem_volume.append(symbol)
        
        print(f"✓ {len(symbol_volumes)} pares com volume no banco")
        
        # Se faltam volumes, buscar apenas dos que não têm
        if symbols_sem_volume:
            print(f"📡 Buscando volumes para {len(symbols_sem_volume)} pares novos...")
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_symbol = {
                    executor.submit(client.get_symbol_volume, symbol): symbol 
                    for symbol in symbols_sem_volume
                }
                for future in as_completed(future_to_symbol):
                    symbol = future_to_symbol[future]
                    try:
                        volume = future.result()
                        if volume > 0:
                            symbol_volumes[symbol] = volume
                    except Exception:
                        symbol_volumes[symbol] = 0
            
            print(f"✓ Volumes obtidos para {len([v for v in symbol_volumes.values() if v > 0])} pares\n")
        else:
            print("✓ Todos os pares já têm volume no banco\n")
        
        # Loop infinito
        cycle = 0
        while True:
            cycle += 1
            print(f"\n{'='*100}")
            print(f"📅 CICLO #{cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*100}")
            
            updated_count = 0
            error_count = 0
            
            # Processar cada PAR (com todos os timeframes)
            for i, symbol in enumerate(symbols, 1):
                try:
                    volume = symbol_volumes.get(symbol, 0)
                    print(f"\n  [{i:3}/{len(symbols)}] {symbol:12}")
                    print(f"  {'-'*60}")
                    
                    # Para cada par, processar TODOS os timeframes
                    for timeframe in TIMEFRAMES:
                        try:
                            # Buscar e processar um par/timeframe
                            closes = client.get_klines(symbol, timeframe, limit=100)
                            
                            if closes:
                                from src.indicators import calculate_stoch_rsi
                                stoch_rsi_values = calculate_stoch_rsi(closes)
                                
                                if stoch_rsi_values:
                                    current = stoch_rsi_values[-1]
                                    
                                    if current and current.k is not None and current.d is not None:
                                        # Salvar no banco IMEDIATAMENTE
                                        db.save_stoch_rsi_data(
                                            symbol,
                                            timeframe,
                                            current.k,
                                            current.d,
                                            current.rsi,
                                            volume=volume
                                        )
                                        
                                        # Salvar closes
                                        db.save_candles(symbol, timeframe, closes)
                                        
                                        # Salvar histórico
                                        valid_values = [v for v in stoch_rsi_values if v.k is not None and v.d is not None]
                                        last_values = valid_values[-5:] if valid_values else []
                                        history_values = [
                                            {
                                                'k': v.k,
                                                'd': v.d,
                                                'rsi': v.rsi if v.rsi else 0
                                            }
                                            for v in last_values
                                        ]
                                        db.save_history(symbol, timeframe, history_values)
                                        
                                        k = round(current.k, 4)
                                        d = round(current.d, 4)
                                        print(f"    ⏱️  {timeframe:4} | %K: {k:>7.4f} | %D: {d:>7.4f} ✓")
                                        updated_count += 1
                                    else:
                                        print(f"    ⏱️  {timeframe:4} | Sem dados")
                        
                        except Exception as e:
                            error_count += 1
                            print(f"    ⏱️  {timeframe:4} | Erro: {str(e)[:40]}")
                    
                    # Pequeno delay entre pares para não sobrecarregar
                    time.sleep(0.1)
                
                except Exception as e:
                    error_count += 1
                    print(f"  [{i:3}/{len(symbols)}] {symbol:12} | Erro geral: {str(e)[:50]}")
            
            # Resumo do ciclo
            print(f"\n{'='*100}")
            print(f"✓ Ciclo #{cycle} concluído: {updated_count} atualizados | {error_count} erros")
            print(f"⏳ Próximo ciclo em 5 minutos...")
            print(f"{'='*100}")
            time.sleep(300)
    
    except KeyboardInterrupt:
        print("\n\n⛔ Interrompido pelo utilizador")
        db.close()
        sys.exit(0)
    
    except Exception as e:
        print(f"\n✗ Erro fatal: {e}")
        db.close()
        sys.exit(1)


if __name__ == "__main__":
    main()
