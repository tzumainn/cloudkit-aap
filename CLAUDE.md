# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The osac-aap repository contains Ansible automation for provisioning OSAC infrastructure resources. It integrates with Ansible Automation Platform (AAP) and provides:

- **Playbooks** - Top-level workflows triggered by osac-operator via AAP job templates
- **Ansible Collections** - Reusable roles and modules organized by domain
- **Templates** - Infrastructure implementation roles (networking, compute, clusters)
- **Config-as-Code** - AAP configuration management for OSAC deployment

This repository was created by merging osac-templates into osac-aap, consolidating all Ansible automation in one place.

## Repository Structure

```
osac-aap/
├── playbook_osac_*.yml                    # Top-level playbooks (AAP job templates)
├── collections/ansible_collections/       # Ansible collections
│   ├── osac.service/                      # Core service roles (common utilities)
│   ├── osac.templates/                    # Infrastructure templates
│   ├── osac.workflows/                    # Multi-step workflows
│   └── osac.config_as_code/              # AAP configuration
├── vendor/                                # Vendored Ansible collections
├── tests/integration/                     # Integration test suites
├── samples/                               # Example configurations
├── inventory/                             # Ansible inventory files
├── group_vars/                            # Group variables
└── pyproject.toml                         # Python dependencies (uv)
```

### Collection Organization

| Collection | Purpose | Key Roles |
|------------|---------|-----------|
| **osac.service** | Core utilities and common tasks | `common`, `finalizer`, `lease`, `wait_for`, `tenant_storage_class` |
| **osac.templates** | Infrastructure provisioning templates | `cudn_net` (networking), `ocp_virt_vm` (VMs), `ocp_4_17_small` (clusters) |
| **osac.workflows** | Multi-step playbooks | Cluster create/delete, compute instance lifecycle |
| **osac.config_as_code** | AAP configuration | Job templates, inventories, credentials |

## Development Setup

### Prerequisites

- Python 3.13+
- `uv` (Python package manager)
- Access to an OpenShift cluster
- AAP instance (for integration testing)

### Installation

```bash
# Install all dependencies (Ansible, ansible-lint, etc.)
uv sync --all-groups

# Activate virtual environment
source .venv/bin/activate

# Verify installation
ansible --version
ansible-lint --version
```

### Re-vendoring Collections

After updating `collections/requirements.yml`, re-vendor dependencies:

```bash
# Set up Red Hat Automation Hub authentication
export ANSIBLE_GALAXY_SERVER_LIST=automation_hub,default
export ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_URL=https://console.redhat.com/api/automation-hub/content/published/
export ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_AUTH_URL=https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token
export ANSIBLE_GALAXY_SERVER_DEFAULT_URL=https://galaxy.ansible.com/
export ANSIBLE_GALAXY_SERVER_AUTOMATION_HUB_TOKEN=<your-token>

# Re-vendor collections
rm -rf vendor
ansible-galaxy collection install -r collections/requirements.yml
```

## Playbook Architecture

### Naming Convention

Top-level playbooks follow the pattern: `playbook_osac_{action}_{resource}.yml`

**Examples:**
- `playbook_osac_create_subnet.yml`
- `playbook_osac_delete_virtual_network.yml`
- `playbook_osac_create_security_group.yml`
- `playbook_osac_create_hosted_cluster.yml`
- `playbook_osac_delete_compute_instance.yml`

### Playbook-to-Template Mapping

AAP job templates are named: `osac-{action}-{resource}`

| Playbook | AAP Job Template | Triggered By |
|----------|------------------|--------------|
| `playbook_osac_create_subnet.yml` | `osac-create-subnet` | osac-operator SubnetReconciler |
| `playbook_osac_delete_virtual_network.yml` | `osac-delete-virtual-network` | osac-operator VirtualNetworkReconciler |
| `playbook_osac_create_security_group.yml` | `osac-create-security-group` | osac-operator SecurityGroupReconciler |

**Configuration:** osac-operator env var `OSAC_AAP_TEMPLATE_PREFIX` (default: `osac`)

### Playbook Structure

All playbooks follow a standard pattern:

