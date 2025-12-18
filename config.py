"""
Configuração padrão do projeto
"""

# Diretórios de saída
RESULTS_DIR = "results"

# Parâmetros padrão Binance
BINANCE_TIMEOUT = 10
DEFAULT_INTERVAL = "1d"
DEFAULT_LIMIT = 100

# Timeframes disponíveis (em minutos para referência)
# Você pode adicionar/remover timeframes conforme necessário
TIMEFRAMES = [
    "15m",   # 15 minutos
    "1h",    # 1 hora
    "4h",    # 4 horas
    "1d"     # 1 dia
]

# Parâmetros padrão Stochastic RSI
STOCH_RSI_PARAMS = {
    "rsi_length": 14,
    "stoch_length": 14,
    "k_smooth": 3,
    "d_smooth": 3
}
