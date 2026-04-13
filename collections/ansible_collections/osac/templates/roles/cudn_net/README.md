# cudn_net

Provisions networking resources using ClusterUserDefinedNetwork (CUDN) on OpenShift.

## Resources

### VirtualNetwork

VirtualNetworks define the top-level network isolation boundary with CIDR allocation and implementation strategy selection via NetworkClass.

**Key behaviors:**
- Creates ClusterUserDefinedNetwork CR in the cluster
- Supports IPv4-only, IPv6-only, and dual-stack configurations
- NetworkClass determines the implementation strategy (cudn_net)
- One VirtualNetwork maps to one ClusterUserDefinedNetwork

**Implementation:**
- ClusterUserDefinedNetwork is a cluster-scoped resource
- CIDR ranges are configured via spec.network field
- Layer2 topology is used for CUDN implementation

### Subnet

Subnets subdivide VirtualNetworks into logical segments with isolated namespaces for workload deployment.

**Key behaviors:**
- Creates namespace with specific labels for CUDN attachment
- Namespace labeled with `osac.openshift.io/virtual-network: {vn-name}`
- Namespace labeled with `k8s.ovn.org/primary-user-defined-network: ""`
- Enables pod connectivity to the parent VirtualNetwork's CUDN
- One Subnet maps to one namespace

**Namespace targeting:**
- Pods deployed in the Subnet namespace automatically connect to the VirtualNetwork's CUDN
- No additional network configuration needed on pods
- Network attachment is namespace-based, not interface-based

### SecurityGroup

SecurityGroups translate to Kubernetes NetworkPolicy resources that enforce network traffic rules on pods within Subnet namespaces.

**Key behaviors:**
- One NetworkPolicy per SecurityGroup (named `sg-{security-group-name}`)
- NetworkPolicies are deployed to all Subnet namespaces associated with the SecurityGroup's parent VirtualNetwork
- Pod selection uses label `security-group.osac.io/{sg-name}: ""`
- Multiple SecurityGroups are additive: pods can have multiple SG labels, and traffic is allowed if ANY NetworkPolicy allows it
- Empty ingress/egress rule arrays result in deny-all for that direction

**Rule translation:**
- Protocol "all" → omit protocol field in NetworkPolicy (allows all protocols). Port fields are not applicable and ignored by the API.
- Protocol "tcp" or "udp" → include protocol field with port/endPort. Port fields (`portFrom`, `portTo`) are required.
- Protocol "icmp" → port fields are not applicable and ignored by the API. **Note:** Standard Kubernetes NetworkPolicy does not support ICMP protocol filtering. ICMP rules with a source/destination CIDR will allow all protocols from that CIDR, not just ICMP.
- Port ranges: if portFrom == portTo, use single port; if different, use port + endPort
- Source CIDR → ingress.from.ipBlock.cidr
- Destination CIDR → egress.to.ipBlock.cidr

**Namespace targeting:**
- SecurityGroups apply to namespaces labeled with `osac.openshift.io/virtual-network: {vn-name}`
- If no matching namespaces exist when SecurityGroup is created, the task succeeds with a warning
- When new Subnets are created, the osac-operator re-triggers SecurityGroup reconciliation to apply policies

**Multi-SecurityGroup pattern:**
Pods can have multiple SecurityGroup associations:
```yaml
metadata:
  labels:
    security-group.osac.io/web-sg: ""
    security-group.osac.io/db-sg: ""
```
Each SecurityGroup creates its own NetworkPolicy, and Kubernetes applies them additively (traffic allowed if ANY policy allows).

**Known Limitations:**
- ICMP protocol filtering is not supported by standard Kubernetes NetworkPolicy (only TCP, UDP, SCTP are supported). ICMP rules are translated to NetworkPolicy rules without protocol specification, which effectively allows all traffic from the specified CIDR rather than ICMP-only.

## Implementation Strategy

This role implements the `cudn_net` NetworkClass strategy using OpenShift's ClusterUserDefinedNetwork (CUDN) feature. The implementation follows these patterns:

**For VirtualNetworks:**
- Create ClusterUserDefinedNetwork CR with Layer2 topology
- Configure CIDR ranges from VirtualNetwork spec

**For Subnets:**
- Create namespace with CUDN attachment labels
- Label namespace with parent VirtualNetwork reference
- Pods deployed in namespace automatically connect to CUDN

**For SecurityGroups:**
- Create NetworkPolicy resources in Subnet namespaces
- Translate SecurityGroup rules to NetworkPolicy ingress/egress specs
- Use pod labels for traffic targeting

## Task Files

- `tasks/create_virtual_network.yaml` - Creates ClusterUserDefinedNetwork CR from VirtualNetwork resource
- `tasks/delete_virtual_network.yaml` - Removes ClusterUserDefinedNetwork CR
- `tasks/create_subnet.yaml` - Creates namespace with CUDN labels from Subnet resource
- `tasks/delete_subnet.yaml` - Removes namespace
- `tasks/create_security_group.yaml` - Creates NetworkPolicy resources from SecurityGroup rules
- `tasks/delete_security_group.yaml` - Removes NetworkPolicy resources

## Usage

### Example: VirtualNetwork Provisioning

```yaml
- name: Create VirtualNetwork
  ansible.builtin.include_role:
    name: cudn_net
    tasks_from: create_virtual_network
  vars:
    virtual_network: "{{ ansible_eda.event.payload }}"
    virtual_network_name: "{{ ansible_eda.event.payload.metadata.name }}"
```

### Example: Subnet Provisioning

```yaml
- name: Create Subnet
  ansible.builtin.include_role:
    name: cudn_net
    tasks_from: create_subnet
  vars:
    subnet: "{{ ansible_eda.event.payload }}"
    subnet_name: "{{ ansible_eda.event.payload.metadata.name }}"
```

### Example: SecurityGroup Provisioning

```yaml
- name: Create SecurityGroup
  ansible.builtin.include_role:
    name: cudn_net
    tasks_from: create_security_group
  vars:
    security_group: "{{ ansible_eda.event.payload }}"
```