```yaml
---
- name: Create a Subnet resource
  hosts: localhost
  gather_facts: false

  vars:
    # Extract payload from EDA/AAP event
    subnet: "{{ ansible_eda.event.payload }}"
    subnet_name: "{{ ansible_eda.event.payload.metadata.name }}"
    # Implementation strategy annotation set by osac-operator
    implementation_strategy: >-
      {{ ansible_eda.event.payload.metadata.annotations
         ['osac.openshift.io/implementation-strategy'] }}

  pre_tasks:
    - name: Show EDA Event
      ansible.builtin.debug:
        var: ansible_eda.event.payload

  tasks:
    - name: Call the selected implementation role
      ansible.builtin.include_role:
        name: "osac.templates.{{ implementation_strategy }}"
        tasks_from: create_subnet
```

**Key pattern:**
1. Playbook receives K8s CR as `ansible_eda.event.payload`
2. Extracts `implementation-strategy` annotation from CR metadata
3. Dynamically includes the appropriate role from `osac.templates`
4. Role performs actual provisioning (creates K8s resources, updates CR)

## Template Roles

Template roles live in `collections/ansible_collections/osac/templates/roles/` and implement infrastructure provisioning strategies.

### Template Role Structure

```
osac.templates.cudn_net/
├── meta/
│   └── osac.yaml                    # Template metadata (NetworkClass registration)
├── tasks/
│   ├── create_virtual_network.yaml  # VirtualNetwork provisioning
│   ├── create_subnet.yaml           # Subnet provisioning (Namespace + CUDN)
│   ├── create_security_group.yaml   # SecurityGroup provisioning (NetworkPolicy)
│   ├── delete_virtual_network.yaml
│   ├── delete_subnet.yaml
│   └── delete_security_group.yaml
├── defaults/
│   └── main.yml                     # Default variables
└── README.md                        # Usage documentation
```

### Template Metadata (meta/osac.yaml)

Every template role must have `meta/osac.yaml` for NetworkClass registration:

```yaml
---
title: CUDN Network Implementation
description: >
  Provisions networking resources using ClusterUserDefinedNetwork (CUDN).

template_type: network

# NetworkClass registration fields
implementation_strategy: cudn_net
capabilities:
  supports_ipv4: true
  supports_ipv6: true
  supports_dual_stack: true
```

**Fields:**
- `implementation_strategy` - matches annotation value, role name, and NetworkClass strategy
- `template_type` - `network`, `compute`, or `cluster`
- `capabilities` - feature flags published to NetworkClass

### Creating a New Template Role

1. **Create role directory:**
   ```bash
   mkdir -p collections/ansible_collections/osac/templates/roles/my_network_impl
   cd collections/ansible_collections/osac/templates/roles/my_network_impl
   ```

2. **Create meta/osac.yaml:**
   ```yaml
   ---
   title: My Network Implementation
   description: Provisions networking via my custom backend
   template_type: network
   implementation_strategy: my_network_impl
   capabilities:
     supports_ipv4: true
   ```

3. **Create task files:**
   - `tasks/create_virtual_network.yaml`
   - `tasks/create_subnet.yaml`
   - `tasks/create_security_group.yaml`
   - `tasks/delete_*.yaml`

4. **Test locally:**
   ```bash
   # Create test playbook
   cat > test_my_impl.yml <<EOF
   ---
   - hosts: localhost
     tasks:
       - include_role:
           name: osac.templates.my_network_impl
           tasks_from: create_subnet
         vars:
           subnet:
             metadata:
               name: test-subnet
             spec:
               ipv4Cidr: "10.0.1.0/24"
   EOF
   
   ansible-playbook test_my_impl.yml
   ```

5. **Publish to AAP:**
   Run `playbook_osac_config_as_code.yml` to register the template and create NetworkClass.

## Service Roles

Service roles provide common utilities used across templates and workflows.

### Key Service Roles

