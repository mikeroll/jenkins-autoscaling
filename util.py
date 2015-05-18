from jenkins import Jenkins
from xml.etree import ElementTree as ET
from urllib2 import Request
import json
import time


def get_job_label(self, name):
    return ET.fromstring(self.get_job_config(name)).find('assignedNode').text

def get_queued_jobs(self):
    queue = self.get_queue_info()
    job_map = {}
    for job in queue:
        name = job['task']['name']
        label = self.get_job_label(name)
        job_map.setdefault(label, {}) \
               .setdefault('jobs', []) \
               .append(name)
    return job_map

def get_nodes(self, labels):
    node_map = {}
    for label in labels:
        req = Request(self.server + 'label/' + label + '/api/json')
        data = json.loads(self.jenkins_open(req))
        nodes = [ n['nodeName'] for n in data['nodes'] ]
        node_infos = {}
        for node in nodes:
            info = self.get_node_info(node)
            node_infos[node] = { 
                'pending': info['offline'] and not info['offlineCause'],
                'idle': info['idle']
        }

        node_map.setdefault(label, {})['nodes'] = node_infos

    return node_map

def get_cred_id(self, domain='_'):
    req = Request(self.server + 'credential-store/domain/' + domain + '/api/json')
    data = self.jenkins_open(req)
    creds = json.loads(data)['credentials']
    return creds.keys()

def get_node_idle_time(self, node):
    now = int(time.time())
    groovy = 'script=return Jenkins.instance.getComputer("{0}").getIdleStartMilliseconds()'.format(node)
    req = Request(self.server + 'scriptText', data=groovy)
    idle_start = int(self.jenkins_open(req)[8:]) / 1000
    return now - idle_start

def get_state_map(self, labels):
    state_map = self.get_nodes(labels)
    queued_jobs = self.get_queued_jobs()
    for label in state_map:
        state_map[label]['jobs'] = queued_jobs[label]['jobs'] if label in queued_jobs else {}
    return state_map

setattr(Jenkins, 'get_queued_jobs',    get_queued_jobs)
setattr(Jenkins, 'get_nodes',          get_nodes)
setattr(Jenkins, 'get_job_label',      get_job_label)
setattr(Jenkins, 'get_cred_id',        get_cred_id)
setattr(Jenkins, 'get_node_idle_time', get_node_idle_time)
setattr(Jenkins, 'get_state_map',      get_state_map)
