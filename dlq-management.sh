#!/bin/bash

# Data Prepper Dead Letter Queue Management Script
# This script provides utilities for managing DLQ files and error handling

set -euo pipefail

# Configuration
DLQ_BASE_DIR="/usr/share/data-prepper/data/dlq"
ARCHIVE_DIR="${DLQ_BASE_DIR}/archive"
LOG_FILE="/var/log/dlq-management.log"
MAX_DLQ_SIZE="1gb"
DEFAULT_RETENTION_DAYS=7

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${LOG_FILE}"
}

# Function to display usage
usage() {
    cat << EOF
Data Prepper DLQ Management Script

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    status          Show DLQ status and statistics
    list            List all DLQ files
    cleanup         Clean up old DLQ files based on retention policy
    reprocess       Reprocess DLQ files
    archive         Archive processed DLQ files
    monitor         Monitor DLQ size and file count
    validate        Validate DLQ file format and content
    export          Export DLQ data for analysis
    help            Show this help message

Options:
    --dry-run       Show what would be done without executing
    --verbose       Enable verbose output
    --retention     Override default retention days (default: ${DEFAULT_RETENTION_DAYS})
    --category      Filter by error category (validation, sink, critical)
    --date          Filter by date (YYYY-MM-DD format)

Examples:
    $0 status
    $0 cleanup --retention 3 --dry-run
    $0 reprocess --category sink_failures
    $0 monitor --verbose
    $0 export --date 2024-01-15 --category validation

EOF
}

# Function to get DLQ statistics
get_dlq_stats() {
    local total_files=0
    local total_size=0
    local categories=()
    
    if [[ -d "${DLQ_BASE_DIR}" ]]; then
        while IFS= read -r -d '' file; do
            if [[ -f "$file" ]]; then
                ((total_files++))
                local size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
                ((total_size += size))
                
                # Extract category from filename
                local basename=$(basename "$file")
                local category=$(echo "$basename" | cut -d'-' -f2-3)
                if [[ ! " ${categories[*]} " =~ " ${category} " ]]; then
                    categories+=("$category")
                fi
            fi
        done < <(find "${DLQ_BASE_DIR}" -name "*.json" -print0 2>/dev/null || true)
    fi
    
    echo "total_files:$total_files"
    echo "total_size:$total_size"
    echo "categories:${categories[*]}"
}

# Function to show DLQ status
show_status() {
    log "INFO" "Checking DLQ status..."
    
    echo -e "${BLUE}=== Data Prepper DLQ Status ===${NC}"
    echo
    
    if [[ ! -d "${DLQ_BASE_DIR}" ]]; then
        echo -e "${YELLOW}DLQ directory does not exist: ${DLQ_BASE_DIR}${NC}"
        return 0
    fi
    
    local stats=$(get_dlq_stats)
    local total_files=$(echo "$stats" | grep "total_files:" | cut -d':' -f2)
    local total_size=$(echo "$stats" | grep "total_size:" | cut -d':' -f2)
    local categories=$(echo "$stats" | grep "categories:" | cut -d':' -f2-)
    
    # Convert size to human readable
    local human_size=$(numfmt --to=iec-i --suffix=B "$total_size" 2>/dev/null || echo "${total_size} bytes")
    
    echo -e "Total DLQ Files: ${GREEN}${total_files}${NC}"
    echo -e "Total DLQ Size: ${GREEN}${human_size}${NC}"
    echo -e "Error Categories: ${GREEN}${categories}${NC}"
    echo
    
    # Check if size exceeds threshold
    local max_size_bytes=$(numfmt --from=iec "${MAX_DLQ_SIZE}" 2>/dev/null || echo 1073741824)
    if [[ $total_size -gt $max_size_bytes ]]; then
        echo -e "${RED}WARNING: DLQ size exceeds threshold (${MAX_DLQ_SIZE})${NC}"
    fi
    
    # Show recent files
    echo -e "${BLUE}Recent DLQ Files:${NC}"
    find "${DLQ_BASE_DIR}" -name "*.json" -type f -exec ls -lh {} \; 2>/dev/null | head -10 || echo "No DLQ files found"
}

