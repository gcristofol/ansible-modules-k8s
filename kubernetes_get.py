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
    
  object_kind:
    description:
      - The desired object to inspect on the Kubernetes api.
    required: true
    default: "present"
    choices: ["pod", "configmap"]   
  namespace:
    description:
      - object name and auth scope, such as for teams and projects.   
  nameSelector:
    description:
      - Object Id that we are interested in.
    required: true

author: "Gerard Cristofol <gerard.cristofol@clearpoint.co.nz>"
'''


import yaml
import json
import base64
import requests


KIND_URL = {
    "pod": "/api/v1/namespaces/{namespace}/pods",
    "configmap": "/api/v1/namespaces/{namespace}/configmaps",
    "service": "/api/v1/namespaces/{namespace}/services"
}
USER_AGENT = "ansible-k8s-module/0.0.1"

# TODO(gcristofol): Watch modules using resourceVersion specified with a watch call, 
# shows changes that occur after that particular version of a resource. 
# Current behaviour defaults to changes from the beginning of history.


def k8s_get_services(module, url, nameSelector, verify):
    r = requests.get(url, auth=(module.params.get("username"), module.params.get("password")), verify=verify)
    if r.status_code >= 400:
        module.fail_json(msg="failed to create the resource: %s" % info['msg'], url=url)
    
    hostnames = []
    for item in r.json()['items']:
        if item['metadata']['name'] == nameSelector:
            for ingress in item['status']['loadBalancer']['ingress']:
                hostnames.append(ingress['hostname'])
            
    return hostnames


def k8s_get_configmaps(module, url, nameSelector, verify):
    r = requests.get(url, auth=(module.params.get("username"), module.params.get("password")), verify=verify)
    if r.status_code >= 400:
        module.fail_json(msg="failed to create the resource: %s" % info['msg'], url=url)
    
    for item in r.json()['items']:
        if item['metadata']['name'] == nameSelector:
            return item['data']
            
    return None

def k8s_get_pods(module, url, nameSelector, verify):
    r = requests.get(url, auth=(module.params.get("username"), module.params.get("password")), verify=verify)
    if r.status_code >= 400:
        module.fail_json(msg="failed to create the resource: %s" % info['msg'], url=url)
    
    for item in r.json()['items']:
            for i in range(0, len(item['spec']['containers'])):
                container = item['spec']['containers'][i]
                if container['name'] == nameSelector:
                    return item['status']['containerStatuses'][i], "running" in json.dumps(item['status']['containerStatuses'][i]['state'])
    return None, False


def main():
    module = AnsibleModule(
        argument_spec=dict(
            http_agent=dict(default=USER_AGENT),

            username=dict(default="admin"),
            password=dict(default="", no_log=True),
            force_basic_auth=dict(default="yes"),
            validate_certs=dict(default=False, type='bool'),
            certificate_authority_data=dict(required=False),
            insecure=dict(default=False, type='bool'),
            verify=dict(default=False, type='bool'),
            api_endpoint=dict(required=True),
            nameSelector=dict(required=True),
            namespace=dict(default="default"),
            object_kind=dict(default="present", choices=["pod", "configmap", "service"])
        ),
        mutually_exclusive=(('username', 'insecure'), ('password', 'insecure')),
        supports_check_mode=True
    )

    api_endpoint = module.params.get('api_endpoint')
    state = module.params.get('state')
    insecure = module.params.get('insecure')
    verify = module.params.get("verify")
    namespace = module.params.get("namespace")
    object_kind = module.params.get("object_kind")
    nameSelector = module.params.get("nameSelector")

    # set the transport type and build the target endpoint url
    transport = 'https'
    if insecure:
        transport = 'http'

    target_endpoint = "%s://%s" % (transport, api_endpoint)


    try:
        url = target_endpoint + KIND_URL[object_kind]
    except KeyError:
        module.fail_json(msg="invalid resource kind specified in the data: '%s'" % kind)
    
    url = url.replace("{namespace}", namespace)

    #Retrieve the json body from the API call
    api_response = {}
    if object_kind == 'pod':
        pod_json_chunk, pod_running_status = k8s_get_pods(module, url, nameSelector, verify)
        api_response['pod'] = pod_json_chunk 
        api_response['pod_running'] = pod_running_status
    elif object_kind == 'configmap':
        configmap_json_chunk = k8s_get_configmaps(module, url, nameSelector, verify)
        api_response['configmap'] =  configmap_json_chunk
    elif object_kind == 'service':
        api_response['service_hostname_list'] = []
        service_hostnames = k8s_get_services(module, url, nameSelector, verify)
        api_response['service_hostname_count'] = len(service_hostnames)
        [api_response['service_hostname_list'].append( hostname ) for hostname in service_hostnames]
        if service_hostnames:
            api_response['service_hostname'] = api_response['service_hostname_list'][0]

    if not api_response:
        module.fail_json(msg="%s not found in the data" % object_kind)

    module.exit_json(changed=False, api_response=api_response)


# import module snippets
from ansible.module_utils.basic import *    # NOQA
from ansible.module_utils.urls import *     # NOQA


if __name__ == '__main__':
    main()
