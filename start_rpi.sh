#!/bin/bash

# Script para iniciar o sistema no Raspberry Pi com banco de dados LOCAL
# Cada RPi tem seu próprio banco de dados separado

set -e

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detectar diretório do projeto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Usar banco de dados LOCAL no RPi (não compartilhado pela rede)
export DATABASE_PATH="$PROJECT_DIR/data/stoch_rsi_local.db"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Stochastic RSI Dashboard - Raspberry Pi              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}📁 Projeto: $PROJECT_DIR${NC}"
echo -e "${YELLOW}📊 Banco (LOCAL): $DATABASE_PATH${NC}"
echo ""

# Criar diretórios de logs
mkdir -p logs data results

# Verificar se venv existe
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}[!] Criando ambiente virtual...${NC}"
    python3 -m venv venv
fi

# Ativar venv
echo -e "${YELLOW}[*] Ativando ambiente virtual...${NC}"
source venv/bin/activate

# Instalar dependências
echo -e "${YELLOW}[*] Verificando dependências...${NC}"
pip install -q flask flask-cors requests

echo ""
echo -e "${GREEN}✓ Ambiente pronto${NC}"
echo ""

# Iniciar servidor API em background
echo -e "${BLUE}[1/2] Iniciando API Server...${NC}"
nohup python3 api_server.py > logs/api_server.log 2>&1 &
API_PID=$!
echo -e "${GREEN}✓ API Server iniciado (PID: $API_PID)${NC}"
sleep 2

# Iniciar loop de atualização em background
echo -e "${BLUE}[2/2] Iniciando loop de atualização...${NC}"
nohup python3 update_loop.py > logs/update_loop.log 2>&1 &
UPDATE_PID=$!
echo -e "${GREEN}✓ Loop de atualização iniciado (PID: $UPDATE_PID)${NC}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ Sistema iniciado com sucesso!                      ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "🌐 Dashboard:  http://$(hostname -I | awk '{print $1}'):8000"
echo -e "📊 Banco LOCAL: $DATABASE_PATH"
echo -e "📋 Logs API:   tail -f logs/api_server.log"
echo -e "🔄 Logs Loop:  tail -f logs/update_loop.log"
echo ""
echo "Para parar: pkill -f 'python.*api_server.py|python.*update_loop.py'"
echo ""

# Manter script ativo
wait
