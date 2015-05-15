#!/usr/bin/python2

# This script is a template intended to be place as userdata on an ec2 instance.
# Do not run manually


from urllib2 import urlopen
from urllib import urlencode
import json

# replace these
label="{{label}}"
cred_id="{{cred_id}}"
jenkins_url="{{jenkins_url}}"

host=urlopen('http://169.254.169.254/latest/meta-data/local-ipv4').read()
instance_id=urlopen('http://169.254.169.254/latest/meta-data/instance-id').read()

name="{0} ({1})".format(label, instance_id)

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

urlopen("{0}computer/doCreateItem".format(jenkins_url), data=urlencode(params))