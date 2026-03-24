#!/bin/bash

# Pokemon Card Bargain Finder - Git-based Deploy Script

APP_DIR="/data/.openclaw/workspace/pokemon-bargain-finder"
APP_PORT=5000
LOG_FILE="$APP_DIR/deploy.log"

echo "[$(date)] Starting deployment..." >> $LOG_FILE

# Step 1: Pull latest code (or skip if not a git repo)
cd $APP_DIR

if [ -d .git ]; then
    echo "[$(date)] Pulling latest code..." >> $LOG_FILE
    git pull origin master >> $LOG_FILE 2>&1
    if [ $? -ne 0 ]; then
        echo "[$(date)] ERROR: Git pull failed" >> $LOG_FILE
        exit 1
    fi
else
    echo "[$(date)] WARNING: Not a git repo - skipping git pull. Initialize with: git init && git remote add origin <repo_url>" >> $LOG_FILE
fi

# Step 2: Kill existing app process
echo "[$(date)] Stopping app..." >> $LOG_FILE
pkill -f "python3 app.py" 2>/dev/null

# Give it a moment to shut down
sleep 2

# Step 3: Restart app
echo "[$(date)] Starting app..." >> $LOG_FILE
cd $APP_DIR
nohup python3 app.py > app.log 2>&1 &
APP_PID=$!
echo $APP_PID >> $LOG_FILE

# Step 4: Wait and verify
sleep 3
if ps -p $APP_PID > /dev/null; then
    echo "[$(date)] ✅ Deployment SUCCESS - App running (PID: $APP_PID)" >> $LOG_FILE
    echo "OK"
else
    echo "[$(date)] ❌ Deployment FAILED - App did not start" >> $LOG_FILE
    cat $APP_DIR/app.log >> $LOG_FILE
    exit 1
fi
