# Ansible Modules for Kubernetes

This repo contains a subset of ansible-modules to retrieve data from k8s API.

## Usage

###  kubernetes_get

Check the status of a particular pod

    - name: Check that service is up and running
      kubernetes_get:
        api_endpoint: "{{ k8s_api_endpoint }}"
        username: "{{ k8s_username }}"
        password: "{{ k8s_password }}"
        namespace: "{{ environ }}"
        object_kind: pod
        nameSelector: my-service-name
      register: k8s_pod_output
      until: k8s_pod_output['api_response']['pod_running']
      retries: 3
      delay: 10
    

###  kubernetes_manifest

Generate a manifest ini file with the docker images used in the running cluster

    - name: Build a kubernetes cluster manifest
      kubernetes_manifest:
        api_endpoint: 10.0.0.1
        username: admin
        password: edited
        namespace: default
      register: k8s_cluster_output
 
    - fail: msg="Bailing out. this play requires a running cluster"
      when: "not {{ k8s_cluster_output['api_response']['cluster_running'] }}"
    
    - name: Retrieve the cluster information to be accessed in a template
      set_fact:
        cluster_api_response: "{{ k8s_cluster_output['api_response']['cluster'] }}"

    # Create Template file
    - name: Create a template from the variables we just extracted
      template: src=manifest.ini.j2 dest=/tmp/manifest-{{ environ }}.ini

    # Use Template file for lookups
    - debug: msg="Service Image in for edge on {{ environ }} is {{ lookup('ini', 'service.image section=edge file=/tmp/manifest-{{ environ }}.ini') }}"


## Annex 1 manifest.ini.j2

    {% for item in cluster_api_response %}
    [{{ item['name'] }}]
     service.name={{ item['name'] }}
     service.image={{ item['image'] }}
     service.version={{ item['version'] }}
    {% endfor %}