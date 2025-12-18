"""
Gerenciador de banco de dados SQLite para armazenar dados de Stochastic RSI
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple


class StochRSIDatabase:
    """
    Gerencia o armazenamento e recuperação de dados de Stochastic RSI em SQLite.
    Oferece melhor desempenho, queries eficientes e histórico completo.
    """
    
    def __init__(self, db_path: str = "data/stoch_rsi.db"):
        """
        Inicializa a conexão com o banco de dados.
        
        Args:
            db_path: Caminho para o arquivo SQLite
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """Estabelece conexão com o banco de dados"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            print(f"✓ Conectado ao banco de dados: {self.db_path}")
        except sqlite3.Error as e:
            print(f"Erro ao conectar ao banco: {e}")
            raise
    
    def close(self):
        """Fecha a conexão com o banco de dados"""
        if self.connection:
            self.connection.close()
            print("✓ Conexão com banco de dados fechada")
    
    def create_tables(self):
        """Cria as tabelas necessárias"""
        cursor = self.connection.cursor()
        
        # Tabela de timeframes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS timeframes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de símbolos/pares
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS symbols (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                base_asset TEXT,
                quote_asset TEXT,
                volume REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Adiciona coluna volume se não existir (para bancos existentes)
        cursor.execute("PRAGMA table_info(symbols)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'volume' not in columns:
            cursor.execute('ALTER TABLE symbols ADD COLUMN volume REAL DEFAULT 0')
            self.connection.commit()
        
        # Tabela de velas (closes) - para cálculos nas queries
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol_id INTEGER NOT NULL,
                timeframe_id INTEGER NOT NULL,
                close_price REAL NOT NULL,
                open_time INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (symbol_id) REFERENCES symbols (id),
                FOREIGN KEY (timeframe_id) REFERENCES timeframes (id),
                UNIQUE (symbol_id, timeframe_id, open_time)
            )
        ''')
        
        # Tabela principal de dados Stoch RSI
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stoch_rsi_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol_id INTEGER NOT NULL,
                timeframe_id INTEGER NOT NULL,
                k_value REAL,
                d_value REAL,
                rsi_value REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (symbol_id) REFERENCES symbols (id),
                FOREIGN KEY (timeframe_id) REFERENCES timeframes (id),
                UNIQUE (symbol_id, timeframe_id, timestamp)
            )
        ''')
        
        # Tabela de histórico (últimas 5 velas)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stoch_rsi_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol_id INTEGER NOT NULL,
                timeframe_id INTEGER NOT NULL,
                k_value REAL,
                d_value REAL,
                rsi_value REAL,
                sequence INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (symbol_id) REFERENCES symbols (id),
                FOREIGN KEY (timeframe_id) REFERENCES timeframes (id),
                UNIQUE (symbol_id, timeframe_id, sequence)
            )
        ''')
        
        # Criar índices para melhor performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol_timeframe 
            ON stoch_rsi_data (symbol_id, timeframe_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_history_symbol_timeframe 
            ON stoch_rsi_history (symbol_id, timeframe_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_candles_symbol_timeframe 
            ON candles (symbol_id, timeframe_id)
        ''')
        
        self.connection.commit()
    
    def get_or_create_timeframe(self, timeframe: str) -> int:
        """Obtém ou cria um timeframe e retorna seu ID"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT id FROM timeframes WHERE name = ?', (timeframe,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        cursor.execute('INSERT INTO timeframes (name) VALUES (?)', (timeframe,))
        self.connection.commit()
        return cursor.lastrowid
    
    def get_or_create_symbol(self, symbol: str, base_asset: str = None, quote_asset: str = None, volume: float = 0) -> int:
        """Obtém ou cria um símbolo e retorna seu ID"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT id FROM symbols WHERE symbol = ?', (symbol,))
        result = cursor.fetchone()
        
        if result:
            # Atualiza volume se for maior
            cursor.execute('SELECT volume FROM symbols WHERE symbol = ?', (symbol,))
            current_volume = cursor.fetchone()[0] or 0
            if volume > current_volume:
                cursor.execute('UPDATE symbols SET volume = ? WHERE symbol = ?', (volume, symbol))
                self.connection.commit()
            return result[0]
        
        cursor.execute(
            'INSERT INTO symbols (symbol, base_asset, quote_asset, volume) VALUES (?, ?, ?, ?)',
            (symbol, base_asset, quote_asset, volume)
        )
        self.connection.commit()
        return cursor.lastrowid
    
    def save_stoch_rsi_data(self, symbol: str, timeframe: str, k: float, d: float, rsi: float, volume: float = 0):
        """
        Salva dados de Stoch RSI no banco de dados.
        
        Args:
            symbol: Símbolo do par
            timeframe: Timeframe (15m, 1h, 4h, 1d, etc)
            k: Valor de %K
            d: Valor de %D
            rsi: Valor de RSI
            volume: Volume de 24h em USDT
        """
        symbol_id = self.get_or_create_symbol(symbol, volume=volume)
        timeframe_id = self.get_or_create_timeframe(timeframe)
        
        cursor = self.connection.cursor()
        try:
            cursor.execute('''
                INSERT INTO stoch_rsi_data (symbol_id, timeframe_id, k_value, d_value, rsi_value)
                VALUES (?, ?, ?, ?, ?)
            ''', (symbol_id, timeframe_id, k, d, rsi))
            self.connection.commit()
        except sqlite3.IntegrityError:
            # Se já existe, atualiza
            cursor.execute('''
                UPDATE stoch_rsi_data 
                SET k_value = ?, d_value = ?, rsi_value = ?, timestamp = CURRENT_TIMESTAMP
                WHERE symbol_id = ? AND timeframe_id = ?
            ''', (k, d, rsi, symbol_id, timeframe_id))
            self.connection.commit()
    
    def save_candles(self, symbol: str, timeframe: str, closes: list, open_times: list = None):
        """
        Salva preços de fechamento (closes) para cálculos posteriores.
        
        Args:
            symbol: Símbolo do par
            timeframe: Timeframe
            closes: Lista de preços de fechamento
            open_times: Lista de unix timestamps (opcional)
        """
        symbol_id = self.get_or_create_symbol(symbol)
        timeframe_id = self.get_or_create_timeframe(timeframe)
        
        cursor = self.connection.cursor()
        
        # Limpar velas antigas
        cursor.execute(
            'DELETE FROM candles WHERE symbol_id = ? AND timeframe_id = ?',
            (symbol_id, timeframe_id)
        )
        
        # Inserir novas velas
        for i, close in enumerate(closes):
            open_time = open_times[i] if open_times and i < len(open_times) else i
            try:
                cursor.execute('''
                    INSERT INTO candles (symbol_id, timeframe_id, close_price, open_time)
                    VALUES (?, ?, ?, ?)
                ''', (symbol_id, timeframe_id, close, open_time))
            except sqlite3.IntegrityError:
                pass  # Já existe, ignorar
        
        self.connection.commit()
    
    def save_history(self, symbol: str, timeframe: str, values: List[Dict]):
        """
        Salva histórico de últimas velas.
        
        Args:
            symbol: Símbolo do par
            timeframe: Timeframe
            values: Lista de dicionários com k, d, rsi
        """
        symbol_id = self.get_or_create_symbol(symbol)
        timeframe_id = self.get_or_create_timeframe(timeframe)
        
        cursor = self.connection.cursor()
        
        # Limpar histórico anterior
        cursor.execute(
            'DELETE FROM stoch_rsi_history WHERE symbol_id = ? AND timeframe_id = ?',
            (symbol_id, timeframe_id)
        )
        
        # Inserir novo histórico
        for i, value in enumerate(values, 1):
            try:
                cursor.execute('''
                    INSERT INTO stoch_rsi_history 
                    (symbol_id, timeframe_id, k_value, d_value, rsi_value, sequence)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (symbol_id, timeframe_id, value['k'], value['d'], value['rsi'], i))
            except sqlite3.Error as e:
                print(f"Erro ao salvar histórico: {e}")
        
        self.connection.commit()
    
    def get_latest_data(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """
        Obtém os dados mais recentes de um símbolo/timeframe.
        
        Returns:
            Dicionário com k, d, rsi ou None
        """
        symbol_id = self.get_or_create_symbol(symbol)
        timeframe_id = self.get_or_create_timeframe(timeframe)
        
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT k_value, d_value, rsi_value, timestamp 
            FROM stoch_rsi_data 
            WHERE symbol_id = ? AND timeframe_id = ?
            ORDER BY timestamp DESC LIMIT 1
        ''', (symbol_id, timeframe_id))
        
        result = cursor.fetchone()
        if result:
            return {
                'k': round(result[0], 4) if result[0] else None,
                'd': round(result[1], 4) if result[1] else None,
                'rsi': round(result[2], 4) if result[2] else None,
                'timestamp': result[3]
            }
        return None
    
    def get_latest_stoch_rsi(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """
        Obtém o valor mais recente de Stochastic RSI para um símbolo/timeframe.
        Método otimizado para API.
        
        Returns:
            Dicionário com k, d, rsi, timestamp ou None
        """
        return self.get_latest_data(symbol, timeframe)
    
    def get_history(self, symbol: str, timeframe: str) -> List[Dict]:
        """
        Obtém histórico de últimas velas.
        
        Returns:
            Lista de dicionários com k, d, rsi
        """
        symbol_id = self.get_or_create_symbol(symbol)
        timeframe_id = self.get_or_create_timeframe(timeframe)
        
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT k_value, d_value, rsi_value 
            FROM stoch_rsi_history 
            WHERE symbol_id = ? AND timeframe_id = ?
            ORDER BY sequence
        ''', (symbol_id, timeframe_id))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'k': round(row[0], 4) if row[0] else None,
                'd': round(row[1], 4) if row[1] else None,
                'rsi': round(row[2], 4) if row[2] else None
            })
        return results
    
    def get_all_symbols(self) -> List[str]:
        """Obtém lista de todos os símbolos no banco"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT symbol FROM symbols ORDER BY symbol')
        return [row[0] for row in cursor.fetchall()]
    
    def get_all_symbols_by_volume(self) -> List[str]:
        """Obtém lista de todos os símbolos ordenados por volume decrescente"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT symbol FROM symbols WHERE volume > 0 ORDER BY volume DESC')
        symbols_with_volume = [row[0] for row in cursor.fetchall()]
        
        # Adiciona símbolos sem volume no final
        cursor.execute('SELECT symbol FROM symbols WHERE volume = 0 ORDER BY symbol')
        symbols_without_volume = [row[0] for row in cursor.fetchall()]
        
        return symbols_with_volume + symbols_without_volume
    
    def get_symbol_volume(self, symbol: str) -> float:
        """Obtém volume de um símbolo"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT volume FROM symbols WHERE symbol = ?', (symbol,))
        result = cursor.fetchone()
        return float(result[0]) if result and result[0] else 0
    
    def get_all_timeframes(self) -> List[str]:
        """Obtém lista de todos os timeframes no banco"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT name FROM timeframes ORDER BY name')
        return [row[0] for row in cursor.fetchall()]
    
    def get_statistics(self, symbol: str, timeframe: str, limit: int = 100) -> Dict:
        """
        Calcula estatísticas dos dados usando queries otimizadas.
        
        Returns:
            Dicionário com estatísticas (média, min, max, etc)
        """
        symbol_id = self.get_or_create_symbol(symbol)
        timeframe_id = self.get_or_create_timeframe(timeframe)
        
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT 
                AVG(k_value) as k_avg,
                MIN(k_value) as k_min,
                MAX(k_value) as k_max,
                AVG(d_value) as d_avg,
                MIN(d_value) as d_min,
                MAX(d_value) as d_max,
                AVG(rsi_value) as rsi_avg,
                MIN(rsi_value) as rsi_min,
                MAX(rsi_value) as rsi_max,
                COUNT(*) as total_records
            FROM stoch_rsi_data 
            WHERE symbol_id = ? AND timeframe_id = ?
            LIMIT ?
        ''', (symbol_id, timeframe_id, limit))
        
        result = cursor.fetchone()
        if result:
            return {
                'k_avg': round(result[0], 4) if result[0] else None,
                'k_min': round(result[1], 4) if result[1] else None,
                'k_max': round(result[2], 4) if result[2] else None,
                'd_avg': round(result[3], 4) if result[3] else None,
                'd_min': round(result[4], 4) if result[4] else None,
                'd_max': round(result[5], 4) if result[5] else None,
                'rsi_avg': round(result[6], 4) if result[6] else None,
                'rsi_min': round(result[7], 4) if result[7] else None,
                'rsi_max': round(result[8], 4) if result[8] else None,
                'total_records': result[9]
            }
        return {}
    
    def export_to_json(self, filename: str = "results/stoch_rsi_export.json"):
        """
        Exporta todos os dados do banco para JSON.
        
        Args:
            filename: Caminho do arquivo de saída
        """
        import json
        from pathlib import Path
        
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT 
                s.symbol,
                t.name as timeframe,
                d.k_value, d.d_value, d.rsi_value,
                d.timestamp
            FROM stoch_rsi_data d
            JOIN symbols s ON d.symbol_id = s.id
            JOIN timeframes t ON d.timeframe_id = t.id
            ORDER BY s.symbol, t.name
        ''')
        
        data = {}
        for row in cursor.fetchall():
            symbol, timeframe, k, d, rsi, timestamp = row
            
            if symbol not in data:
                data[symbol] = {}
            if timeframe not in data[symbol]:
                data[symbol][timeframe] = []
            
            data[symbol][timeframe].append({
                'k': round(k, 4) if k else None,
                'd': round(d, 4) if d else None,
                'rsi': round(rsi, 4) if rsi else None,
                'timestamp': timestamp
            })
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Dados exportados para '{filename}'")
        return filename