# Function to list DLQ files
list_dlq_files() {
    local category_filter=""
    local date_filter=""
    local verbose=false
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --category)
                category_filter="$2"
                shift 2
                ;;
            --date)
                date_filter="$2"
                shift 2
                ;;
            --verbose)
                verbose=true
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    log "INFO" "Listing DLQ files (category: ${category_filter:-all}, date: ${date_filter:-all})"
    
    local find_pattern="*.json"
    if [[ -n "$category_filter" ]]; then
        find_pattern="*${category_filter}*.json"
    fi
    
    echo -e "${BLUE}=== DLQ Files ===${NC}"
    
    if [[ ! -d "${DLQ_BASE_DIR}" ]]; then
        echo "No DLQ directory found"
        return 0
    fi
    
    local count=0
    while IFS= read -r -d '' file; do
        if [[ -f "$file" ]]; then
            local basename=$(basename "$file")
            
            # Apply date filter if specified
            if [[ -n "$date_filter" && "$basename" != *"$date_filter"* ]]; then
                continue
            fi
            
            ((count++))
            
            if [[ "$verbose" == true ]]; then
                local size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
                local human_size=$(numfmt --to=iec-i --suffix=B "$size" 2>/dev/null || echo "${size}B")
                local mtime=$(stat -f%Sm -t%Y-%m-%d\ %H:%M:%S "$file" 2>/dev/null || stat -c%y "$file" 2>/dev/null | cut -d'.' -f1)
                echo -e "${GREEN}${basename}${NC} (${human_size}, ${mtime})"
                
                # Show first few lines of the file
                echo "  Sample content:"
                head -2 "$file" 2>/dev/null | sed 's/^/    /' || echo "    (unable to read file)"
                echo
            else
                echo "$basename"
            fi
        fi
    done < <(find "${DLQ_BASE_DIR}" -name "$find_pattern" -print0 2>/dev/null || true)
    
    echo -e "\nTotal files: ${GREEN}${count}${NC}"
}

# Function to cleanup old DLQ files
cleanup_dlq() {
    local retention_days=$DEFAULT_RETENTION_DAYS
    local dry_run=false
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --retention)
                retention_days="$2"
                shift 2
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    log "INFO" "Cleaning up DLQ files older than ${retention_days} days (dry-run: ${dry_run})"
    
    if [[ ! -d "${DLQ_BASE_DIR}" ]]; then
        echo "No DLQ directory found"
        return 0
    fi
    
    echo -e "${BLUE}=== DLQ Cleanup ===${NC}"
    echo "Retention policy: ${retention_days} days"
    echo "Dry run: ${dry_run}"
    echo
    
    local deleted_count=0
    local deleted_size=0
    
    # Find files older than retention period
    while IFS= read -r -d '' file; do
        if [[ -f "$file" ]]; then
            local age_days=$(( ($(date +%s) - $(stat -f%m "$file" 2>/dev/null || stat -c%Y "$file" 2>/dev/null || echo 0)) / 86400 ))
            
            if [[ $age_days -gt $retention_days ]]; then
                local size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
                local human_size=$(numfmt --to=iec-i --suffix=B "$size" 2>/dev/null || echo "${size}B")
                
                echo -e "Deleting: ${RED}$(basename "$file")${NC} (${age_days} days old, ${human_size})"
                
                if [[ "$dry_run" == false ]]; then
                    rm -f "$file"
                    log "INFO" "Deleted DLQ file: $file"
                fi
                
                ((deleted_count++))
                ((deleted_size += size))
            fi
        fi
    done < <(find "${DLQ_BASE_DIR}" -name "*.json" -print0 2>/dev/null || true)
    
    local human_deleted_size=$(numfmt --to=iec-i --suffix=B "$deleted_size" 2>/dev/null || echo "${deleted_size}B")
    
    echo
    echo -e "Files ${dry_run:+would be }deleted: ${GREEN}${deleted_count}${NC}"
    echo -e "Space ${dry_run:+would be }freed: ${GREEN}${human_deleted_size}${NC}"
}

# Function to reprocess DLQ files
reprocess_dlq() {
    local category_filter=""
    local dry_run=false
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --category)
                category_filter="$2"
                shift 2
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    log "INFO" "Reprocessing DLQ files (category: ${category_filter:-all}, dry-run: ${dry_run})"
    
    echo -e "${BLUE}=== DLQ Reprocessing ===${NC}"
    echo "Category filter: ${category_filter:-all}"
    echo "Dry run: ${dry_run}"
    echo
    
    if [[ ! -d "${DLQ_BASE_DIR}" ]]; then
        echo "No DLQ directory found"
        return 0
    fi
    
    local find_pattern="*.json"
    if [[ -n "$category_filter" ]]; then
        find_pattern="*${category_filter}*.json"
    fi
    
    local processed_count=0
    
    while IFS= read -r -d '' file; do
        if [[ -f "$file" ]]; then
            echo -e "Processing: ${GREEN}$(basename "$file")${NC}"
            
            if [[ "$dry_run" == false ]]; then
                # Validate JSON format
                if jq empty "$file" 2>/dev/null; then
                    # Move to reprocessing directory
                    local reprocess_dir="${DLQ_BASE_DIR}/reprocessing"
                    mkdir -p "$reprocess_dir"
                    mv "$file" "$reprocess_dir/"
                    log "INFO" "Moved DLQ file for reprocessing: $file"
                else
                    echo -e "  ${RED}ERROR: Invalid JSON format${NC}"
                    log "ERROR" "Invalid JSON format in DLQ file: $file"
                fi
            fi
            
            ((processed_count++))
        fi
    done < <(find "${DLQ_BASE_DIR}" -name "$find_pattern" -not -path "*/reprocessing/*" -not -path "*/archive/*" -print0 2>/dev/null || true)
    
    echo
    echo -e "Files ${dry_run:+would be }processed: ${GREEN}${processed_count}${NC}"
}

