#!/bin/bash

# SQLAlchemy Performance Cookbook - Deployment Script
# This script handles deployment to different environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="development"
BUILD_IMAGES=true
RUN_TESTS=true
SEED_DATA=true

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV    Set environment (development, staging, production)"
    echo "  -n, --no-build          Skip building Docker images"
    echo "  -t, --no-tests          Skip running tests"
    echo "  -s, --no-seed           Skip seeding data"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Deploy to development"
    echo "  $0 -e production -n                  # Deploy to production without building"
    echo "  $0 -e staging -t -s                  # Deploy to staging, skip tests and seeding"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -n|--no-build)
            BUILD_IMAGES=false
            shift
            ;;
        -t|--no-tests)
            RUN_TESTS=false
            shift
            ;;
        -s|--no-seed)
            SEED_DATA=false
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

print_status "Starting deployment for environment: $ENVIRONMENT"

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    print_error "Invalid environment: $ENVIRONMENT"
    print_error "Valid environments: development, staging, production"
    exit 1
fi

# Set environment-specific variables
case $ENVIRONMENT in
    development)
        COMPOSE_FILE="docker-compose.yml"
        ENV_FILE=".env"
        ;;
    staging)
        COMPOSE_FILE="docker-compose.staging.yml"
        ENV_FILE=".env.staging"
        ;;
    production)
        COMPOSE_FILE="docker-compose.prod.yml"
        ENV_FILE=".env.production"
        ;;
esac

# Check if compose file exists
if [[ ! -f "$COMPOSE_FILE" ]]; then
    print_warning "Compose file $COMPOSE_FILE not found, using default docker-compose.yml"
    COMPOSE_FILE="docker-compose.yml"
fi

# Check if env file exists
if [[ ! -f "$ENV_FILE" ]]; then
    print_warning "Environment file $ENV_FILE not found, using .env"
    ENV_FILE=".env"
fi

# Build images if requested
if [[ "$BUILD_IMAGES" == true ]]; then
    print_status "Building Docker images..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build
fi

# Run tests if requested
if [[ "$RUN_TESTS" == true ]]; then
    print_status "Running tests..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" run --rm api pytest
fi

# Stop existing containers
print_status "Stopping existing containers..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down

# Start services
print_status "Starting services..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 10

# Check service health
print_status "Checking service health..."
if ! docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps | grep -q "Up"; then
    print_error "Some services failed to start"
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs
    exit 1
fi

# Seed data if requested
if [[ "$SEED_DATA" == true ]]; then
    print_status "Seeding data..."
    sleep 5  # Give API time to start
    
    # Try to seed admin user
    if curl -f -X POST http://localhost:8000/auth/seed > /dev/null 2>&1; then
        print_status "Admin user seeded successfully"
    else
        print_warning "Failed to seed admin user (API might not be ready yet)"
    fi
fi

# Show service status
print_status "Deployment completed successfully!"
echo ""
echo "Services status:"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
echo ""
echo "API is available at: http://localhost:8000"
echo "API documentation: http://localhost:8000/docs"
echo ""
echo "To view logs: docker compose -f $COMPOSE_FILE --env-file $ENV_FILE logs -f"
echo "To stop services: docker compose -f $COMPOSE_FILE --env-file $ENV_FILE down"
