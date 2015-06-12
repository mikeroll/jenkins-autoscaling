#!/usr/bin/python2

from jenkins import Jenkins, LAUNCHER_SSH
from boto import ec2
import os
import json
import time
import yaml
import re
from sys import argv

import util

class SlaveManager(object):

    def __init__(self, ec2_conn, j, config_file='labels.yml', init_file='slave_init.py'):
        super(SlaveManager, self).__init__()
        self.ec2_conn = ec2_conn
        self.j = j
        with open(config_file, 'r') as f:
            self.config = yaml.load(f)
            self.config.pop('_default')
        with open(init_file, 'r') as f:
            self.init = f.read()

    @staticmethod
    def _get_node_id(name):
        return re.match('.* \((.+)\)', name).groups()[0]

    @staticmethod
    def _make_node_name(label, node_id):
        return "{0} ({1})".format(label, node_id)

    def _make_initscript(self, label):
        cred_id = self.j.get_cred_id(self.config[label]['cred_domain'])[0]
        return self.init.replace('{{label}}', label) \
                        .replace('{{cred_id}}', cred_id) \
                        .replace('{{jenkins_url}}', self.j.server)

    # --- public interface

    def start_slaves(self, label, count):
        params = dict(
            (k, self.config[label][k]) for k in [ 
                'key_name', 'instance_type',
                'instance_profile_arn', 'placement',
                'security_group_ids', 'subnet_id'
            ]
        )
        params['min_count'] = count
        params['max_count'] = count

        params['user_data'] = self._make_initscript(label)

        reservation = self.ec2_conn.run_instances(self.config[label]['ami'], **params)
        for instance in reservation.instances:
            instance.add_tags({ 'Name': '{0}-jenkins-slave'.format(label) })
        return [ self._make_node_name(label, i.id) for i in reservation.instances ]


    def delete_slaves(self, nodes):
        for node in nodes:
            j.delete_node(node)
        idle_ids = [ self._get_node_id(node) for node in nodes ]
        self.ec2_conn.terminate_instances(idle_ids)

    def wait_for_slaves(self, nodes, interval=5):
        while not all([ self.j.node_exists(node) for node in nodes ]):
            time.sleep(interval)


if __name__ == '__main__':
    if len(argv) >= 2:
        j_url = argv[1]
    else:
        j_url = 'http://jenkins.poc.devops/'

    ec2_conn = ec2.connect_to_region('eu-west-1')

    username, password = os.getenv('SLAVEMANAGER_CREDS', ':').split(':')
    j = Jenkins(j_url, username=username, password=password)

    manager = SlaveManager(ec2_conn, j, 'labels.yml')

    labels = manager.config.keys()
    state_map = j.get_state_map(labels)

    nodes_to_wait = []
    for label, data in state_map.iteritems():
        candidates = [ 
            n for (n, s) in data['nodes'].iteritems()
            if s['pending'] or s['idle']
        ]

        to_start = len(data['jobs']) - len(candidates) 

        if to_start > 0:
            print("{0:<16}: starting {1} more node(s)".format(label, to_start))
            new_nodes = manager.start_slaves(label, to_start)
            for node in new_nodes:
                print("{0:<16}: -- {1}".format(label, node))
                nodes_to_wait.append(node)
        
        idle_nodes = [ 
            n for n, s in data['nodes'].iteritems()
            if j.get_node_idle_time(n) > manager.config[label]['idle_timeout'] and not s['pending'] 
        ]

        if idle_nodes:
            print("{0:<16}: terminating {1} idle node(s):".format(label, len(idle_nodes)))
            for idle_node in idle_nodes:
                print("{0:<16}: -- {1}".format(label, idle_node))
            manager.delete_slaves(idle_nodes)

    if nodes_to_wait:
        print("Waiting for nodes to become available...")
        manager.wait_for_slaves(nodes_to_wait)

