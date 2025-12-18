"""
Script de utilidade para consultar dados do banco de dados SQLite
"""

from src.db.database import StochRSIDatabase
import sys


def show_menu():
    """Exibe menu de opções"""
    print("\n" + "="*80)
    print("CONSULTAS - BANCO DE DADOS STOCHASTIC RSI")
    print("="*80)
    print("1. Dados mais recentes de um símbolo/timeframe")
    print("2. Histórico de um símbolo/timeframe")
    print("3. Estatísticas de um símbolo/timeframe")
    print("4. Listar todos os símbolos")
    print("5. Listar todos os timeframes")
    print("6. Exportar dados para JSON")
    print("7. Sair")
    print("="*80)


def query_latest_data(db):
    """Consulta dados mais recentes"""
    symbol = input("\nDigite o símbolo (ex: BTCUSDT): ").upper().strip()
    timeframe = input("Digite o timeframe (ex: 1d): ").strip()
    
    data = db.get_latest_data(symbol, timeframe)
    if data:
        print(f"\n✓ Dados mais recentes para {symbol} ({timeframe}):")
        print(f"  %K: {data['k']}")
        print(f"  %D: {data['d']}")
        print(f"  RSI: {data['rsi']}")
        print(f"  Timestamp: {data['timestamp']}")
    else:
        print(f"\n✗ Nenhum dado encontrado para {symbol} ({timeframe})")


def query_history(db):
    """Consulta histórico"""
    symbol = input("\nDigite o símbolo (ex: BTCUSDT): ").upper().strip()
    timeframe = input("Digite o timeframe (ex: 1d): ").strip()
    
    history = db.get_history(symbol, timeframe)
    if history:
        print(f"\n✓ Histórico para {symbol} ({timeframe}) - Últimas 5 velas:")
        for i, h in enumerate(history, 1):
            print(f"  {i}. %K: {h['k']:>7.4f} | %D: {h['d']:>7.4f} | RSI: {h['rsi']:>7.4f}")
    else:
        print(f"\n✗ Nenhum histórico encontrado para {symbol} ({timeframe})")


def query_statistics(db):
    """Consulta estatísticas"""
    symbol = input("\nDigite o símbolo (ex: BTCUSDT): ").upper().strip()
    timeframe = input("Digite o timeframe (ex: 1d): ").strip()
    limit = input("Limite de registros para cálculo (default 100): ").strip()
    limit = int(limit) if limit else 100
    
    stats = db.get_statistics(symbol, timeframe, limit)
    if stats and stats.get('total_records', 0) > 0:
        print(f"\n✓ Estatísticas para {symbol} ({timeframe}) - Últimos {limit} registros:")
        print(f"\n  %K:")
        print(f"    Média: {stats['k_avg']}")
        print(f"    Mínimo: {stats['k_min']}")
        print(f"    Máximo: {stats['k_max']}")
        print(f"\n  %D:")
        print(f"    Média: {stats['d_avg']}")
        print(f"    Mínimo: {stats['d_min']}")
        print(f"    Máximo: {stats['d_max']}")
        print(f"\n  RSI:")
        print(f"    Média: {stats['rsi_avg']}")
        print(f"    Mínimo: {stats['rsi_min']}")
        print(f"    Máximo: {stats['rsi_max']}")
        print(f"\n  Total de registros: {stats['total_records']}")
    else:
        print(f"\n✗ Nenhum dado encontrado para {symbol} ({timeframe})")


def list_symbols(db):
    """Lista todos os símbolos"""
    symbols = db.get_all_symbols()
    if symbols:
        print(f"\n✓ Símbolos no banco ({len(symbols)} total):")
        for i, symbol in enumerate(symbols, 1):
            if i % 5 == 0:
                print(f"  {symbol}")
            else:
                print(f"  {symbol}", end="")
        print()
    else:
        print("\n✗ Nenhum símbolo encontrado no banco")


def list_timeframes(db):
    """Lista todos os timeframes"""
    timeframes = db.get_all_timeframes()
    if timeframes:
        print(f"\n✓ Timeframes no banco ({len(timeframes)} total):")
        print(f"  {', '.join(timeframes)}")
    else:
        print("\n✗ Nenhum timeframe encontrado no banco")


def export_data(db):
    """Exporta dados para JSON"""
    filename = input("\nNome do arquivo (default: results/database_export.json): ").strip()
    if not filename:
        filename = "results/database_export.json"
    
    db.export_to_json(filename)


def main():
    """Função principal"""
    print("\nConectando ao banco de dados...")
    db = StochRSIDatabase()
    
    try:
        while True:
            show_menu()
            choice = input("\nEscolha uma opção (1-7): ").strip()
            
            if choice == "1":
                query_latest_data(db)
            elif choice == "2":
                query_history(db)
            elif choice == "3":
                query_statistics(db)
            elif choice == "4":
                list_symbols(db)
            elif choice == "5":
                list_timeframes(db)
            elif choice == "6":
                export_data(db)
            elif choice == "7":
                print("\nFechando conexão...")
                db.close()
                print("✓ Até logo!")
                break
            else:
                print("\n✗ Opção inválida!")
    except KeyboardInterrupt:
        print("\n\nInterrompido pelo usuário")
        db.close()
    except Exception as e:
        print(f"\n✗ Erro: {e}")
        db.close()


if __name__ == "__main__":
    main()
