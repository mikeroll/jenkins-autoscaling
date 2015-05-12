from jenkins import Jenkins
from xml.etree import ElementTree as ET
from urllib2 import Request
import json

def get_all_labels(self):
    jobs = [ j['name'] for j in self.get_info()['jobs'] ]
    return [ self.get_job_label(j) for j in jobs ]

def get_job_label(self, name):
    config = ET.fromstring(self.get_job_config(name))
    return config.find('assignedNode').text

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

def get_nodes(self, *labels):
    node_map = {}
    if not labels: labels = self.get_all_labels()
    for label in labels:
        req = Request(self.server + '/label/' + label + '/api/json')
        data = json.loads(self.jenkins_open(req))
        nodes = [ n['nodeName'] for n in data['nodes'] ]
        node_infos = {}
        for node in nodes:
            info = self.get_node_info(node)
            node_infos[node] = dict( (k, info[k]) for k in ['idle', 'offline'] )

        node_map.setdefault(label, {})['nodes'] = node_infos

    return node_map

def get_credentials(self, domain='_'):
    req = Request(self.server + 'credential-store/domain/' + domain + '/api/json')
    data = self.jenkins_open(req)
    creds = json.loads(data)['credentials']
    return creds.keys()

def get_state_map(self):
    state_map = self.get_nodes()
    queued_jobs = self.get_queued_jobs()
    for label in state_map:
        state_map[label]['jobs'] = queued_jobs[label]['jobs'] if label in queued_jobs else {}
    return state_map


setattr(Jenkins, 'get_all_labels',     get_all_labels)
setattr(Jenkins, 'get_queued_jobs',    get_queued_jobs)
setattr(Jenkins, 'get_nodes',          get_nodes)
setattr(Jenkins, 'get_job_label',      get_job_label)
setattr(Jenkins, 'get_credentials',    get_credentials)
setattr(Jenkins, 'get_state_map',      get_state_map)