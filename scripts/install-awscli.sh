# Download the installer package
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"

# Unzip the installer package
unzip awscliv2.zip

# Run the installation script
sudo ./aws/install

# Remove the packages after installation
sudo rm -rf ~/.aws
