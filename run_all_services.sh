#!/bin/bash

echo "Starting Event-Driven Image System..."
echo "========================================"

# Kill any existing services
pkill -f "processor_service.py" 2>/dev/null
pkill -f "storage_service.py" 2>/dev/null
pkill -f "embedding_service.py" 2>/dev/null
pkill -f "search_service.py" 2>/dev/null

# Start services in background
python3 processor_service.py &
echo "✓ Processor service started"

python3 storage_service.py &
echo "✓ Storage service started"

python3 embedding_service.py &
echo "✓ Embedding service started"

python3 search_service.py &
echo "✓ Search service started"

sleep 2
echo ""
echo "All services running. Starting CLI..."
echo "========================================"

# Run CLI in foreground
python3 cli_service.py

# Cleanup on exit
pkill -f "processor_service.py"
pkill -f "storage_service.py"
pkill -f "embedding_service.py"
pkill -f "search_service.py"
echo "All services stopped."
