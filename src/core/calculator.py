"""
Lógica principal de cálculo para múltiplos pares
"""

from typing import List, Dict
from src.api.binance import BinanceClient
from src.indicators import calculate_stoch_rsi, StochRSIValue
from src.db.database import StochRSIDatabase


class StochRSICalculatorCore:
    """
    Orquestra o cálculo de Stochastic RSI para múltiplos pares.
    Integra com banco de dados SQLite para armazenamento eficiente.
    """
    
    def __init__(self, binance_client: BinanceClient = None, db: StochRSIDatabase = None):
        """
        Inicializa o calculador.
        
        Args:
            binance_client: Cliente Binance (cria um novo se não fornecido)
            db: Instância do banco de dados (cria uma nova se não fornecida)
        """
        self.client = binance_client or BinanceClient()
        self.db = db or StochRSIDatabase()
        self.symbol_volumes = {}  # Cache de volumes
    
    def calculate_pair(self, symbol: str, interval: str = "1d", limit: int = 100, volume: float = 0) -> Dict:
        """
        Calcula Stochastic RSI para um par específico e salva no banco.
        
        Args:
            symbol: Símbolo do par
            interval: Intervalo de tempo
            limit: Número de velas
            volume: Volume de 24h em USDT
        
        Returns:
            Dicionário com resultados
        """
        # Buscar preços
        closes = self.client.get_klines(symbol, interval, limit)
        
        if not closes:
            return {
                'symbol': symbol,
                'error': 'Não foi possível buscar preços'
            }
        
        # Calcular Stoch RSI
        stoch_rsi_values = calculate_stoch_rsi(closes)
        
        # Extrair últimos 5 valores válidos
        valid_values = [v for v in stoch_rsi_values if v.k is not None and v.d is not None]
        last_values = valid_values[-5:] if valid_values else []
        
        current = stoch_rsi_values[-1] if stoch_rsi_values else None
        
        result = {
            'symbol': symbol,
            'timeframe': interval,
            'total_candles': len(closes),
            'last_values': [
                {
                    'k': round(v.k, 4),
                    'd': round(v.d, 4),
                    'rsi': round(v.rsi, 4) if v.rsi else None
                }
                for v in last_values
            ],
            'current': {
                'k': round(current.k, 4) if current and current.k else None,
                'd': round(current.d, 4) if current and current.d else None,
                'rsi': round(current.rsi, 4) if current and current.rsi else None
            } if current else None
        }
        
        # Salvar no banco de dados
        if current and current.k is not None and current.d is not None:
            self.db.save_stoch_rsi_data(
                symbol, 
                interval, 
                current.k, 
                current.d, 
                current.rsi,
                volume=volume
            )
            
            # Salvar closes para cálculos posteriores
            self.db.save_candles(symbol, interval, closes)
            
            # Salvar histórico
            history_values = [
                {
                    'k': v.k,
                    'd': v.d,
                    'rsi': v.rsi if v.rsi else 0
                }
                for v in last_values
            ]
            self.db.save_history(symbol, interval, history_values)
        
        return result
    
    def calculate_multiple(self, symbols: List[str], interval: str = "1d", limit: int = 100, symbol_volumes: Dict[str, float] = None) -> List[Dict]:
        """
        Calcula Stochastic RSI para múltiplos pares.
        
        Args:
            symbols: Lista de símbolos
            interval: Intervalo de tempo
            limit: Número de velas
            symbol_volumes: Dicionário com volumes dos pares {symbol: volume}
        
        Returns:
            Lista de resultados
        """
        if symbol_volumes is None:
            symbol_volumes = {}
        
        results = []
        total = len(symbols)
        
        for i, symbol in enumerate(symbols, 1):
            print(f"[{i}/{total}] Processando {symbol}...")
            volume = symbol_volumes.get(symbol, 0)
            result = self.calculate_pair(symbol, interval, limit, volume=volume)
            results.append(result)
        
        return results
