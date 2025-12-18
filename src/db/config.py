"""
Configuração da base de dados SQLite
"""

# Caminho do banco de dados
DATABASE_PATH = "data/stoch_rsi.db"

# Configurações SQLite
SQLITE_CONFIG = {
    "timeout": 5.0,
    "check_same_thread": False,
    "isolation_level": None  # Autocommit mode
}

# Descrição das tabelas:
#
# 1. timeframes
#    - Armazena nomes de timeframes (15m, 1h, 4h, 1d, etc)
#    - Evita duplicação e facilita queries
#
# 2. symbols
#    - Armazena símbolos/pares (BTCUSDT, ETHUSDT, etc)
#    - Referência para dados de múltiplos pares
#
# 3. stoch_rsi_data
#    - Armazena os valores mais recentes de K, D e RSI
#    - Índices para acesso rápido por símbolo/timeframe
#    - UNIQUE constraint evita duplicatas
#
# 4. stoch_rsi_history
#    - Armazena histórico das últimas 5 velas
#    - Sequence para manter ordem
#    - Facilita análise de tendências recentes

print("✓ Configuração de banco de dados carregada")
