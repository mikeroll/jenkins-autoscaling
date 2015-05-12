#!/usr/bin/python2

from jenkins import Jenkins, LAUNCHER_SSH
from boto import ec2
import json
import time
import yaml
import re

import util

def load_config():
    with open('labels.yml', 'r') as config:
        return yaml.load(config)

def start_instances(label, slave_config, count):
    ami = slave_config.pop('ami')
    slave_config['min_count'] = count
    slave_config['max_count'] = count
    idle_timeout = slave_config.pop('idle_timeout')
    reservation = conn.run_instances(ami, **slave_config)
    slave_config['idle_timeout'] = idle_timeout
    for instance in reservation.instances:
        instance.add_tags({ 'Name': '{0}-jenkins-slave'.format(label) })
    while not all(i.state == 'running' for i in reservation.instances):
        time.sleep(3)
        for instance in reservation.instances:
            instance.update()
    return reservation.instances

def get_node_id(name):
    return re.match('.* \((.+)\)', name).groups()[0]

def make_slave(jenkins, label, ip, name, port=22):
    jenkins.create_node(
        labels=label,
        name=name,
        launcher=LAUNCHER_SSH, 
        launcher_params={
            'host': ip,
            'port': port,
            'credentialsId': jenkins.get_credentials(domain='SSHSlaves')[0],
            'launchTimeoutInSeconds': 360,
            'maxNumRetries': 3
        },
        numExecutors=1,
        remoteFS='/opt/jenkins/jenkins-slave'
    )


if __name__ == '__main__':
    conn = ec2.connect_to_region('eu-west-1')
    j = Jenkins('http://52.17.66.29/')

    config = load_config()
    labels = config.keys()
    labels.remove('_default')

    state_map = j.get_state_map(labels)
    # print(json.dumps(state_map,indent=4))

    for label, data in state_map.iteritems():
        candidates = [ 
            n for (n, s) in data['nodes'].iteritems()
            if s['pending'] or s['idle']
        ]

        to_start = len(data['jobs']) - len(candidates) 

        if to_start > 0:
            print("{0:<8}: starting {1} more node(s)".format(label, to_start))
            for node in start_instances(label, config[label], to_start):
                print("{0:<8}: -- {1}".format(label, node.id))
                make_slave(j, label, node.private_ip_address, "{0} ({1})".format(label, node.id))
        
        idle_nodes = [ 
            node for node in data['nodes'] 
            if j.get_node_idle_time(node) > config[label]['idle_timeout'] and not s['pending'] 
        ]

        if idle_nodes:
            print("{0:<8}: terminating {1} idle node(s):".format(label, len(idle_nodes)))
            idle_ids = [ get_node_id(name) for name in idle_nodes ]
            conn.terminate_instances(idle_ids)
            for idle_node in idle_nodes:
                print("{0:<8}: -- {1}".format(label, idle_node))
                j.delete_node(idle_node)

