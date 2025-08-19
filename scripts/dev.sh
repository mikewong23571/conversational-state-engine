#!/bin/bash
# Development startup script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Conversational State Engine Development Environment${NC}"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ uv is not installed. Please install it first: https://docs.astral.sh/uv/getting-started/installation/${NC}"
    exit 1
fi

# Check if pnpm is installed
if ! command -v pnpm &> /dev/null; then
    echo -e "${RED}❌ pnpm is not installed. Please install it first: npm install -g pnpm${NC}"
    exit 1
fi

# Install dependencies
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
uv sync
pnpm install

# Check if this is the first run
if [ ! -f "state_engine.db" ]; then
    echo -e "${YELLOW}🗄️  Initializing database...${NC}"
    uv run python -c "
from server.app import init_db
init_db()
print('Database initialized successfully')
"
fi

echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo -e "${YELLOW}🚀 Choose how to start services:${NC}"
echo "  1) Both backend and frontend (recommended)"
echo "  2) Backend only"
echo "  3) Frontend only"
echo "  4) Just setup (don't start services)"
echo ""
read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo -e "${GREEN}🚀 Starting both backend and frontend...${NC}"
        echo -e "${YELLOW}📍 Services will be available at:${NC}"
        echo "  Backend:  http://localhost:8000"
        echo "  Frontend: http://localhost:5173"
        echo "  API Docs: http://localhost:8000/docs"
        echo ""
        echo -e "${YELLOW}💡 Press Ctrl+C to stop all services${NC}"
        echo ""
        exec pnpm run dev
        ;;
    2)
        echo -e "${GREEN}🚀 Starting backend only...${NC}"
        echo -e "${YELLOW}📍 Backend will be available at:${NC}"
        echo "  Backend:  http://localhost:8000"
        echo "  API Docs: http://localhost:8000/docs"
        echo ""
        echo -e "${YELLOW}💡 Press Ctrl+C to stop the service${NC}"
        echo ""
        exec pnpm run dev:backend
        ;;
    3)
        echo -e "${GREEN}🚀 Starting frontend only...${NC}"
        echo -e "${YELLOW}📍 Frontend will be available at:${NC}"
        echo "  Frontend: http://localhost:5173"
        echo ""
        echo -e "${YELLOW}💡 Press Ctrl+C to stop the service${NC}"
        echo ""
        exec pnpm run dev:frontend
        ;;
    4)
        echo -e "${GREEN}✅ Setup complete! Services not started.${NC}"
        echo ""
        echo -e "${YELLOW}📋 To start services manually:${NC}"
        echo "  pnpm run dev          - Start both backend and frontend"
        echo "  pnpm run dev:backend  - Start only backend server"
        echo "  pnpm run dev:frontend - Start only frontend"
        echo ""
        echo -e "${YELLOW}📋 Other available commands:${NC}"
        echo "  pnpm run test         - Run all tests"
        echo "  pnpm run lint         - Lint all code"
        echo "  pnpm run type-check   - Type check all code"
        ;;
    *)
        echo -e "${RED}❌ Invalid choice. Exiting without starting services.${NC}"
        echo ""
        echo -e "${YELLOW}📋 To start services manually:${NC}"
        echo "  pnpm run dev          - Start both backend and frontend"
        echo "  pnpm run dev:backend  - Start only backend server"
        echo "  pnpm run dev:frontend - Start only frontend"
        exit 1
        ;;
esac
