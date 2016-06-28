#!/usr/bin/python

DOCUMENTATION = '''
---
module: kubernetes
version_added: "2.1"
short_description: Manage Kubernetes resources.
description:
    - This module can manage Kubernetes resources on an existing cluster using
      the Kubernetes server API. 
options:
  api_endpoint:
    description:
      - The IPv4 API endpoint of the Kubernetes cluster.
    required: true
    default: null
    aliases: ["endpoint"]
  certificate_authority_data:
    description:
      - Certificate Authority data for Kubernetes server. Should be in either
        standard PEM format or base64 encoded PEM data. Note that certificate
        verification is broken until ansible supports a version of
        'match_hostname' that can match the IP address against the CA data.
    required: false
    default: null
  password:
    description:
      - The HTTP Basic Auth password for the API I(endpoint). This should be set
        unless using the C('insecure') option.
    default: null
  username:
    description:
      - The HTTP Basic Auth username for the API I(endpoint). This should be set
        unless using the C('insecure') option.
    default: "admin"
  insecure:
    description:
      - "Reverts the connection to using HTTP instead of HTTPS. This option should
        only be used when execuing the M('kubernetes') module local to the Kubernetes
        cluster using the insecure local port (locahost:8080 by default)."
  verify:
    description:
      - "allows insecure SSL conections"        
  validate_certs:
    description:
      - Enable/disable certificate validation. Note that this is set to
        C(false) until Ansible can support IP address based certificate
        hostname matching (exists in >= python3.5.0).
    required: false
    default: false
  namespace:
    description:
      - object name and auth scope, such as for teams and projects.   

author: "Gerard Cristofol <gerard.cristofol@clearpoint.co.nz>"
'''

import yaml
import json
import base64
import requests


API_URL = "/api/v1/namespaces/{namespace}/pods"


def k8s_get_all_pods(module, url, verify):
    r = requests.get(url, auth=(module.params.get("username"), module.params.get("password")), verify=verify)
    if r.status_code >= 400:
        module.fail_json(msg="failed to retrieve the resource: %s" % info['msg'], url=url)

    result = []    
    for item in r.json()['items']:
            for i in range(0, len(item['spec']['containers'])):
                d = {}
                d["name"] = item['spec']['containers'][i]['name']
                d["running"] = "running" in json.dumps(item['status']['containerStatuses'][i]['state'])
                d["image"] = item['spec']['containers'][i]['image']
                if d["image"].find(':') != -1:
                    d["version"] = d["image"].split(':')[1]
                else:
                    d["version"] = "latest"
                result.append( d )

    running = []
    [running.append(True) for pod in result if pod["running"]]
    return result, len(running) == len(result)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            username=dict(default="admin"),
            password=dict(default="", no_log=True),
            force_basic_auth=dict(default="yes"),
            validate_certs=dict(default=False, type='bool'),
            certificate_authority_data=dict(required=False),
            insecure=dict(default=False, type='bool'),
            verify=dict(default=False, type='bool'),
            api_endpoint=dict(required=True),
            namespace=dict(default="default"),
        ),
        mutually_exclusive=(('username', 'insecure'), ('password', 'insecure')),
        supports_check_mode=True
    )

    api_endpoint = module.params.get('api_endpoint')
    state = module.params.get('state')
    insecure = module.params.get('insecure')
    verify = module.params.get("verify")
    namespace = module.params.get("namespace")

    # Set the transport type and build the target endpoint url
    transport = 'https'
    if insecure:
        transport = 'http'
    target_endpoint = "%s://%s" % (transport, api_endpoint)
    
    url = target_endpoint + API_URL.replace("{namespace}", namespace)

    # Retrieve the json body from the API call
    api_response = {}
    cluster_json, cluster_status = k8s_get_all_pods(module, url, verify)
    api_response['cluster'] = cluster_json
    api_response['cluster_running'] = cluster_status

    if not api_response:
        module.fail_json(msg="cluster data not found")

    module.exit_json(changed=False, api_response=api_response)


# import module snippets
from ansible.module_utils.basic import *    # NOQA
from ansible.module_utils.urls import *     # NOQA


if __name__ == '__main__':
    main()
