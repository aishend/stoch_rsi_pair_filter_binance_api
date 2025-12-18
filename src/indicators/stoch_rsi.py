"""
Módulo para cálculo do Stochastic RSI (Stoch RSI)
Implementação 100% fiel ao TradingView
Parâmetros: RSI length=14, Stochastic length=14, K smooth=3, D smooth=3
"""

from typing import List, Optional
from dataclasses import dataclass


@dataclass
class StochRSIValue:
    """Representa um valor do Stochastic RSI"""
    k: Optional[float]  # %K (Stochastic RSI)
    d: Optional[float]  # %D (SMA de %K)
    rsi: Optional[float]  # RSI usado no cálculo


class StochasticRSICalculator:
    """
    Calcula Stochastic RSI com 100% precisão TradingView.
    
    Parâmetros padrão TradingView:
    - RSI length: 14
    - Stochastic length: 14  
    - K smooth: 3
    - D smooth: 3
    - RSI source: close
    """
    
    def __init__(self, rsi_length: int = 14, stoch_length: int = 14, k_smooth: int = 3, d_smooth: int = 3):
        """
        Inicializa com parâmetros TradingView.
        
        Args:
            rsi_length: Comprimento do RSI (default: 14)
            stoch_length: Comprimento do Stochastic (default: 14)
            k_smooth: Período para suavização %K (default: 3)
            d_smooth: Período para suavização %D (default: 3)
        """
        self.rsi_length = rsi_length
        self.stoch_length = stoch_length
        self.k_smooth = k_smooth
        self.d_smooth = d_smooth
    
    @staticmethod
    def _calculate_rsi(closes: List[float], period: int = 14) -> List[Optional[float]]:
        """
        Calcula RSI usando Wilder's smoothing (exatamente como TradingView).
        
        Args:
            closes: Lista de preços de fechamento
            period: Período do RSI
        
        Returns:
            Lista com valores RSI
        """
        if len(closes) < period + 1:
            return [None] * len(closes)
        
        rsi_values = [None] * len(closes)
        
        # Calcular mudanças
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        
        # Ganhos e perdas
        gains = [max(d, 0) for d in deltas]
        losses = [abs(min(d, 0)) for d in deltas]
        
        # Primeira média (SMA simples para os primeiros 'period' valores)
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        # Calcular RSI para posição 'period'
        if avg_loss == 0:
            rsi_values[period] = 100 if avg_gain > 0 else 0
        else:
            rs = avg_gain / avg_loss
            rsi_values[period] = 100 - (100 / (1 + rs))
        
        # Aplicar Wilder's smoothing para o restante
        for i in range(period + 1, len(closes)):
            avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
            
            if avg_loss == 0:
                rsi_values[i] = 100 if avg_gain > 0 else 0
            else:
                rs = avg_gain / avg_loss
                rsi_values[i] = 100 - (100 / (1 + rs))
        
        return rsi_values
    
    @staticmethod
    def _calculate_stoch_k(rsi_values: List[Optional[float]], period: int = 14) -> List[Optional[float]]:
        """
        Calcula %K do Stochastic RSI.
        
        %K = ((RSI - Lowest Low) / (Highest High - Lowest Low)) * 100
        
        Args:
            rsi_values: Lista de valores RSI
            period: Período para encontrar min/max (default: 14)
        
        Returns:
            Lista com valores %K
        """
        k_values = [None] * len(rsi_values)
        
        for i in range(period - 1, len(rsi_values)):
            # Pegar últimos 'period' valores RSI válidos
            window = []
            for j in range(i - period + 1, i + 1):
                if rsi_values[j] is not None:
                    window.append(rsi_values[j])
            
            if len(window) < period:
                continue
            
            min_rsi = min(window)
            max_rsi = max(window)
            
            # Evitar divisão por zero
            if max_rsi == min_rsi:
                k_values[i] = 50
            else:
                k_values[i] = ((rsi_values[i] - min_rsi) / (max_rsi - min_rsi)) * 100
        
        return k_values
    
    @staticmethod
    def _calculate_sma(values: List[Optional[float]], period: int = 3) -> List[Optional[float]]:
        """
        Calcula SMA (Simple Moving Average).
        
        Args:
            values: Lista de valores
            period: Período da média
        
        Returns:
            Lista com valores SMA
        """
        sma_values = [None] * len(values)
        
        for i in range(period - 1, len(values)):
            window = []
            for j in range(i - period + 1, i + 1):
                if values[j] is not None:
                    window.append(values[j])
            
            if len(window) == period:
                sma_values[i] = sum(window) / period
        
        return sma_values
    
    def calculate(self, closes: List[float]) -> List[StochRSIValue]:
        """
        Calcula o Stochastic RSI completo com parâmetros TradingView.
        
        Args:
            closes: Lista de preços de fechamento
        
        Returns:
            Lista de StochRSIValue
        """
        if len(closes) < self.rsi_length + self.stoch_length + self.k_smooth + self.d_smooth - 2:
            return [StochRSIValue(k=None, d=None, rsi=None)] * len(closes)
        
        # 1. Calcular RSI(14)
        rsi_values = self._calculate_rsi(closes, self.rsi_length)
        
        # 2. Calcular %K = Stochastic do RSI
        k_values = self._calculate_stoch_k(rsi_values, self.stoch_length)
        
        # 3. Suavizar %K com SMA(3)
        k_smoothed = self._calculate_sma(k_values, self.k_smooth)
        
        # 4. Calcular %D = SMA de %K suavizado (SMA(3) de SMA(3))
        d_values = self._calculate_sma(k_smoothed, self.d_smooth)
        
        # Montar resultado
        result = []
        for i in range(len(closes)):
            result.append(StochRSIValue(
                k=k_smoothed[i],
                d=d_values[i],
                rsi=rsi_values[i]
            ))
        
        return result


def calculate_stoch_rsi(closes: List[float], 
                       rsi_length: int = 14,
                       stoch_length: int = 14, 
                       k_smooth: int = 3,
                       d_smooth: int = 3) -> List[StochRSIValue]:
    """
    Função conveniência para calcular Stochastic RSI com parâmetros TradingView.
    
    Parâmetros padrão TradingView:
    - RSI length: 14
    - Stochastic length: 14
    - K smooth: 3
    - D smooth: 3
    
    Args:
        closes: Lista de preços de fechamento
        rsi_length: Período RSI (default: 14)
        stoch_length: Período Stochastic (default: 14)
        k_smooth: Período suavização %K (default: 3)
        d_smooth: Período suavização %D (default: 3)
    
    Returns:
        Lista de StochRSIValue com K, D, RSI
    """
    calculator = StochasticRSICalculator(rsi_length, stoch_length, k_smooth, d_smooth)
    return calculator.calculate(closes)
