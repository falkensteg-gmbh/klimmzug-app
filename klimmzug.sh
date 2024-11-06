#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

# Variables
REPO_URL="https://github.com/falkensteg-gmbh/klimmzug-app.git"
PROJECT_DIR="klimmzug-app"

# Update and upgrade the system
sudo apt-get update -y
sudo apt-get upgrade -y

# Install necessary programs
sudo apt-get install -y git python3 python3-venv python3-pip

# Install Docker (official installation)
if ! command -v docker &> /dev/null; then
    echo "Docker not found, installing..."
    # Remove any older versions of Docker (optional)
    sudo apt-get remove -y docker docker.io containerd runc
    
    # Set up the Docker repository
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl gnupg lsb-release
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine and Docker Compose plugin
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
else
    echo "Docker is already installed."
fi

# Start and enable Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add current user to the docker group (requires re-login to take effect)
sudo usermod -aG docker $USER

# Clone the repository or pull latest changes
if [ -d "$PROJECT_DIR" ]; then
    cd $PROJECT_DIR
    git pull origin main
else
    git clone $REPO_URL
    cd $PROJECT_DIR
fi

# Build and start the Docker containers
docker compose up --build -d

# Print success message
echo "Deployment completed successfully! Please log out and log back in to apply Docker permissions."
