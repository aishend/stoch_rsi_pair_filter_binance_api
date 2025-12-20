#!/usr/bin/env python3
"""
Script de teste para verificar se o banco de dados está funcional e acessível
Executa antes de rodar o programa principal
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Cores para output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    NC = '\033[0m'  # No Color
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.NC}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text:^70}{Colors.NC}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.NC}\n")

def print_ok(text):
    print(f"{Colors.GREEN}✓{Colors.NC} {text}")

def print_error(text):
    print(f"{Colors.RED}✗{Colors.NC} {text}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠{Colors.NC} {text}")

def print_info(text):
    print(f"{Colors.CYAN}ℹ{Colors.NC} {text}")

def check_db_path():
    """Verifica o caminho do banco de dados"""
    print_header("1. VERIFICANDO CAMINHO DO BANCO DE DADOS")
    
    # Obter do ambiente ou usar default
    db_path = os.getenv('DATABASE_PATH', 'data/stoch_rsi.db')
    print_info(f"Caminho definido: {db_path}")
    
    # Verificar se é caminho absoluto ou relativo
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.getcwd(), db_path)
        print_info(f"Convertendo para caminho absoluto: {db_path}")
    
    return db_path

def check_file_exists(db_path):
    """Verifica se o arquivo do banco existe"""
    print_header("2. VERIFICANDO EXISTÊNCIA DO ARQUIVO")
    
    if os.path.exists(db_path):
        print_ok(f"Arquivo existe: {db_path}")
        
        # Verificar tamanho
        size = os.path.getsize(db_path)
        print_info(f"Tamanho: {size:,} bytes ({size / 1024:.2f} KB)")
        
        # Verificar data de modificação
        mtime = os.path.getmtime(db_path)
        mod_time = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        print_info(f"Última modificação: {mod_time}")
        
        return True
    else:
        print_error(f"Arquivo NÃO existe: {db_path}")
        return False

def check_file_permissions(db_path):
    """Verifica permissões do arquivo"""
    print_header("3. VERIFICANDO PERMISSÕES")
    
    if not os.path.exists(db_path):
        print_warning("Arquivo não existe, pulando verificação de permissões")
        return False
    
    # Verificar leitura
    if os.access(db_path, os.R_OK):
        print_ok("✓ Arquivo é legível (read permission)")
    else:
        print_error("✗ Arquivo NÃO é legível")
        return False
    
    # Verificar escrita
    if os.access(db_path, os.W_OK):
        print_ok("✓ Arquivo é gravável (write permission)")
    else:
        print_error("✗ Arquivo NÃO é gravável")
        return False
    
    # Mostrar permissões
    mode = os.stat(db_path).st_mode
    octal = oct(mode)[-3:]
    print_info(f"Permissões: {octal}")
    
    return True

def check_db_connection(db_path):
    """Tenta conectar ao banco de dados"""
    print_header("4. TESTANDO CONEXÃO COM O BANCO")
    
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print_ok(f"Conexão estabelecida com sucesso")
        
        return conn, cursor
    except sqlite3.Error as e:
        print_error(f"Erro ao conectar: {e}")
        return None, None
    except Exception as e:
        print_error(f"Erro inesperado: {e}")
        return None, None

def check_tables(cursor):
    """Verifica se as tabelas existem"""
    print_header("5. VERIFICANDO TABELAS")
    
    if cursor is None:
        print_error("Cursor não disponível")
        return False
    
    required_tables = ['symbols', 'timeframes', 'stoch_rsi_data', 'stoch_rsi_history']
    found_tables = []
    missing_tables = []
    
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        print_info(f"Tabelas encontradas: {len(existing_tables)}")
        for table in existing_tables:
            print_info(f"  • {table}")
        
        for table in required_tables:
            if table in existing_tables:
                found_tables.append(table)
                print_ok(f"✓ Tabela '{table}' existe")
            else:
                missing_tables.append(table)
                print_warning(f"⚠ Tabela '{table}' NÃO existe")
        
        if missing_tables:
            print_warning(f"\n{len(missing_tables)} tabela(s) necessária(s) não encontrada(s)")
            return False
        else:
            print_ok(f"\n✓ Todas as {len(required_tables)} tabelas necessárias existem")
            return True
            
    except sqlite3.Error as e:
        print_error(f"Erro ao consultar tabelas: {e}")
        return False

def check_table_structure(cursor):
    """Verifica a estrutura das tabelas"""
    print_header("6. VERIFICANDO ESTRUTURA DAS TABELAS")
    
    if cursor is None:
        print_error("Cursor não disponível")
        return False
    
    tables_info = {
        'symbols': ['symbol', 'volume'],
        'timeframes': ['name'],
        'stoch_rsi_data': ['symbol_id', 'timeframe_id', 'k_value', 'd_value', 'rsi_value'],
        'stoch_rsi_history': ['symbol_id', 'timeframe_id', 'k_value', 'd_value', 'rsi_value']
    }
    
    all_ok = True
    
    for table, expected_cols in tables_info.items():
        try:
            cursor.execute(f"PRAGMA table_info({table});")
            columns = [row[1] for row in cursor.fetchall()]
            
            print_info(f"Tabela '{table}':")
            
            for col in expected_cols:
                if col in columns:
                    print_ok(f"  ✓ Coluna '{col}' existe")
                else:
                    print_warning(f"  ⚠ Coluna '{col}' NÃO existe")
                    all_ok = False
            
        except sqlite3.Error as e:
            print_error(f"Erro ao verificar tabela '{table}': {e}")
            all_ok = False
    
    return all_ok

def check_data_count(cursor):
    """Verifica quantidade de dados em cada tabela"""
    print_header("7. VERIFICANDO DADOS NAS TABELAS")
    
    if cursor is None:
        print_error("Cursor não disponível")
        return False
    
    tables = ['symbols', 'stoch_rsi_data', 'stoch_rsi_history']
    
    try:
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]
            
            if count > 0:
                print_ok(f"Tabela '{table}': {count:,} registros")
            else:
                print_warning(f"Tabela '{table}': vazia")
        
        return True
        
    except sqlite3.Error as e:
        print_error(f"Erro ao contar registros: {e}")
        return False

def test_insert_read(cursor):
    """Testa operação de insert e read"""
    print_header("8. TESTANDO OPERAÇÕES (INSERT/READ)")
    
    if cursor is None:
        print_error("Cursor não disponível")
        return False
    
    try:
        # Tentar ler dados existentes
        cursor.execute("""
            SELECT s.symbol, COUNT(sr.id) as data_count 
            FROM symbols s 
            LEFT JOIN stoch_rsi_data sr ON s.id = sr.symbol_id 
            GROUP BY s.id 
            LIMIT 1
        """)
        result = cursor.fetchone()
        
        if result:
            symbol = result[0]
            data_count = result[1]
            print_ok(f"✓ Leitura (SELECT) funcionando")
            print_info(f"  Símbolo lido: {symbol}")
            print_info(f"  Dados de Stoch RSI: {data_count} registros")
        else:
            print_warning("⚠ Nenhum símbolo encontrado na tabela (banco vazio)")
        
        # Verificar índices
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%';")
        indices = [row[0] for row in cursor.fetchall()]
        if indices:
            print_ok(f"✓ Índices encontrados: {len(indices)}")
            for idx in indices:
                print_info(f"  • {idx}")
        
        return True
        
    except sqlite3.Error as e:
        print_error(f"Erro ao testar operações: {e}")
        return False

def main():
    """Função principal"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║         TESTE DE BANCO DE DADOS - Stochastic RSI                   ║")
    print("║         Data: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " " * 25 + "║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.NC}\n")
    
    # Executar verificações
    results = {}
    
    # 1. Caminho
    db_path = check_db_path()
    
    # 2. Arquivo existe
    results['file_exists'] = check_file_exists(db_path)
    
    # 3. Permissões
    results['permissions'] = check_file_permissions(db_path)
    
    # 4. Conexão
    conn, cursor = check_db_connection(db_path)
    results['connection'] = conn is not None
    
    # 5-8. Testes de banco (se conectou)
    if conn is not None:
        results['tables'] = check_tables(cursor)
        results['structure'] = check_table_structure(cursor)
        results['data_count'] = check_data_count(cursor)
        results['operations'] = test_insert_read(cursor)
        
        cursor.close()
        conn.close()
        print_ok("Conexão fechada")
    
    # Resumo final
    print_header("RESUMO DOS TESTES")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print_info(f"Testes passados: {passed}/{total}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ TODOS OS TESTES PASSARAM!{Colors.NC}")
        print(f"{Colors.GREEN}Banco de dados está funcional e pronto para usar.{Colors.NC}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ ALGUNS TESTES FALHARAM{Colors.NC}")
        print(f"{Colors.YELLOW}Verifique os erros acima antes de rodar o programa.{Colors.NC}\n")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
