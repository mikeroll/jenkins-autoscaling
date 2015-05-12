#!/usr/bin/python2

from jenkins import Jenkins, LAUNCHER_SSH
from boto import ec2
import json
import time
import yaml

import jenkins_util

def load_config():
    with open('slaves.yml', 'r') as config:
        return yaml.load(config)

def start_instances(label, slave_config, count):
    ami = slave_config.pop('ami')
    slave_config['min_count'] = count
    slave_config['max_count'] = count
    reservation = conn.run_instances(ami, **slave_config)
    for instance in reservation.instances:
        instance.add_tags({ 'Name': '{0}-jenkins-slave'.format(label) })
    while not all(i.state == 'running' for i in reservation.instances):
        time.sleep(3)
        for instance in reservation.instances:
            instance.update()
    return reservation.instances

def make_slave(jenkins, label, ip, name, port=22):
    jenkins.create_node(
        labels=label,
        name=name,
        launcher=LAUNCHER_SSH, 
        launcher_params={
            'host': ip,
            'port': port,
            'credentialsId': jenkins.get_credentials(domain='SSHSlaves')[0],
            'launchTimeoutInSeconds': 180,
            'maxNumRetries': 3
        },
        numExecutors=1,
        remoteFS='/opt/jenkins/jenkins-slave'
    )


if __name__ == '__main__':
    conn = ec2.connect_to_region('eu-west-1')
    j = Jenkins('http://52.17.66.29/')

    config = load_config()

    state_map = j.get_state_map()
    print(json.dumps(state_map, indent=4))

    for label, data in state_map.iteritems():
        if data['jobs']:
            print("{0:<8}: {1} waiting jobs".format(label, len(data['jobs'])))
            nodes = start_instances(label, config[label], len(data['jobs']))
            for node in nodes:
                make_slave(j, label, node.private_ip_address, "{0} ({1})".format(label, node.id))
