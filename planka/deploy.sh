#!/bin/bash
# ============================================================================
# Planka Deploy Script for MakerPi GroundControl
# Deploys a kanban board with GroundControl-matching theme
# ============================================================================

set -e

# Parse arguments
INTERACTIVE=false
if [ "$1" == "--interactive" ] || [ "$1" == "-i" ]; then
    INTERACTIVE=true
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PI_HOST="100.78.55.14"
PI_USER="dev"
REMOTE_DIR="/home/dev/planka"
PLANKA_PORT="3001"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Planka Deploy for MakerPi GroundControl${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if we can reach the Pi
echo -e "${YELLOW}Checking connection to Pi...${NC}"
if ! ping -c 1 -W 2 "$PI_HOST" &> /dev/null; then
    echo -e "${RED}Error: Cannot reach Pi at $PI_HOST${NC}"
    exit 1
fi
echo -e "${GREEN}Pi is reachable${NC}"
echo ""

# Generate a secret key if not already set
if [ -z "$PLANKA_SECRET_KEY" ]; then
    PLANKA_SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || head -c 64 /dev/urandom | xxd -p | tr -d '\n')
    echo -e "${YELLOW}Generated new secret key${NC}"
fi

# Create remote directory
echo -e "${YELLOW}Creating remote directory...${NC}"
ssh "$PI_USER@$PI_HOST" "mkdir -p $REMOTE_DIR"

# Copy files to Pi
echo -e "${YELLOW}Copying files to Pi...${NC}"
scp docker-compose.yml "$PI_USER@$PI_HOST:$REMOTE_DIR/"
scp custom.css "$PI_USER@$PI_HOST:$REMOTE_DIR/"

# Create .env file on Pi
echo -e "${YELLOW}Setting up environment...${NC}"
ssh "$PI_USER@$PI_HOST" "cat > $REMOTE_DIR/.env << 'EOF'
# Planka Configuration
PLANKA_SECRET_KEY=$PLANKA_SECRET_KEY
BASE_URL=http://$PI_HOST:$PLANKA_PORT
EOF"

# Check if Docker is installed on Pi
echo -e "${YELLOW}Checking Docker installation...${NC}"
if ! ssh "$PI_USER@$PI_HOST" "command -v docker &> /dev/null"; then
    echo -e "${YELLOW}Docker not found.${NC}"
    
    if [ "$INTERACTIVE" = true ]; then
        echo -e "${YELLOW}Installing Docker interactively (you'll be prompted for sudo password)...${NC}"
        # Use -t for pseudo-terminal to allow password entry
        ssh -t "$PI_USER@$PI_HOST" "
            curl -fsSL https://get.docker.com -o get-docker.sh && 
            sudo sh get-docker.sh && 
            sudo usermod -aG docker $PI_USER && 
            sudo apt-get install -y docker-compose-plugin && 
            rm get-docker.sh
        "
        echo -e "${YELLOW}Docker installed.${NC}"
        echo -e "${RED}IMPORTANT: Please log out and SSH back in, then re-run this script.${NC}"
        exit 0
    else
        echo -e "${RED}Docker not installed. Run with --interactive flag for auto-install:${NC}"
        echo -e "${YELLOW}  ./deploy.sh --interactive${NC}"
        echo ""
        echo -e "Or install manually by SSHing to the Pi and running:${NC}"
        echo -e "${YELLOW}  curl -fsSL https://get.docker.com | sudo sh${NC}"
        echo -e "${YELLOW}  sudo usermod -aG docker dev${NC}"
        echo -e "${YELLOW}  sudo apt-get install -y docker-compose-plugin${NC}"
        exit 1
    fi
fi

# Check if user can run docker without sudo
echo -e "${YELLOW}Checking Docker permissions...${NC}"
if ! ssh "$PI_USER@$PI_HOST" "docker ps &> /dev/null"; then
    if [ "$INTERACTIVE" = true ]; then
        echo -e "${YELLOW}Docker requires sudo. Will use sudo for docker commands (password may be prompted)...${NC}"
        DOCKER_PREFIX="sudo"
    else
        echo -e "${RED}Cannot run Docker commands. Either:${NC}"
        echo -e "  1. Add user to docker group: ${YELLOW}sudo usermod -aG docker dev${NC}, then re-login"
        echo -e "  2. Or run with --interactive: ${YELLOW}./deploy.sh --interactive${NC}"
        exit 1
    fi
else
    DOCKER_PREFIX=""
    echo -e "${GREEN}Docker permissions OK${NC}"
fi

# Deploy Planka
echo -e "${YELLOW}Deploying Planka...${NC}"

if [ "$INTERACTIVE" = true ] && [ "$DOCKER_PREFIX" = "sudo" ]; then
    # Use -t for interactive sudo password entry
    ssh -t "$PI_USER@$PI_HOST" "
        cd $REMOTE_DIR
        
        echo 'Pulling Docker images...'
        sudo docker compose pull
        
        echo 'Starting services...'
        sudo docker compose up -d
        
        echo 'Waiting for services to start (10s)...'
        sleep 10
        
        echo 'Checking service status...'
        if sudo docker compose ps | grep -q 'Up'; then
            echo 'Planka is running!'
        else
            echo 'Warning: Services may not have started properly'
            echo 'Last 20 log lines:'
            sudo docker compose logs --tail 20
        fi
    "
else
    ssh "$PI_USER@$PI_HOST" "
        cd $REMOTE_DIR
        
        # Pull latest images
        ${DOCKER_PREFIX}docker compose pull
        
        # Start services
        ${DOCKER_PREFIX}docker compose up -d
        
        # Wait for services to be ready
        echo 'Waiting for services to start...'
        sleep 10
        
        # Check if running
        if ${DOCKER_PREFIX}docker compose ps | grep -q 'Up'; then
            echo 'Planka is running!'
        else
            echo 'Warning: Services may not have started properly'
            ${DOCKER_PREFIX}docker compose logs --tail 20
        fi
    "
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Planka Deployed Successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Access URLs:"
echo -e "  Local network: ${YELLOW}http://192.168.3.228:$PLANKA_PORT${NC}"
echo -e "  Tailscale:     ${YELLOW}http://100.78.55.14:$PLANKA_PORT${NC}"
echo ""
echo -e "First time setup:"
echo -e "  1. Open either URL above in your browser"
echo -e "  2. Register your admin account"
echo -e "  3. Create boards and start tracking!"
echo ""
echo -e "Useful commands (run on Pi):"
echo -e "  ${YELLOW}sudo docker compose -C $REMOTE_DIR logs -f${NC}  # View logs"
echo -e "  ${YELLOW}sudo docker compose -C $REMOTE_DIR stop${NC}     # Stop Planka"
echo -e "  ${YELLOW}sudo docker compose -C $REMOTE_DIR start${NC}    # Start Planka"
echo -e "  ${YELLOW}sudo docker compose -C $REMOTE_DIR down${NC}      # Remove containers"
echo ""
echo -e "${GREEN}Enjoy your kanban board!${NC}"
