#!/bin/bash
# Initial project setup script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Conversational State Engine - Project Setup${NC}"

# Function to check command existence
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 is not installed.${NC}"
        return 1
    else
        echo -e "${GREEN}✅ $1 is installed${NC}"
        return 0
    fi
}

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"
MISSING_DEPS=0

if ! check_command "uv"; then
    echo -e "${BLUE}   Install uv: https://docs.astral.sh/uv/getting-started/installation/${NC}"
    MISSING_DEPS=1
fi

if ! check_command "pnpm"; then
    echo -e "${BLUE}   Install pnpm: npm install -g pnpm${NC}"
    MISSING_DEPS=1
fi

if ! check_command "node"; then
    echo -e "${BLUE}   Install Node.js: https://nodejs.org/${NC}"
    MISSING_DEPS=1
fi

if [ $MISSING_DEPS -eq 1 ]; then
    echo -e "${RED}❌ Please install missing dependencies before continuing.${NC}"
    exit 1
fi

# Setup Python environment
echo -e "${YELLOW}🐍 Setting up Python environment...${NC}"
uv sync

# Setup Node.js dependencies
echo -e "${YELLOW}📦 Installing Node.js dependencies...${NC}"
pnpm install

# Initialize database
echo -e "${YELLOW}🗄️  Initializing database...${NC}"
uv run python -c "
from server.app import init_db
init_db()
print('Database initialized successfully')
"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}📝 Creating .env file...${NC}"
    cat > .env << EOF
# Environment Configuration
CSE_DB_URL=sqlite:///state_engine.db
CSE_FEATURE_BATCH=false
CSE_LLM_PROVIDER=mock
EOF
fi

echo -e "${GREEN}🎉 Setup complete!${NC}"
echo -e "${YELLOW}📋 Next steps:${NC}"
echo "  1. Run 'pnpm run dev' to start development servers"
echo "  2. Visit http://localhost:5173 for the frontend"
echo "  3. Visit http://localhost:8000/docs for API documentation"
echo ""
echo -e "${BLUE}📚 Useful commands:${NC}"
echo "  pnpm run dev          - Start both servers"
echo "  pnpm run test         - Run all tests" 
echo "  pnpm run lint         - Lint all code"
echo "  pnpm run type-check   - Type check all code"