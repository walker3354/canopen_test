#!/usr/bin/python3
# sudo ifconfig can0 txqueuelen 10000
# sudo ip link set can0 up type can bitrate 1000000
import tomli
import time
import canopen


class CsCanOpen:
    def __init__(self, can_interface, config_file):
        self.porx_node_list = []
        self.light_node_list = []
        self.control_id = 0
        self.pre_control_id = 1

        self.send_key = False
        self.start = 0
        self.config = self.load_config(config_file)
        self.can_network = self.canopen_init(can_interface)
        self.load_light_nodes(self.config["light"])
        self.load_prox_nodes(self.config["proximity"])

    def load_config(self, config_file):
        with open(config_file, "rb") as f:
            toml_dict = tomli.load(f)
            return toml_dict

    def canopen_init(self, can_interface="can0"):
        network = canopen.Network()
        network.connect(channel=can_interface, bustype='socketcan')
        return network

    def load_light_nodes(self, config):
        for node in config["nodes"]:
            print("Wait for light_node {0:} ready...".format(node["node_id"]))
            can_node = self.can_network.add_node(
                node["node_id"], config["config_file"])
            can_node.rpdo.read()
            can_node.nmt.wait_for_heartbeat()
            self.light_node_list.append(can_node)
        print("Check all light nodes completed!\n")

    def load_prox_nodes(self, config):
        for node in config["nodes"]:
            print("Wait for prox_node {0:} ready...".format(node["node_id"]))
            can_node = self.can_network.add_node(
                node["node_id"], config["config_file"])
            can_node.tpdo.read()
            can_node.nmt.wait_for_heartbeat()
            self.porx_node_list.append(can_node)
        print("Check all prox nodes completed!")
        for node in self.porx_node_list:
            node.tpdo[1].add_callback(self.proximity_callback)

    def proximity_callback(self, msg):
        node_id = msg.cob_id - 384
        for var in msg:
            print(node_id, " : ", var.raw)
            if var.raw < 15:
                self.control_id = node_id
                if not self.send_key:
                    self.start = time.time()
                    self.send_key = True
        if self.send_key and (time.time() - self.start) > 4:
            if self.control_id != 0 and self.control_id != self.pre_control_id:
                print(self.control_id, "sending message")
                for light_node in self.light_node_list:
                    light_node.nmt.state = 'PRE-OPERATIONAL'
                    light_node.rpdo[1][0x6001].phys = self.control_id
                    light_node.rpdo[1].start(0.2)
                    light_node.nmt.state = 'OPERATIONAL'
                    light_node.rpdo[1].stop()
                self.pre_control_id = self.control_id
                self.control_id = 0
            elif self.control_id == self.pre_control_id:
                print("reset")
                for light_node in self.light_node_list:
                    light_node.rpdo[1][0x6001].phys = 0x00
                    light_node.rpdo[1].start(0.2)
                    light_node.rpdo[1].stop()
                self.control_id = 0
                self.pre_control_id = 1
            self.send_key = False

    def disconnect(self):
        self.can_network.disconnect()


def main():
    cs_canopen = CsCanOpen("can0", "./test.toml")
    while True:
        time.sleep(0.2)
    return


if __name__ == "__main__":
    main()
