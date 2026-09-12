#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8088}"
DEMO_TIMEOUT_SECONDS="${DEMO_TIMEOUT_SECONDS:-1800}"
DEMO_POLL_SECONDS="${DEMO_POLL_SECONDS:-10}"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "error: python3 or python is required for JSON parsing" >&2
  exit 1
fi

mkdir -p artifacts

json_value() {
  "$PYTHON_BIN" -c 'import json, sys; print(json.load(sys.stdin).get(sys.argv[1], ""))' "$1"
}

submit_job() {
  local prompt="$1"
  local payload
  payload="$("$PYTHON_BIN" -c 'import json, sys; print(json.dumps({"query": sys.argv[1]}))' "$prompt")"

  curl -fsS \
    -H "Content-Type: application/json" \
    -d "$payload" \
    "$API_URL/jobs"
}

poll_job() {
  local job_id="$1"
  local label="$2"
  local deadline=$((SECONDS + DEMO_TIMEOUT_SECONDS))
  local response status error

  while (( SECONDS < deadline )); do
    response="$(curl -fsS "$API_URL/jobs/$job_id")"
    status="$(printf '%s' "$response" | json_value status)"

    printf '[%s] %s\n' "$label" "$status"

    case "$status" in
      completed)
        return 0
        ;;
      failed)
        error="$(printf '%s' "$response" | json_value error)"
        echo "error: job $job_id failed: $error" >&2
        return 1
        ;;
    esac

    sleep "$DEMO_POLL_SECONDS"
  done

  echo "error: job $job_id timed out after ${DEMO_TIMEOUT_SECONDS}s" >&2
  return 1
}

echo "Checking API at $API_URL/health"
if ! curl -fsS "$API_URL/health" >/dev/null; then
  echo "error: API is not reachable at $API_URL" >&2
  exit 1
fi

prompts=(
  "How does the pH scale work?"
  "Why do atoms form covalent bonds?"
  "What is the difference between ionic and covalent bonding?"
)

labels=(
  "pH scale"
  "covalent bonds"
  "ionic vs covalent"
)

outputs=(
  "artifacts/demo_ph_scale.mp4"
  "artifacts/demo_covalent_bonds.mp4"
  "artifacts/demo_ionic_vs_covalent.mp4"
)

job_ids=()

for i in "${!prompts[@]}"; do
  echo "Submitting: ${prompts[$i]}"
  response="$(submit_job "${prompts[$i]}")"
  job_id="$(printf '%s' "$response" | json_value id)"
  if [[ -z "$job_id" ]]; then
    echo "error: POST /jobs did not return an id" >&2
    exit 1
  fi
  job_ids+=("$job_id")
  echo "[${labels[$i]}] job_id=$job_id"
done

for i in "${!job_ids[@]}"; do
  poll_job "${job_ids[$i]}" "${labels[$i]}"
  echo "Downloading ${outputs[$i]}"
  curl -fL "$API_URL/jobs/${job_ids[$i]}/artifact" -o "${outputs[$i]}"
  if [[ ! -s "${outputs[$i]}" ]]; then
    echo "error: downloaded artifact is empty: ${outputs[$i]}" >&2
    exit 1
  fi
done

echo "Demo complete:"
printf '  %s\n' "${outputs[@]}"
