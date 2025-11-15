#!/bin/bash

# Load environment variables from .env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at $ENV_FILE"
    echo "Please copy .env.example to .env and configure your settings:"
    echo "  cp .env.example .env"
    exit 1
fi

echo "Loading environment variables from .env file..."
set -a  # automatically export all variables
source "$ENV_FILE"
set +a  # stop automatically exporting

# Check if using OpenRouter API
if [ -n "$OPENROUTER_API_KEY" ]; then
    echo "Using OpenRouter API mode - skipping local server startup"
    USE_OPENROUTER=true
else
    echo "Using local model mode"
    USE_OPENROUTER=false

    # Validate critical variables for local mode
    if [ "$MODEL_PATH" = "/your/model/path" ] || [ -z "$MODEL_PATH" ]; then
        echo "Error: MODEL_PATH not configured in .env file"
        exit 1
    fi
fi

######################################
### 1. start server (if not using OpenRouter) ###
######################################

if [ "$USE_OPENROUTER" = "false" ]; then
    echo "Starting VLLM servers..."
    CUDA_VISIBLE_DEVICES=0 vllm serve $MODEL_PATH --host 0.0.0.0 --port 6001 --disable-log-requests &
    CUDA_VISIBLE_DEVICES=1 vllm serve $MODEL_PATH --host 0.0.0.0 --port 6002 --disable-log-requests &
    CUDA_VISIBLE_DEVICES=2 vllm serve $MODEL_PATH --host 0.0.0.0 --port 6003 --disable-log-requests &
    CUDA_VISIBLE_DEVICES=3 vllm serve $MODEL_PATH --host 0.0.0.0 --port 6004 --disable-log-requests &
    CUDA_VISIBLE_DEVICES=4 vllm serve $MODEL_PATH --host 0.0.0.0 --port 6005 --disable-log-requests &
    CUDA_VISIBLE_DEVICES=5 vllm serve $MODEL_PATH --host 0.0.0.0 --port 6006 --disable-log-requests &
    CUDA_VISIBLE_DEVICES=6 vllm serve $MODEL_PATH --host 0.0.0.0 --port 6007 --disable-log-requests &
    CUDA_VISIBLE_DEVICES=7 vllm serve $MODEL_PATH --host 0.0.0.0 --port 6008 --disable-log-requests &
fi

#######################################################
### 2. Waiting for the server port to be ready (if not using OpenRouter) ###
######################################################

if [ "$USE_OPENROUTER" = "false" ]; then
    timeout=6000
    start_time=$(date +%s)

    main_ports=(6001 6002 6003 6004 6005 6006 6007 6008)
    echo "Mode: All ports used as main model"

    declare -A server_status
    for port in "${main_ports[@]}"; do
        server_status[$port]=false
    done

    echo "Waiting for servers to start..."

    while true; do
        all_ready=true

        for port in "${main_ports[@]}"; do
            if [ "${server_status[$port]}" = "false" ]; then
                if curl -s -f http://localhost:$port/v1/models > /dev/null 2>&1; then
                    echo "Main model server (port $port) is ready!"
                    server_status[$port]=true
                else
                    all_ready=false
                fi
            fi
        done

        if [ "$all_ready" = "true" ]; then
            echo "All servers are ready for inference!"
            break
        fi

        current_time=$(date +%s)
        elapsed=$((current_time - start_time))
        if [ $elapsed -gt $timeout ]; then
            echo -e "\nError: Server startup timeout after ${timeout} seconds"

            for port in "${main_ports[@]}"; do
                if [ "${server_status[$port]}" = "false" ]; then
                    echo "Main model server (port $port) failed to start"
                fi
            done


            exit 1
        fi

        printf 'Waiting for servers to start .....'
        sleep 10
    done

    failed_servers=()
    for port in "${main_ports[@]}"; do
        if [ "${server_status[$port]}" = "false" ]; then
            failed_servers+=($port)
        fi
    done

    if [ ${#failed_servers[@]} -gt 0 ]; then
        echo "Error: The following servers failed to start: ${failed_servers[*]}"
        exit 1
    else
        echo "All required servers are running successfully!"
    fi
else
    echo "Using OpenRouter API - no local servers needed"
fi

#####################################
### 3. start infer               ####
#####################################

echo "==== start infer... ===="

cd "$( dirname -- "${BASH_SOURCE[0]}" )"

if [ "$USE_OPENROUTER" = "true" ]; then
    echo "Running with OpenRouter API"
    python -u run_multi_react.py --dataset "$DATASET" --output "$OUTPUT_PATH" --max_workers $MAX_WORKERS --model "openrouter" --temperature $TEMPERATURE --presence_penalty $PRESENCE_PENALTY --total_splits ${WORLD_SIZE:-1} --worker_split $((${RANK:-0} + 1)) --roll_out_count $ROLLOUT_COUNT
else
    echo "Running with local model"
    python -u run_multi_react.py --dataset "$DATASET" --output "$OUTPUT_PATH" --max_workers $MAX_WORKERS --model $MODEL_PATH --temperature $TEMPERATURE --presence_penalty $PRESENCE_PENALTY --total_splits ${WORLD_SIZE:-1} --worker_split $((${RANK:-0} + 1)) --roll_out_count $ROLLOUT_COUNT
fi
