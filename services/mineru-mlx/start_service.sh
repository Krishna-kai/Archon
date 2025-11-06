#!/bin/bash
# MinerU MLX Service Startup Script
# Manages virtual environment and starts the FastAPI service on port 9006
# Optimized for Apple Silicon with Metal GPU acceleration

set -e  # Exit on error

# ==================== Configuration ====================
export PORT=${PORT:-9006}
export HOST=${HOST:-0.0.0.0}
export LOG_LEVEL=${LOG_LEVEL:-info}
export PYTHONUNBUFFERED=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
LOG_DIR="$SCRIPT_DIR/logs"
PYTHON_VERSION="python3.12"

# ==================== Helper Functions ====================

log_info() {
    echo "ℹ️  $1"
}

log_success() {
    echo "✅ $1"
}

log_error() {
    echo "❌ $1"
}

log_warning() {
    echo "⚠️  $1"
}

check_python() {
    if ! command -v $PYTHON_VERSION &> /dev/null; then
        log_warning "$PYTHON_VERSION not found, trying python3..."
        PYTHON_VERSION="python3"
        if ! command -v $PYTHON_VERSION &> /dev/null; then
            log_error "Python 3.12+ is required but not found"
            exit 1
        fi
    fi
    log_success "Using $($PYTHON_VERSION --version)"
}

create_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        log_info "Creating virtual environment..."
        $PYTHON_VERSION -m venv "$VENV_DIR"
        log_success "Virtual environment created"
    else
        log_info "Virtual environment already exists"
    fi
}

activate_venv() {
    log_info "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
    log_success "Virtual environment activated"
}

install_dependencies() {
    log_info "Checking dependencies..."

    # Upgrade pip first
    pip install --quiet --upgrade pip

    # Check if requirements are already installed
    if pip list | grep -q "fastapi"; then
        log_info "Dependencies appear to be installed"
        read -p "📦 Reinstall dependencies? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Skipping dependency installation"
            return
        fi
    fi

    log_info "Installing dependencies from requirements.txt..."
    pip install -r "$SCRIPT_DIR/requirements.txt"
    log_success "Dependencies installed"
}

create_log_dir() {
    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR"
        log_success "Log directory created: $LOG_DIR"
    fi
}

check_port() {
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_warning "Port $PORT is already in use"
        read -p "⚠️  Kill the process and continue? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            local PID=$(lsof -Pi :$PORT -sTCP:LISTEN -t)
            kill -9 $PID 2>/dev/null || true
            sleep 1
            log_success "Process on port $PORT terminated"
        else
            log_error "Cannot start service - port $PORT is in use"
            exit 1
        fi
    fi
}

health_check() {
    log_info "Performing health check..."
    sleep 3  # Wait for service to start

    if curl -sf http://localhost:$PORT/health > /dev/null; then
        log_success "Health check passed - service is running"
        return 0
    else
        log_warning "Health check failed - service may still be starting"
        return 1
    fi
}

# ==================== Main Script ====================

main() {
    echo "════════════════════════════════════════════════════════════"
    echo "🚀 MinerU MLX Service Startup"
    echo "════════════════════════════════════════════════════════════"
    echo ""

    # Check Python
    check_python

    # Setup environment
    create_venv
    activate_venv
    install_dependencies
    create_log_dir

    # Check port availability
    check_port

    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "🌐 Starting MinerU MLX Service"
    echo "════════════════════════════════════════════════════════════"
    echo "📍 Port: $PORT"
    echo "🖥️  Host: $HOST"
    echo "📝 Log Level: $LOG_LEVEL"
    echo "🔥 Backend: MinerU with Apple Metal GPU"
    echo "📁 Working Dir: $SCRIPT_DIR"
    echo "📂 Logs: $LOG_DIR"
    echo "════════════════════════════════════════════════════════════"
    echo ""

    # Start service with uvicorn
    cd "$SCRIPT_DIR"

    # Start in foreground with live output
    exec uvicorn app:app \
        --host $HOST \
        --port $PORT \
        --reload \
        --log-level $LOG_LEVEL \
        --access-log
}

# ==================== Script Entry Point ====================

# Trap Ctrl+C and cleanup
trap 'echo ""; log_info "Shutting down..."; exit 0' INT TERM

# Run main function
main
