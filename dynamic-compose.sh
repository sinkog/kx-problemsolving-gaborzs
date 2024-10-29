#!/bin/bash

# Default values
NUM_STORAGE_CONTAINERS=3
LOG_LEVEL=INFO

# Handle parameters
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    -n|--num_containers) NUM_STORAGE_CONTAINERS="$2"; shift 2;;
    -l|--log_level) LOG_LEVEL="$2"; shift 2;;
    -h|--help)
      echo "Usage: $0 [-n number_of_containers] [-l ERROR/WARNING/INFO/DEBUG/CRITICAL]"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1;;
  esac
done


# Generating Docker Compose file based on the number of storage containers
cat <<EOF > dyn-docker-compose.yaml
version: '3.8'

services:
  gateway-service:
    build:
      context: ./gateway-service
      dockerfile: Dockerfile
    ports:
      - "8080:5000"
    environment:
      - STORAGE_SERVICES=$(for i in $(seq 1 $NUM_STORAGE_CONTAINERS); do echo -n "http://storage$i:5000,"; done | sed 's/,$//')
      - LOG_LEVEL=$LOG_LEVEL
    networks:
      - my-network
    restart: always
EOF

# Creating storage services
for i in $(seq 1 $NUM_STORAGE_CONTAINERS); do
  cat <<EOF >> dyn-docker-compose.yaml

  storage$i:
    build:
      context: ./storage-service
      dockerfile: Dockerfile
    ports:
      - "500$i:5000"
    networks:
      - my-network
    restart: always
EOF
done

# Setting up the network
cat <<EOF >> dyn-docker-compose.yaml

networks:
  my-network:
    driver: bridge
EOF