| Role | Purpose | Usage |
|------|---------|-------|
| `osac.service.common` | Shared utilities (kubeconfig, credentials) | `tasks_from: get_remote_cluster_kubeconfig` |
| `osac.service.finalizer` | Finalizer management for CRs | `tasks_from: add_finalizer` |
| `osac.service.lease` | Bare metal lease management | Used by cluster/compute workflows |
| `osac.service.wait_for` | Polling utilities | Wait for pods, deployments, CRs |
| `osac.service.tenant_storage_class` | StorageClass discovery | Find tenant-specific storage |
| `osac.service.publish_templates` | Template registration | Publishes NetworkClass from `meta/osac.yaml` |

### Using Service Roles

```yaml
- name: Get remote cluster kubeconfig
  ansible.builtin.include_role:
    name: osac.service.common
    tasks_from: get_remote_cluster_kubeconfig

# Now remote_cluster_kubeconfig variable is available
- name: Create resource on remote cluster
  kubernetes.core.k8s:
    kubeconfig: "{{ remote_cluster_kubeconfig | default(omit) }}"
    state: present
    definition:
      apiVersion: v1
      kind: ConfigMap
      metadata:
        name: my-config
```

## Networking Implementation: cudn_net

The `cudn_net` role implements networking via OpenShift's ClusterUserDefinedNetwork (CUDN).

### Architecture

```
VirtualNetwork (logical grouping)
  └── Subnet (Namespace + CUDN + IPAM)
        └── SecurityGroup (NetworkPolicy)
```

**VirtualNetwork:**
- Logical grouping only (no K8s resources created)
- Stores CIDR blocks and implementation strategy
- Parent reference for Subnets

**Subnet:**
- Creates **Namespace** with labels for OVN primary UDN
- Creates **ClusterUserDefinedNetwork** with namespaceSelector
- Provisions Layer-2 network with persistent IPAM

**SecurityGroup:**
- Creates **NetworkPolicy** in target namespace
- Translates ingress/egress rules to K8s NetworkPolicy
- Supports protocols (TCP, UDP, ICMP), port ranges, CIDR sources

### Key Files

**Subnet provisioning:**
- `collections/ansible_collections/osac/templates/roles/cudn_net/tasks/create_subnet.yaml`
- Creates Namespace with `k8s.ovn.org/primary-user-defined-network: ""` label
- Creates CUDN with `network.spec.subnets` from `subnet.spec.ipv4Cidr` / `subnet.spec.ipv6Cidr`

**SecurityGroup provisioning:**
- `collections/ansible_collections/osac/templates/roles/cudn_net/tasks/create_security_group.yaml`
- Translates SecurityGroup CR to NetworkPolicy
- Maps ingress/egress rules to podSelector, policyTypes

### Variable Flow

```
osac-operator
  ↓ (triggers AAP job template)
playbook_osac_create_subnet.yml
  ↓ (sets implementation_strategy from annotation)
osac.templates.cudn_net (role)
  ↓ (reads subnet.spec.*, creates K8s resources)
Namespace + ClusterUserDefinedNetwork
```

## Testing

### Linting

```bash
# Lint all playbooks and roles
ansible-lint

# Lint specific playbook
ansible-lint playbook_osac_create_subnet.yml

# Lint collection
ansible-lint collections/ansible_collections/osac/templates/
```

### Integration Tests

Integration tests use `ansible-test`:

```bash
# Run all integration tests
ansible-test integration

# Run specific test target
ansible-test integration cluster_create

# Run with specific Python version
ansible-test integration --python 3.13
```

**Test structure:**
```
tests/integration/targets/{test_name}/
├── tasks/
│   └── main.yml              # Test tasks
├── defaults/
│   └── main.yml              # Test variables
└── meta/
    └── main.yml              # Test dependencies
```

### Manual Testing

```bash
# Test a playbook locally
ansible-playbook playbook_osac_create_subnet.yml \
  -e @samples/subnet_payload.json

# Test against AAP
# (requires AAP credentials and inventory)
ansible-playbook -i inventory/aap.yml playbook_osac_create_subnet.yml
```

## Config-as-Code

The `osac.config_as_code` collection manages AAP configuration declaratively.

### Configuring AAP

```bash
# Deploy all OSAC configuration to AAP
ansible-playbook playbook_osac_config_as_code.yml \
  -e @config/base/controller_config.yml

# Subscribe to event-driven rules
ansible-playbook collections/ansible_collections/osac/config_as_code/playbooks/subscription.yml
```

