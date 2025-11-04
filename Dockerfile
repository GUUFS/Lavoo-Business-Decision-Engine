# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install Node.js 20.x
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy package files
COPY package*.json ./
COPY requirements.txt ./

# Install Node dependencies
RUN npm install

# Copy all project files
COPY . .

# Build frontend
RUN npm run build

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy start script
COPY start.py /app/start.py

# Expose port
EXPOSE 8000

# Start the application
CMD ["python", "start.py"]
