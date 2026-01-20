#!/usr/bin/python3

HOST_POWER_STATE_OFF = "HOST_POWER_STATE_OFF"
HOST_POWER_STATE_ON = "HOST_POWER_STATE_ON"
HOST_POWER_STATE_UNSPECIFIED = "HOST_POWER_STATE_UNSPECIFIED"

def ironic_to_osac_power_state(ironic_power_state):
    match ironic_power_state:
        case "power on":
            return HOST_POWER_STATE_ON
        case "power off":
            return HOST_POWER_STATE_OFF
        case _:
            return HOST_POWER_STATE_UNSPECIFIED

def osac_power_state_to_ironic_action(osac_power_state):
    match osac_power_state:
        case "HOST_POWER_STATE_OFF":
            return "off"
        case "HOST_POWER_STATE_ON":
            return "on"
        case _:
            return None


def ironic_node_to_osac_host(ironic_node):
    host = {
        "name": ironic_node["name"],
        "host_class": ironic_node["resource_class"],
        "power_state": ironic_to_osac_power_state(ironic_node["power_state"]),
        "target_power_state": ironic_node["target_power_state"],
    }
    return host


class FilterModule(object):
    def filters(self):
        return {
            'ironic_node_to_osac_host': ironic_node_to_osac_host,
            'osac_power_state_to_ironic_action': osac_power_state_to_ironic_action,
        }