**What gets configured:**
- Job templates (osac-create-subnet, osac-delete-virtual-network, etc.)
- Inventories (localhost for playbook execution)
- Credentials (K8s kubeconfig, cloud credentials)
- Projects (Git repo sync)
- NetworkClass resources (published from template `meta/osac.yaml`)

### Template Discovery and Publication

The `osac.service.publish_templates` role:
1. Scans `collections/ansible_collections/osac/templates/roles/*/meta/osac.yaml`
2. Creates NetworkClass CR for each network template
3. Registers capabilities (IPv4, IPv6, dual-stack support)

```yaml
# Automatically run during config-as-code playbook
- name: Publish templates to fulfillment API
  ansible.builtin.include_role:
    name: osac.service.publish_templates
```

## Common Patterns

### Extracting CR Fields

```yaml
# Standard pattern for networking resources
- name: Extract Subnet configuration
  ansible.builtin.set_fact:
    subnet_name: "{{ subnet.metadata.name }}"
    subnet_namespace: "{{ subnet.metadata.namespace }}"
    subnet_id: "{{ subnet.metadata.labels['osac.openshift.io/subnet-uuid'] }}"
    subnet_ipv4_cidr: "{{ subnet.spec.ipv4Cidr | default('') }}"
    subnet_tenant_id: "{{ subnet.metadata.annotations['osac.openshift.io/tenant'] }}"
```

### Dynamic Role Inclusion

```yaml
# Load role based on implementation strategy annotation
- name: Call the selected implementation role
  ansible.builtin.include_role:
    name: "osac.templates.{{ implementation_strategy }}"
    tasks_from: create_subnet
```

### Creating K8s Resources

```yaml
# Use kubernetes.core.k8s with remote cluster kubeconfig
- name: Create Namespace for Subnet
  kubernetes.core.k8s:
    kubeconfig: "{{ remote_cluster_kubeconfig | default(omit) }}"
    state: present
    definition:
      apiVersion: v1
      kind: Namespace
      metadata:
        name: "{{ subnet_name }}"
        labels:
          osac.openshift.io/subnet-id: "{{ subnet_id }}"
          osac.openshift.io/tenant: "{{ subnet_tenant_id }}"
```

### Updating CR Status

```yaml
# Update K8s CR status after provisioning
- name: Update Subnet CR status
  kubernetes.core.k8s:
    kubeconfig: "{{ remote_cluster_kubeconfig | default(omit) }}"
    state: patched
    api_version: osac.openshift.io/v1alpha1
    kind: Subnet
    name: "{{ subnet_name }}"
    namespace: "{{ subnet_namespace }}"
    definition:
      status:
        phase: Ready
        backendNetworkID: "{{ subnet_name }}"  # Namespace name
```

### Conditional CIDR Handling

```yaml
# Build subnets array from IPv4/IPv6 CIDRs
- name: Build CUDN subnets array
  ansible.builtin.set_fact:
    cudn_subnets: >-
      {{
        ((subnet_ipv4_cidr | length > 0) | ternary([subnet_ipv4_cidr], []))
        + ((subnet_ipv6_cidr | length > 0) | ternary([subnet_ipv6_cidr], []))
      }}
```

## Common Pitfalls

### 1. Forgetting to Activate venv

**Problem:** `ansible-playbook: command not found`

**Solution:**
```bash
source .venv/bin/activate
# or use uv directly:
uv run ansible-playbook playbook_osac_create_subnet.yml
```

### 2. Stale Vendored Collections

**Problem:** Changes to `collections/requirements.yml` not reflected

**Solution:** Re-vendor collections (see Development Setup)

### 3. Implementation Strategy Mismatch

**Problem:** Playbook fails with "role 'osac.templates.my-impl' not found"

**Fix:** Ensure consistency across:
- Role directory name: `collections/ansible_collections/osac/templates/roles/my_impl/`
- `meta/osac.yaml` field: `implementation_strategy: my_impl`
- Annotation value: `osac.openshift.io/implementation-strategy: my_impl`

**Note:** Use underscores (`_`), not hyphens (`-`), in role names.

### 4. Missing Remote Cluster Kubeconfig

