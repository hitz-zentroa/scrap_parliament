#!/bin/bash

#####################################################   CONFIGURATION   ######################################################

FOLDER="src"
SCRIPT_NAME="scrap_metadata"

# Paths
DB_PATH="db/database.db"
OUTPUT_DIR="data"

# Inputs
PLENO_URL="https://www.legebiltzarra.eus/portal/es/transparencia/open-data?opcion=pleno"
BASE_COMISIONES_URL="https://www.legebiltzarra.eus/portal/es/transparencia/open-data?opcion=comisiones&numLegislatura="

# Flags
ONLY_STATS="false"   # true, false
SAVE_XML="false"     # true, false

#############################################################################################################################

# Arguments array
args=(
  --db_path "$DB_PATH"
  --output_dir "$OUTPUT_DIR"
  --pleno_url "$PLENO_URL"
  --base_comisiones_url "$BASE_COMISIONES_URL"
)
[[ "$ONLY_STATS" == "true" ]] && args+=(--only_stats)
[[ "$SAVE_XML" == "true" ]] && args+=(--save_xml)

# Call universal runner
bash src/run_task.sh "$FOLDER" "$SCRIPT_NAME" "${args[@]}"

