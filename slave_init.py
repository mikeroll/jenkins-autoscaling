#!/usr/bin/env python

# This script is a template intended to be placed as userdata
# on an ec2 instance.
# Do not run manually


from urllib2 import Request, urlopen
from urllib import urlencode
import json

# replace these
label = "{{label}}"
cred_id = "{{cred_id}}"
jenkins_url = "{{jenkins_url}}"
manager_auth = "{{manager_auth}}"

meta_url = 'http://169.254.169.254/latest/meta-data/'
host = urlopen(meta_url + 'local-ipv4').read()
instance_id = urlopen(meta_url + 'instance-id').read()

name = "{0} ({1})".format(label, instance_id)

j = {
    "name": name,
    "nodeDescription": "",
    "numExecutors": 1,
    "remoteFS": "/opt/jenkins/jenkins-slave",
    "labelString": label,
    "mode": "EXCLUSIVE",
    "type": "hudson.slaves.DumbSlave$DescriptorImpl",
    "retentionStrategy": {
        "stapler-class": "hudson.slaves.RetentionStrategy$Always"
    },
    "nodeProperties": {"stapler-class-bag": "true"},
    "launcher": {
        "stapler-class": "hudson.plugins.sshslaves.SSHLauncher",
        "host": host,
        "port": 22,
        "credentialsId": cred_id,
        "launchTimeoutInSeconds": 360,
        "maxNumRetries": 5
    }
}

params = {
    "name": name,
    "type": "hudson.slaves.DumbSlave$DescriptorImpl",
    "json": json.dumps(j)
}


request = Request("{0}computer/doCreateItem".format(jenkins_url),
                  data=urlencode(params))
if manager_auth:
    request.add_header("Authorization", "Basic %s" % manager_auth)
urlopen(request)