**Problem:** Playbook fails creating resources on remote cluster

**Solution:** Always include common role to set `remote_cluster_kubeconfig`:
```yaml
- name: Include get remote cluster kubeconfig
  ansible.builtin.include_role:
    name: osac.service.common
    tasks_from: get_remote_cluster_kubeconfig
```

### 5. Namespace Label Syntax

**Problem:** OVN primary UDN not assigned to namespace

**Fix:** Label value must be empty string, not missing:
```yaml
# Correct:
labels:
  k8s.ovn.org/primary-user-defined-network: ""

# Incorrect:
labels:
  k8s.ovn.org/primary-user-defined-network:
```

### 6. ansible-lint Warnings

**Problem:** `ansible-lint` fails on playbooks

**Common issues:**
- Missing `name:` on tasks
- Using `shell` instead of `ansible.builtin.command`
- Not using FQCN (fully qualified collection name) for modules

**Fix:**
```yaml
# Bad:
- debug:
    msg: "hello"

# Good:
- name: Display message
  ansible.builtin.debug:
    msg: "hello"
```

## Cross-Repo Coordination

When making changes that span repositories:

### Adding a New Field to Networking Resource

**Typical change order:**
1. **fulfillment-service**: Add field to proto, regenerate
2. **osac-operator**: Add field to CRD spec, update controller
3. **osac-aap**: Update playbook to extract field, pass to role
4. **osac-aap (role)**: Read field, provision infrastructure

**Example: Adding `mtu` field to Subnet**

1. fulfillment-service: Add `int32 mtu = 5;` to `subnet_type.proto`
2. osac-operator: Add `MTU *int32` to `SubnetSpec`
3. osac-aap: Update `playbook_osac_create_subnet.yml`:
   ```yaml
   subnet_mtu: "{{ subnet.spec.mtu | default(1500) }}"
   ```
4. osac-aap: Update `cudn_net/tasks/create_subnet.yaml` to set CUDN MTU

### Adding a New Networking Implementation

1. **osac-aap**: Create new template role with `meta/osac.yaml`
2. **osac-aap**: Test role locally with sample payloads
3. **osac-aap**: Run config-as-code to publish NetworkClass
4. **fulfillment-service**: NetworkClass appears in API (auto-discovered)
5. **Users**: Can create VirtualNetwork with new `networkClass`

## Development Workflow

### Before Committing

```bash
# Lint playbooks and roles
ansible-lint

# Format YAML (if using prettier or similar)
prettier --write "**/*.{yml,yaml}"

# Test playbook syntax
ansible-playbook --syntax-check playbook_osac_create_subnet.yml
```

### Commit Message Format

```bash
git commit -m "MGMT-XXXXX: description of change"
```

**Examples:**
- `MGMT-23730: add PublicIPPool playbook and metallb_l2 role`
- `MGMT-23835: fix cudn_net implementation_strategy hyphen mismatch`

### Pull Request Checklist

- [ ] `ansible-lint` passes
- [ ] Integration tests pass (if applicable)
- [ ] `meta/osac.yaml` updated for template role changes
- [ ] Cross-repo dependencies documented in PR description
- [ ] Playbook tested locally or against AAP

## Environment Variables

Common environment variables used in playbooks/roles:

| Variable | Purpose | Set By |
|----------|---------|--------|
| `ansible_eda.event.payload` | K8s CR data | AAP/EDA event |
| `remote_cluster_kubeconfig` | Path to remote kubeconfig | `osac.service.common` role |
| `implementation_strategy` | Network implementation to use | Extracted from CR annotation |
| `OSAC_AAP_URL` | AAP server URL | osac-operator config |
| `OSAC_AAP_TOKEN` | AAP auth token | osac-operator config |

## Links

- [Ansible Documentation](https://docs.ansible.com/)
- [Ansible Automation Platform](https://www.redhat.com/en/technologies/management/ansible)
- [kubernetes.core collection](https://docs.ansible.com/ansible/latest/collections/kubernetes/core/)
- [osac-operator](../osac-operator/CLAUDE.md) - Kubernetes operator integration
- [fulfillment-service](../fulfillment-service/CLAUDE.md) - Backend API
