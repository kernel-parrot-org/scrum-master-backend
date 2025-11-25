#!/bin/bash
# Reset PostgreSQL database volume
echo "Stopping containers..."
docker-compose down

echo "Removing postgres volume..."
docker volume rm scrum-master-backend_postgres_data 2>/dev/null || true

echo "Starting containers..."
docker-compose up -d

echo "Database reset complete. Wait for postgres to be healthy before running migrations."

