# CLAUDE.md

## Project Overview

The osac-aap repository contains Ansible automation for provisioning OSAC (Open Sovereign AI Cloud) infrastructure resources. It integrates with Ansible Automation Platform (AAP) and provides playbooks, collections, template roles, and Config-as-Code. This repository was created by merging osac-templates into osac-aap.

## Critical Rules

- **Use FQCN** for all modules: `ansible.builtin.debug`, not `debug`
- **Add `name:` to every task** — ansible-lint enforces this
- **Use underscores** in role names and `implementation_strategy`, never hyphens
- **Always include `osac.service.common`** to get `remote_cluster_kubeconfig` before creating K8s resources on remote clusters
- **Run `ansible-lint`** before committing

## Repository Structure

```text
osac-aap/
├── playbook_osac_*.yml                    # Top-level playbooks (AAP job templates)
├── collections/ansible_collections/
│   ├── osac.service/                      # Core service roles (common utilities)
│   ├── osac.templates/                    # Infrastructure templates
│   ├── osac.workflows/                    # Multi-step workflows
│   └── osac.config_as_code/              # AAP configuration
├── vendor/                                # Vendored Ansible collections
├── tests/                                 # Integration test suites
├── samples/                               # Example configurations
└── pyproject.toml                         # Python dependencies (uv)
```

### Collections

| Collection | Purpose | Key Roles |
|------------|---------|-----------|
| **osac.service** | Core utilities | `common`, `finalizer`, `lease`, `wait_for`, `publish_templates`, `tenant_storage_class` |
| **osac.templates** | Infrastructure provisioning | `cudn_net` (networking), `metallb_l2` (PublicIPPool), `ocp_virt_vm` (VMs), `ocp_4_17_small` (clusters) |
| **osac.workflows** | Multi-step playbooks | Cluster create/delete, compute instance lifecycle |
| **osac.config_as_code** | AAP configuration | Job templates, inventories, credentials |

## Quick Reference Commands

```bash
# Setup
uv sync --all-groups && source .venv/bin/activate

# Lint
ansible-lint

# Test playbook syntax
ansible-playbook --syntax-check playbook_osac_create_subnet.yml

# Test playbook locally
ansible-playbook playbook_osac_create_subnet.yml -e @samples/subnet_payload.json

# Re-vendor collections (after updating collections/requirements.yml)
rm -rf vendor && ansible-galaxy collection install -r collections/requirements.yml
```

## Detailed Rules (auto-loaded from `.claude/rules/`)

- **`playbook-patterns.md`** — Playbook naming, template roles, service roles, standard patterns, variable flow
- **`networking-cudn.md`** — CUDN networking implementation details (VirtualNetwork, Subnet, SecurityGroup)

## Creating a New Template Role

1. Create role at `collections/ansible_collections/osac/templates/roles/<name>/`
2. Add `meta/osac.yaml` with `implementation_strategy`, `template_type`, `capabilities`
3. Create task files: `tasks/create_<resource>.yaml`, `tasks/delete_<resource>.yaml`
4. Run `playbook_osac_config_as_code.yml` to register and publish NetworkClass

## Common Pitfalls

1. **venv not activated** — `ansible-playbook: command not found` → `source .venv/bin/activate` or `uv run`
2. **Stale vendored collections** — re-vendor after updating `collections/requirements.yml`
3. **Implementation strategy mismatch** — role dir name, `meta/osac.yaml`, and CR annotation must all match (use underscores)
4. **Missing remote kubeconfig** — always include `osac.service.common` with `tasks_from: get_remote_cluster_kubeconfig`
5. **Namespace label syntax** — `k8s.ovn.org/primary-user-defined-network: ""` (empty string, not missing value)

## Cross-Repo Coordination

**Adding a new field to a resource (e.g., `mtu` to Subnet):**
1. fulfillment-service: Add field to proto, regenerate
2. osac-operator: Add field to CRD spec, update controller
3. osac-aap: Extract field in playbook, pass to role
4. osac-aap: Role reads field and provisions infrastructure

**Adding a new networking implementation:**
1. osac-aap: Create template role with `meta/osac.yaml`
2. osac-aap: Run config-as-code to publish NetworkClass
3. fulfillment-service: NetworkClass auto-discovered in API
4. Users: Create VirtualNetwork with new `networkClass`

## Development Workflow

```bash
# Before committing
ansible-lint
ansible-playbook --syntax-check playbook_osac_create_subnet.yml

# Commit format
git commit -s -m "MGMT-XXXXX: description of change"
```

### PR Checklist

- [ ] `ansible-lint` passes
- [ ] `meta/osac.yaml` updated for template role changes
- [ ] Cross-repo dependencies documented in PR description
- [ ] Playbook tested locally or against AAP

## Links

- [Ansible Documentation](https://docs.ansible.com/)
- [kubernetes.core collection](https://docs.ansible.com/ansible/latest/collections/kubernetes/core/)
- [osac-operator](https://github.com/osac-project/osac-operator) — Kubernetes operator integration
- [fulfillment-service](https://github.com/osac-project/fulfillment-service) — Backend API
