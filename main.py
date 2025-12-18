"""
Script principal para calcular Stochastic RSI de múltiplos pares
Suporta modo teste com -test para processar apenas os primeiros 5 pares
"""

import json
import sys
import argparse
from config import TIMEFRAMES
from src.api.binance import BinanceClient
from src.core.calculator import StochRSICalculatorCore
from src.db.database import StochRSIDatabase


def save_results(results: dict, filename: str = "results/stoch_rsi_results.json"):
    """Salva resultados em arquivo JSON"""
    import os
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Resultados salvos em '{filename}'")


def print_summary(results: dict, limit: int = 20):
    """Exibe resumo dos resultados para todos os timeframes"""
    print("\n" + "="*100)
    print("Stochastic RSI - Resumo por Timeframe")
    print("="*100)
    
    for timeframe, timeframe_results in results.items():
        print(f"\n📊 TIMEFRAME: {timeframe}")
        print("-"*100)
        
        for i, result in enumerate(timeframe_results[:limit], 1):
            if 'error' in result:
                print(f"{i}. {result['symbol']}: {result['error']}")
            else:
                current = result.get('current')
                if current and current.get('k') is not None:
                    k = current.get('k', 0) or 0
                    d = current.get('d', 0) or 0
                    rsi = current.get('rsi', 0) or 0
                    print(f"{i}. {result['symbol']:12} | %K: {k:>7.4f} | %D: {d:>7.4f} | RSI: {rsi:>7.4f}")
                else:
                    print(f"{i}. {result['symbol']:12} | Sem dados suficientes")


def main():
    """Função principal"""
    # Parser para argumentos de linha de comando
    parser = argparse.ArgumentParser(
        description='Calcular Stochastic RSI para pares de criptomoedas',
        epilog='Exemplos:\n  python main.py          # Processa TODOS os pares\n  python main.py -test    # Modo teste: apenas 5 pares\n  python main.py --help   # Mostra esta ajuda',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '-test', '--test-mode',
        action='store_true',
        dest='test_mode',
        help='Modo teste: processa apenas os primeiros 5 pares (rápido para testes)'
    )
    
    parser.add_argument(
        '-n', '--num-pairs',
        type=int,
        default=None,
        metavar='N',
        help='Número de pares a processar (default: TODOS, ou 5 se -test)'
    )
    
    parser.add_argument(
        '--no-export',
        action='store_true',
        help='Não exporta dados para JSON'
    )
    
    parser.add_argument(
        '--only-db',
        action='store_true',
        help='Salva apenas no banco de dados, sem JSON'
    )
    
    # Parsear argumentos
    args = parser.parse_args()
    
    # Determinar número de pares baseado nos argumentos
    if args.test_mode:
        num_pairs = 5
        mode_label = "TESTE"
    elif args.num_pairs:
        num_pairs = args.num_pairs
        mode_label = "CUSTOMIZADO"
    else:
        num_pairs = None  # None significa processar TODOS
        mode_label = "COMPLETO"
    
    print("Inicializando...\n")
    print(f"🔧 Modo: {mode_label}")
    if args.test_mode:
        print("   Processando apenas 5 pares principais (teste rápido)")
    print(f"   Pares a processar: {num_pairs if num_pairs else 'TODOS os disponíveis'}")
    print(f"   Timeframes: {', '.join(TIMEFRAMES)}\n")
    
    # Inicializar cliente, calculador e banco de dados
    binance_client = BinanceClient()
    db = StochRSIDatabase()
    calculator = StochRSICalculatorCore(binance_client, db)
    
    # Obter pares disponíveis
    print("Buscando pares de futures...")
    pairs = binance_client.get_trading_pairs()
    
    if not pairs:
        print("Erro: Nenhum par encontrado!")
        db.close()
        return
    
    print(f"✓ Total de pares encontrados: {len(pairs)}\n")
    
    # Selecionar pares baseado no modo
    if num_pairs is None:
        symbols = [p['symbol'] for p in pairs]  # TODOS os pares
    else:
        symbols = [p['symbol'] for p in pairs[:num_pairs]]
    
    print(f"✓ Selecionados {len(symbols)} pares para processamento:")
    if len(symbols) <= 20:
        print(f"  {', '.join(symbols)}\n")
    else:
        print(f"  {', '.join(symbols[:10])}... (+{len(symbols)-10} mais)\n")
    
    # Obter volumes de 24h dos pares selecionados
    print("Buscando volumes de 24h...")
    symbol_volumes = {}
    for symbol in symbols:
        volume = binance_client.get_symbol_volume(symbol)
        symbol_volumes[symbol] = volume
    print(f"✓ Volumes obtidos para {len([v for v in symbol_volumes.values() if v > 0])} pares\n")
    
    # Dicionário para armazenar resultados de todos os timeframes
    all_results = {}
    
    # Processar cada timeframe
    for timeframe in TIMEFRAMES:
        print(f"\n{'='*100}")
        print(f"📈 Processando timeframe: {timeframe}")
        print(f"{'='*100}")
        print(f"Calculando Stoch RSI para {len(symbols)} pares no timeframe {timeframe}...\n")
        
        results = calculator.calculate_multiple(symbols, interval=timeframe, limit=100, symbol_volumes=symbol_volumes)
        all_results[timeframe] = results
        
        # Estatísticas por timeframe
        successful = [r for r in results if 'error' not in r and 'current' in r]
        print(f"✓ {len(successful)}/{len(results)} pares calculados com sucesso\n")
    
    # Exibir resumo consolidado
    print_summary(all_results, limit=20)
    
    # Salvar resultados em JSON (se não usar --only-db)
    if not args.only_db and not args.no_export:
        save_results(all_results)
    
    # Exportar dados do banco para JSON (se não usar --no-export)
    if not args.no_export:
        db.export_to_json("results/database_export.json")
    
    # Estatísticas finais
    print(f"\n" + "="*100)
    print("RESUMO FINAL")
    print("="*100)
    for timeframe, results in all_results.items():
        successful = [r for r in results if 'error' not in r and 'current' in r]
        print(f"{timeframe:>5}: {len(successful):3}/{len(results):3} pares processados com sucesso")
    
    print("\n📊 Banco de dados:")
    print(f"   - Símbolos no banco: {len(db.get_all_symbols())}")
    print(f"   - Timeframes no banco: {len(db.get_all_timeframes())}")
    print(f"   - Arquivo: {db.db_path}")
    
    if args.test_mode:
        print("\n💡 Modo teste ativo: para processar todos os pares, execute:")
        print("   python main.py")
    
    print("="*100)
    
    # Fechar conexão com banco
    db.close()


if __name__ == "__main__":
    main()
