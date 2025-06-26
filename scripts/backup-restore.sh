#!/bin/bash

# Zazzle Agent Backup and Restore Script
# This script handles backup and restore operations for the application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

info() {
    echo -e "${PURPLE}ℹ️  $1${NC}"
}

# Configuration
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="zazzle_agent_backup_${TIMESTAMP}.tar.gz"

# Create backup directory if it doesn't exist
create_backup_dir() {
    mkdir -p "$BACKUP_DIR"
}

# Create backup
create_backup() {
    log "Creating backup..."
    
    create_backup_dir
    
    # Stop services to ensure data consistency
    log "Stopping services for consistent backup..."
    docker-compose down
    
    # Create backup archive
    log "Creating backup archive..."
    tar -czf "$BACKUP_DIR/$BACKUP_NAME" \
        --exclude='./backups' \
        --exclude='./node_modules' \
        --exclude='./.git' \
        --exclude='./__pycache__' \
        --exclude='./*.pyc' \
        --exclude='./.coverage' \
        --exclude='./htmlcov' \
        --exclude='./.pytest_cache' \
        --exclude='./frontend/node_modules' \
        --exclude='./frontend/dist' \
        --exclude='./frontend/.vite' \
        .
    
    # Restart services
    log "Restarting services..."
    docker-compose up -d
    
    success "Backup created: $BACKUP_DIR/$BACKUP_NAME"
    
    # Show backup size
    local size=$(du -h "$BACKUP_DIR/$BACKUP_NAME" | cut -f1)
    info "Backup size: $size"
}

