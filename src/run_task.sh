#!/bin/bash

FOLDER=$1
SCRIPT_NAME=$2
shift 2

ROOT_DIR=$(pwd)
LOG_DIR="$ROOT_DIR/logs/$SCRIPT_NAME"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/$(date +'%Y%m%d_%H%M%S').log"

{
    echo "================================================"
    echo "START [$FOLDER/$SCRIPT_NAME.py]: $(date +"%Y-%m-%d %H:%M:%S")"
    echo "================================================"
    
    START_SECONDS=$SECONDS

    python -m "$FOLDER.$SCRIPT_NAME" "$@" 2>&1

    ELAPSED=$(( SECONDS - START_SECONDS ))
    days=$(( ELAPSED / 86400 ))
    hours=$(( (ELAPSED % 86400) / 3600 ))
    mins=$(( (ELAPSED % 3600) / 60 ))
    secs=$(( ELAPSED % 60 ))

    echo ""
    echo "================================================"
    echo "END [$FOLDER/$SCRIPT_NAME.py]: $(date +"%Y-%m-%d %H:%M:%S")"
    echo "ELAPSED TIME: ${days}d ${hours}h ${mins}m ${secs}s"
    echo "================================================"

} 2>&1 | tee "$LOG_FILE"