# Function to monitor DLQ
monitor_dlq() {
    local verbose=false
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --verbose)
                verbose=true
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    log "INFO" "Monitoring DLQ status"
    
    echo -e "${BLUE}=== DLQ Monitoring ===${NC}"
    
    while true; do
        clear
        echo -e "${BLUE}DLQ Monitor - $(date)${NC}"
        echo "Press Ctrl+C to exit"
        echo
        
        show_status
        
        if [[ "$verbose" == true ]]; then
            echo
            echo -e "${BLUE}=== Recent Activity ===${NC}"
            tail -5 "${LOG_FILE}" 2>/dev/null || echo "No recent activity"
        fi
        
        sleep 30
    done
}

# Function to validate DLQ files
validate_dlq() {
    log "INFO" "Validating DLQ files"
    
    echo -e "${BLUE}=== DLQ Validation ===${NC}"
    
    if [[ ! -d "${DLQ_BASE_DIR}" ]]; then
        echo "No DLQ directory found"
        return 0
    fi
    
    local valid_count=0
    local invalid_count=0
    
    while IFS= read -r -d '' file; do
        if [[ -f "$file" ]]; then
            echo -n "Validating $(basename "$file")... "
            
            if jq empty "$file" 2>/dev/null; then
                echo -e "${GREEN}VALID${NC}"
                ((valid_count++))
            else
                echo -e "${RED}INVALID${NC}"
                ((invalid_count++))
                log "ERROR" "Invalid JSON in DLQ file: $file"
            fi
        fi
    done < <(find "${DLQ_BASE_DIR}" -name "*.json" -print0 2>/dev/null || true)
    
    echo
    echo -e "Valid files: ${GREEN}${valid_count}${NC}"
    echo -e "Invalid files: ${RED}${invalid_count}${NC}"
}

# Function to export DLQ data
export_dlq() {
    local category_filter=""
    local date_filter=""
    local output_file="dlq-export-$(date +%Y%m%d-%H%M%S).json"
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --category)
                category_filter="$2"
                shift 2
                ;;
            --date)
                date_filter="$2"
                shift 2
                ;;
            --output)
                output_file="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    
    log "INFO" "Exporting DLQ data to ${output_file}"
    
    echo -e "${BLUE}=== DLQ Export ===${NC}"
    echo "Output file: ${output_file}"
    echo "Category filter: ${category_filter:-all}"
    echo "Date filter: ${date_filter:-all}"
    echo
    
    if [[ ! -d "${DLQ_BASE_DIR}" ]]; then
        echo "No DLQ directory found"
        return 0
    fi
    
    local find_pattern="*.json"
    if [[ -n "$category_filter" ]]; then
        find_pattern="*${category_filter}*.json"
    fi
    
    echo "[" > "$output_file"
    local first=true
    local exported_count=0
    
    while IFS= read -r -d '' file; do
        if [[ -f "$file" ]]; then
            local basename=$(basename "$file")
            
            # Apply date filter if specified
            if [[ -n "$date_filter" && "$basename" != *"$date_filter"* ]]; then
                continue
            fi
            
            if [[ "$first" == true ]]; then
                first=false
            else
                echo "," >> "$output_file"
            fi
            
            echo -n "  {\"file\": \"$basename\", \"content\": " >> "$output_file"
            cat "$file" >> "$output_file"
            echo -n "}" >> "$output_file"
            
            ((exported_count++))
        fi
    done < <(find "${DLQ_BASE_DIR}" -name "$find_pattern" -print0 2>/dev/null || true)
    
    echo >> "$output_file"
    echo "]" >> "$output_file"
    
    echo -e "Exported ${GREEN}${exported_count}${NC} DLQ entries to ${GREEN}${output_file}${NC}"
}

# Main function
main() {
    # Create log directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Create DLQ directories if they don't exist
    mkdir -p "${DLQ_BASE_DIR}" "${ARCHIVE_DIR}"
    
    case "${1:-help}" in
        status)
            shift
            show_status "$@"
            ;;
        list)
            shift
            list_dlq_files "$@"
            ;;
        cleanup)
            shift
            cleanup_dlq "$@"
            ;;
        reprocess)
            shift
            reprocess_dlq "$@"
            ;;
        monitor)
            shift
            monitor_dlq "$@"
            ;;
        validate)
            shift
            validate_dlq "$@"
            ;;
        export)
            shift
            export_dlq "$@"
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            echo -e "${RED}Unknown command: $1${NC}"
            echo
            usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"