# List available backups
list_backups() {
    log "Available backups:"
    echo ""
    
    if [[ ! -d "$BACKUP_DIR" ]] || [[ -z "$(ls -A $BACKUP_DIR 2>/dev/null)" ]]; then
        warning "No backups found"
        return
    fi
    
    echo "Backup files in $BACKUP_DIR:"
    echo ""
    
    for backup in "$BACKUP_DIR"/*.tar.gz; do
        if [[ -f "$backup" ]]; then
            local filename=$(basename "$backup")
            local size=$(du -h "$backup" | cut -f1)
            local date=$(echo "$filename" | sed 's/zazzle_agent_backup_\(.*\)\.tar\.gz/\1/' | sed 's/_/ /g')
            echo "  📦 $filename"
            echo "     Size: $size"
            echo "     Date: $date"
            echo ""
        fi
    done
}

# Restore from backup
restore_backup() {
    local backup_file="$1"
    
    if [[ -z "$backup_file" ]]; then
        error "No backup file specified"
        echo ""
        echo "Usage: $0 restore <backup_file>"
        echo ""
        echo "Available backups:"
        list_backups
        exit 1
    fi
    
    # Check if backup file exists
    if [[ ! -f "$backup_file" ]]; then
        # Try to find it in backup directory
        if [[ -f "$BACKUP_DIR/$backup_file" ]]; then
            backup_file="$BACKUP_DIR/$backup_file"
        else
            error "Backup file not found: $backup_file"
            exit 1
        fi
    fi
    
    log "Restoring from backup: $backup_file"
    
    # Confirm restoration
    echo ""
    warning "This will overwrite the current application data!"
    echo "Are you sure you want to continue? (y/N)"
    read -r response
    
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        info "Restoration cancelled"
        exit 0
    fi
    
    # Stop services
    log "Stopping services..."
    docker-compose down
    
    # Create backup of current state before restore
    log "Creating backup of current state..."
    create_backup_dir
    local current_backup="zazzle_agent_pre_restore_${TIMESTAMP}.tar.gz"
    tar -czf "$BACKUP_DIR/$current_backup" \
        --exclude='./backups' \
        --exclude='./node_modules' \
        --exclude='./.git' \
        --exclude='./__pycache__' \
        --exclude='./*.pyc' \
        --exclude='./.coverage' \
        --exclude='./htmlcov' \
        --exclude='./.pytest_cache' \
        --exclude='./frontend/node_modules' \
        --exclude='./frontend/dist' \
        --exclude='./frontend/.vite' \
        .
    
    info "Current state backed up as: $BACKUP_DIR/$current_backup"
    
    # Extract backup
    log "Extracting backup..."
    tar -xzf "$backup_file"
    
    # Restart services
    log "Restarting services..."
    docker-compose up -d
    
    success "Restoration completed successfully"
    info "Previous state backed up as: $BACKUP_DIR/$current_backup"
}

# Clean old backups
clean_backups() {
    local days="$1"
    
    if [[ -z "$days" ]]; then
        days=30  # Default to 30 days
    fi
    
    log "Cleaning backups older than $days days..."
    
    if [[ ! -d "$BACKUP_DIR" ]]; then
        warning "No backup directory found"
        return
    fi
    
    local deleted_count=0
    
    # Find and delete old backups
    while IFS= read -r -d '' file; do
        if [[ -f "$file" ]]; then
            rm "$file"
            ((deleted_count++))
            info "Deleted: $(basename "$file")"
        fi
    done < <(find "$BACKUP_DIR" -name "*.tar.gz" -mtime +"$days" -print0)
    
    if [[ $deleted_count -eq 0 ]]; then
        info "No old backups found to delete"
    else
        success "Deleted $deleted_count old backup(s)"
    fi
}

# Database-specific backup
backup_database() {
    log "Creating database backup..."
    
    create_backup_dir
    
    if [[ -f "data/zazzle_pipeline.db" ]]; then
        local db_backup="database_backup_${TIMESTAMP}.db"
        cp "data/zazzle_pipeline.db" "$BACKUP_DIR/$db_backup"
        
        local size=$(du -h "$BACKUP_DIR/$db_backup" | cut -f1)
        success "Database backed up: $BACKUP_DIR/$db_backup (Size: $size)"
    else
        error "Database file not found"
        exit 1
    fi
}

# Database-specific restore
restore_database() {
    local db_file="$1"
    
    if [[ -z "$db_file" ]]; then
        error "No database file specified"
        echo ""
        echo "Usage: $0 restore-db <database_file>"
        echo ""
        echo "Available database backups:"
        if [[ -d "$BACKUP_DIR" ]]; then
            for db in "$BACKUP_DIR"/database_backup_*.db; do
                if [[ -f "$db" ]]; then
                    local filename=$(basename "$db")
                    local size=$(du -h "$db" | cut -f1)
                    echo "  📊 $filename (Size: $size)"
                fi
            done
        fi
        exit 1
    fi
    
    # Check if database file exists
    if [[ ! -f "$db_file" ]]; then
        # Try to find it in backup directory
        if [[ -f "$BACKUP_DIR/$db_file" ]]; then
            db_file="$BACKUP_DIR/$db_file"
        else
            error "Database file not found: $db_file"
            exit 1
        fi
    fi
    
    log "Restoring database from: $db_file"
    
    # Confirm restoration
    echo ""
    warning "This will overwrite the current database!"
    echo "Are you sure you want to continue? (y/N)"
    read -r response
    
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        info "Database restoration cancelled"
        exit 0
    fi
    
    # Stop services
    log "Stopping services..."
    docker-compose down
    
    # Backup current database
    if [[ -f "data/zazzle_pipeline.db" ]]; then
        log "Backing up current database..."
        local current_db_backup="database_pre_restore_${TIMESTAMP}.db"
        cp "data/zazzle_pipeline.db" "$BACKUP_DIR/$current_db_backup"
        info "Current database backed up as: $BACKUP_DIR/$current_db_backup"
    fi
    
    # Restore database
    log "Restoring database..."
    cp "$db_file" "data/zazzle_pipeline.db"
    
    # Restart services
    log "Restarting services..."
    docker-compose up -d
    
    success "Database restoration completed successfully"
}

# Show backup statistics
show_stats() {
    log "Backup Statistics"
    echo "================="
    
    if [[ ! -d "$BACKUP_DIR" ]]; then
        warning "No backup directory found"
        return
    fi
    
    local total_backups=$(find "$BACKUP_DIR" -name "*.tar.gz" | wc -l)
    local total_db_backups=$(find "$BACKUP_DIR" -name "database_backup_*.db" | wc -l)
    local total_size=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1 || echo "0")
    
    echo "Total full backups: $total_backups"
    echo "Total database backups: $total_db_backups"
    echo "Total backup size: $total_size"
    echo ""
    
    if [[ $total_backups -gt 0 ]]; then
        echo "Recent backups:"
        find "$BACKUP_DIR" -name "*.tar.gz" -printf "%T@ %p\n" | sort -nr | head -5 | while read -r timestamp file; do
            local filename=$(basename "$file")
            local size=$(du -h "$file" | cut -f1)
            local date=$(date -d "@$timestamp" '+%Y-%m-%d %H:%M:%S')
            echo "  📦 $filename (Size: $size, Date: $date)"
        done
    fi
}

# Main function
main() {
    echo "💾 Zazzle Agent Backup and Restore"
    echo "=================================="
    echo ""
    
    # Parse command line arguments
    case "${1:-}" in
        "backup")
            create_backup
            ;;
        "restore")
            restore_backup "$2"
            ;;
        "list")
            list_backups
            ;;
        "clean")
            clean_backups "$2"
            ;;
        "backup-db")
            backup_database
            ;;
        "restore-db")
            restore_database "$2"
            ;;
        "stats")
            show_stats
            ;;
        "help"|"--help"|"-h"|"")
            echo "Usage: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  backup              Create a full backup of the application"
            echo "  restore <file>      Restore from a backup file"
            echo "  list                List available backups"
            echo "  clean [days]        Clean backups older than N days (default: 30)"
            echo "  backup-db           Create a database-only backup"
            echo "  restore-db <file>   Restore database from backup"
            echo "  stats               Show backup statistics"
            echo "  help                Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 backup"
            echo "  $0 restore zazzle_agent_backup_20241201_120000.tar.gz"
            echo "  $0 clean 7"
            echo "  $0 backup-db"
            echo "  $0 restore-db database_backup_20241201_120000.db"
            echo ""
            ;;
        *)
            error "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@" 