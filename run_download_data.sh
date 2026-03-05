#!/bin/bash

#####################################################   CONFIGURATION   ######################################################

FOLDER="src"
SCRIPT_NAME="download_data"

# Paths
DB_PATH="db/database.db"
OUTPUT_DIR="data"

# Inputs
LEGISLATURA_NUM=$1

# Flags
DOWNLOAD_PLENO="true"    # true, false
DOWNLOAD_COMISION="true" # true, false

##############################################################################################################################

# Arguments array
args=(
  --db_path "$DB_PATH"
  --output_dir "$OUTPUT_DIR"
  --legislatura_num "$LEGISLATURA_NUM"
)
[[ "$DOWNLOAD_PLENO" == "true" ]] && args+=(--download_pleno)
[[ "$DOWNLOAD_COMISION" == "true" ]] && args+=(--download_comision)

# Call universal runner
bash src/run_task.sh "$FOLDER" "$SCRIPT_NAME" "${args[@]}"
