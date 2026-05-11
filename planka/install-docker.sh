#!/bin/bash
# Run this on the Pi to install Docker

echo "Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

echo "Adding user to docker group..."
sudo usermod -aG docker dev

echo "Installing docker-compose-plugin..."
sudo apt-get update
sudo apt-get install -y docker-compose-plugin

# Clean up
rm -f get-docker.sh

echo ""
echo "Docker installed! Please log out and SSH back in for group changes to take effect."
echo "Then run: cd ~/planka && docker compose up -d"
