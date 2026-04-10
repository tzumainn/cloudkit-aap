#!/bin/bash
set -e

# Set KUBECONFIG to dedicated file for kind cluster
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export KUBECONFIG="${SCRIPT_DIR}/kubeconfig-osac-test"
export K8S_AUTH_KUBECONFIG="${KUBECONFIG}"
echo "Using kubeconfig: ${KUBECONFIG}"

# Set Pod environment variables for lease creation (normally set by Kubernetes)
export POD_NAMESPACE="osac-system"
export POD_NAME="test-runner"
# Use real pod UID if available (created by setup_test_env.sh), fall back to placeholder
if [ -f "${SCRIPT_DIR}/test-runner-uid" ]; then
  export POD_UID=$(cat "${SCRIPT_DIR}/test-runner-uid")
else
  export POD_UID="00000000-0000-0000-0000-000000000000"
fi

# Suppress inventory parsing warnings
export ANSIBLE_INVENTORY_UNPARSED_WARNING=False
export ANSIBLE_LOCALHOST_WARNING=False

FAILED=()
PASSED=()

# Test workflows
WORKFLOWS=(
  "cluster_create"
  "cluster_delete"
  "cluster_post_install"
  "compute_instance_create"
  "compute_instance_with_gpu_create"
  "compute_instance_delete"
  "cluster_status_reporting"
)

# Role-level integration tests (baseline only, no overrides)
ROLE_TESTS=(
  "finalizer"
  "lease"
  "cluster_working_namespace"
  "compute_instance_working_namespace"
)

echo "=== Running Workflow Integration Tests ==="
echo ""

for workflow in "${WORKFLOWS[@]}"; do
  echo "----------------------------------------"
  echo "Testing: $workflow"
  echo "----------------------------------------"

  # Baseline test
  echo "  [1/2] Running baseline test..."
  if ansible-playbook "targets/${workflow}/tasks/baseline.yml" -e "@common_vars.yml" -v; then
    echo "  ✓ Baseline passed"
    PASSED+=("$workflow:baseline")
  else
    echo "  ✗ Baseline failed"
    FAILED+=("$workflow:baseline")
  fi

  # Override test (skip if no overrides playbook exists)
  if [ -f "targets/${workflow}/tasks/overrides.yml" ]; then
    echo "  [2/2] Running override test..."
    # Clear override log
    > /tmp/osac_test_overrides.log

    if ansible-playbook "targets/${workflow}/tasks/overrides.yml" -e "@common_vars.yml" -v; then
      # Verify override log has entries
      if [ -s /tmp/osac_test_overrides.log ]; then
        echo "  ✓ Override test passed"
        PASSED+=("$workflow:overrides")
      else
        echo "  ✗ Override test failed (no override log entries)"
        FAILED+=("$workflow:overrides-no-log")
      fi
    else
      echo "  ✗ Override test failed"
      FAILED+=("$workflow:overrides")
    fi
  else
    echo "  [2/2] No override test (skipped)"
  fi

  echo ""
done

echo "=== Running Role Integration Tests ==="
echo ""

for role in "${ROLE_TESTS[@]}"; do
  echo "----------------------------------------"
  echo "Testing role: $role"
  echo "----------------------------------------"

  if ansible-playbook "targets/${role}/tasks/baseline.yml" -e "@common_vars.yml" -v; then
    echo "  ✓ Passed"
    PASSED+=("$role:baseline")
  else
    echo "  ✗ Failed"
    FAILED+=("$role:baseline")
  fi

  echo ""
done

echo "========================================"
echo "Test Results"
echo "========================================"
echo "Passed: ${#PASSED[@]}"
echo "Failed: ${#FAILED[@]}"

if [ ${#FAILED[@]} -eq 0 ]; then
  echo ""
  echo "✓ All tests passed!"
  exit 0
else
  echo ""
  echo "✗ Failed tests:"
  for test in "${FAILED[@]}"; do
    echo "  - $test"
  done
  exit 1
fi
