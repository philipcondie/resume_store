#!/bin/bash
set -euo pipefail

# --- config ---                                                                                         
SERVER="philip@resume_store"
REMOTE_PATH="/home/philip/resume_store"                                                                             
HEALTH_URL="https://resume-api.philcondie.com/health"                                                    
HEALTH_TIMEOUT=60                                                                                        
COMPOSE_FILE="docker-compose.prod.yml"                                                                   
                                                                                                        
SCRIPT_START=$(date +%s)

log() {                                                                                                  
    local elapsed=$(($(date +%s) - SCRIPT_START))
    echo "[deploy +${elapsed}s] $*"                                                                      
}

# wait_for_health URL TIMEOUT_SECONDS
# returns 0 on success, 1 on timeout
wait_for_health() {
    local url="$1"
    local timeout="$2"
    local start=$(date +%s)
    local deadline=$((start + timeout))
    local attempt=1
    local http_code

    while [[ $(date +%s) -lt $deadline ]]; do
        http_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" || echo "000")
        if [[ "$http_code" == "200" ]]; then
            return 0
        fi
        log " attempt $attempt: got $http_code"
        sleep 2
        ((attempt++))
    done
    return 1
}

if [[ -n "$(git status --porcelain)" ]]; then                                                            
    log "ERROR: uncommitted changes in local repo. Commit or stash first."
    exit 1                                                                                               
fi

# log "pushing to origin"                
# git push

log "recording current remote SHA for potential rollback"                                                
PREVIOUS_SHA=$(ssh "$SERVER" "cd $REMOTE_PATH && git rev-parse HEAD")
log "current remote HEAD: $PREVIOUS_SHA"

log "pulling + rebuilding on $SERVER"
# The migrate service runs to completion before app starts. If it exits
# non-zero, compose aborts here and the app is never started.
if ! ssh "$SERVER" "cd $REMOTE_PATH && git pull && docker compose -f $COMPOSE_FILE up -d --build"; then
    log "FAILURE: build/startup failed. Migration logs:"
    ssh "$SERVER" "cd $REMOTE_PATH && docker compose -f $COMPOSE_FILE logs --no-color --tail 50 migrate" || true
    log "NOT auto-rolling back: migrations may have partially applied, and"
    log "reverting code against a changed schema can be worse than stopping."
    log "Previous SHA for manual rollback: $PREVIOUS_SHA"
    exit 3
fi

log "waiting up to ${HEALTH_TIMEOUT}s for $HEALTH_URL"
if wait_for_health "$HEALTH_URL" "$HEALTH_TIMEOUT"; then                                                 
    log "SUCCESS: health check passed"                                                                   
    exit 0                                                                                               
fi

# Migrations succeeded (compose would have aborted above otherwise), so this is
# an app-level failure and rolling the code back is safe.
log "FAILURE: health check timed out. App logs:"
ssh "$SERVER" "cd $REMOTE_PATH && docker compose -f $COMPOSE_FILE logs --no-color --tail 50 app" || true

log "rolling back to $PREVIOUS_SHA"
ssh "$SERVER" "cd $REMOTE_PATH && git reset --hard $PREVIOUS_SHA && docker compose -f $COMPOSE_FILE up -d --build"                                                                                                
                                        
log "verifying rollback"                                                                                 
if wait_for_health "$HEALTH_URL" "$HEALTH_TIMEOUT"; then
    log "rollback successful"
    exit 1   # still non-zero — the deploy failed, even though rollback worked                           
else                                                                                                     
    log "CRITICAL: rollback also failed. Server may need manual intervention."                           
    exit 2                                                                                               
fi