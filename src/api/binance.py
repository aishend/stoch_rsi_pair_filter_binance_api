"""
Cliente para integração com a API Binance Futures
"""

import requests
from typing import List, Dict, Optional


class BinanceClient:
    """
    Cliente para interagir com a API Binance Futures.
    """
    
    BASE_URL = "https://fapi.binance.com"
    EXCHANGE_INFO_ENDPOINT = "/fapi/v1/exchangeInfo"
    KLINES_ENDPOINT = "/fapi/v1/klines"
    TICKER_24H_ENDPOINT = "/fapi/v1/ticker/24hr"
    
    def __init__(self, timeout: int = 10):
        """
        Inicializa o cliente Binance.
        
        Args:
            timeout: Tempo máximo de espera por requisição em segundos
        """
        self.timeout = timeout
    
    def get_exchange_info(self) -> Optional[Dict]:
        """
        Obtém informações do exchange (símbolos, status, etc).
        
        Returns:
            Dicionário com informações do exchange ou None em caso de erro
        """
        try:
            url = f"{self.BASE_URL}{self.EXCHANGE_INFO_ENDPOINT}"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Erro ao obter exchange info: {e}")
            return None
    
    def get_trading_pairs(self) -> List[Dict]:
        """
        Obtém todos os pares de trading ativos.
        
        Returns:
            Lista de dicionários com informações dos pares
        """
        exchange_info = self.get_exchange_info()
        
        if not exchange_info:
            return []
        
        symbols = exchange_info.get('symbols', [])
        
        # Filtrar apenas símbolos TRADING
        active_symbols = [s for s in symbols if s['status'] == 'TRADING']
        
        pairs_info = []
        for symbol in active_symbols:
            pairs_info.append({
                'symbol': symbol['symbol'],
                'baseAsset': symbol['baseAsset'],
                'quoteAsset': symbol['quoteAsset'],
                'status': symbol['status'],
                'underlyingType': symbol.get('underlyingType', 'N/A'),
                'underlyingSubType': symbol.get('underlyingSubType', 'N/A'),
            })
        
        return pairs_info
    
    def get_klines(self, symbol: str, interval: str = "1d", limit: int = 100) -> List[float]:
        """
        Obtém o histórico de preços (klines) de um par.
        
        Args:
            symbol: Símbolo do par (ex: BTCUSDT)
            interval: Intervalo de tempo (default: 1d)
            limit: Número de velas a buscar (default: 100)
        
        Returns:
            Lista de preços de fechamento
        """
        try:
            url = f"{self.BASE_URL}{self.KLINES_ENDPOINT}"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            klines = response.json()
            
            # Extrair preços de fechamento (índice 4)
            closes = [float(kline[4]) for kline in klines]
            
            return closes
        
        except requests.exceptions.RequestException as e:
            print(f"Erro ao buscar klines para {symbol}: {e}")
            return []
    
    def get_24h_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Obtém informações de 24h de um símbolo (incluindo volume).
        
        Args:
            symbol: Símbolo do par (ex: BTCUSDT)
        
        Returns:
            Dicionário com informações de 24h ou None em caso de erro
        """
        try:
            url = f"{self.BASE_URL}{self.TICKER_24H_ENDPOINT}"
            params = {'symbol': symbol}
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"Erro ao buscar ticker 24h para {symbol}: {e}")
            return None
    
    def get_symbol_volume(self, symbol: str) -> float:
        """
        Obtém o volume em USDT de 24h de um símbolo.
        
        Args:
            symbol: Símbolo do par (ex: BTCUSDT)
        
        Returns:
            Volume em USDT ou 0 em caso de erro
        """
        ticker = self.get_24h_ticker(symbol)
        
        if ticker and 'quoteVolume' in ticker:
            try:
                return float(ticker['quoteVolume'])
            except (ValueError, TypeError):
                return 0
        
        return 0
