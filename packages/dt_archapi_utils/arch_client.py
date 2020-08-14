#!/usr/bin/env python3
#This script is part of the DT Architecture Library for dt-commons

import yaml
import docker
import os
import shutil
import git
import glob
import json
import requests
from git import Repo
from .arch_message import ApiMessage
from .arch_worker import ApiWorker

'''
    THIS LIB INCLUDES FUNCTIONS THAT ALLOW TO COMMUNICATE WITH AN ARCHITECTURE
    API RUNNING ON A SINGLE ROBOT (MSG TYPES FOR VARIOUS ENDPOINTS OF A SINGLE
    ARCHITECTURE API), BUT DO NOT SPECIFY THE REQUIRED API FOR THAT. I.E. THE
    REQUIRED SERVER IS NOT RUNNING WITHIN THE LIBRARY
'''

class ArchAPIClient:
    def __init__(self, hostname="hostname", robot_type=None, client=None):
        #Initialize robot hostname & docker.DockerClient()
        self.hostname = hostname
        self.client = client
        self.name = os.environ['VEHICLE_NAME']

        #Initialize folders and directories
        self.active_config = None
        self.config_path = None
        self.module_path = None
        self.current_configuration = "none"

        self.dt_version = "ente"
        self.status = ApiMessage()
        self.work = ApiWorker(self.client)

        #Retract robot_type
        if robot_type is None:
            if os.path.isfile("/data/config/robot_type"):
                self.robot_type = open("/data/config/robot_type").readline()
            elif os.path.isfile("/data/stats/init_sd_card/parameters/robot_type"):
                self.robot_type = open("/data/stats/init_sd_card/parameters/robot_type").readline()
            else: #error upon initialization = status
                self.status.msg["status"] = "error"
                self.status.msg["message"] = "could not find robot_type in expected paths"
                self.status.msg["data"] = {}
                self.robot_type = ""
        else:
            self.robot_type = robot_type

        #Include !up-to-date! ente version of dt-architecture-data repo
        if os.path.isdir("/data/assets/dt-architecture-data"):
            #danger! bad coding could lead to required reflashing
            shutil.rmtree("/data/assets/dt-architecture-data")
            os.makedirs("/data/assets", exist_ok=True)
            git.Git("/data/assets").clone("git://github.com/duckietown/dt-architecture-data.git", branch=self.dt_version)
        else:
            os.makedirs("/data/assets", exist_ok=True)
            git.Git("/data/assets").clone("git://github.com/duckietown/dt-architecture-data.git", branch=self.dt_version)

        self.config_path = "/data/assets/dt-architecture-data/configurations/"+self.robot_type
        self.module_path = "/data/assets/dt-architecture-data/modules/"


#RE-USE INITIALIZED PATHS: in multi_arch_client
    def config_path(self):
        return self.config_path

    def module_path(self):
        return self.module_path


#PASSIVE MESSAGING: monitoring (info, list, status) requests
    def default_response(self):
        return self.status.msg

    def configuration_status(self):
        config_status = {}
        config_status = self.work.container_status()
        #todo: include error msg upon unhealthy/bad container status
        #msg
        self.status.msg["status"] = "ok"
        self.status.msg["message"] = {}
        self.status.msg["data"] = config_status
        return self.status.msg
        

    def configuration_list(self):
        config_list = {} #re-initialize every time called for (empty when error)
        if self.config_path is not None:
            config_paths = glob.glob(self.config_path + "/*.yaml")
            config_list["configurations"] = [os.path.splitext(os.path.basename(f))[0] for f in config_paths]
            #msg
            self.status.msg["status"] = "ok"
            self.status.msg["message"] = {}
            self.status.msg["data"] = config_list
        else: #error msg
            self.status.msg["status"] = "error"
            self.status.msg["message"] = "could not find configurations for " + self.robot_type + " in dt-architecture-data"
            self.status.msg["data"] = {}
            return self.status.msg

        return self.status.msg


    def configuration_info(self, config):
        try:
            with open(self.config_path + "/" + config + ".yaml", 'r') as file:
                config_info = yaml.load(file, Loader=yaml.FullLoader)
                if "modules" in config_info:
                    mods = config_info["modules"]
                    for m in mods:
                        if "type" in mods[m]:
                            mod_type = mods[m]["type"]
                            mod_config = self.module_info(mod_type)["data"]
                            if "configuration" in mod_config:
                                #Virtually append module configuration info to configuration file
                                config_info["modules"][m]["configuration"] = mod_config["configuration"]
                                #if any additional command was specified in config file, attach module info for input to DockerClient
                                for other in {"command", "privileged", "mem_limit", "memswap_limit", "stdin_open", "tty", "detach", "environment", "restart_policy"}:
                                    #fully compatible with Docker SDK for Python client.containers.run()
                                    if other in mods[m]:
                                        config_info["modules"][m]["configuration"][other] = mods[m][other]
                #msg
                self.status.msg["status"] = "ok"
                self.status.msg["message"] = {}
                self.status.msg["data"] = config_info
                return self.status.msg

        except FileNotFoundError: #error msg
            self.status.msg["status"] = "error"
            self.status.msg["message"] = "Configuration file not found in " + self.config_path + "/" + config + ".yaml"
            self.status.msg["data"] = {}
            return self.status.msg


    def module_list(self):
        mod_list = {} #re-initialize every time called for (empty when error)
        yaml_paths = glob.glob(self.module_path + "/*.yaml")
        mod_list["modules"] = []
        for file in yaml_paths:
            try:
                with open(file, 'r') as fd:
                    print ("loading module: " + file)
                    config = yaml.load(fd, Loader=yaml.FullLoader)
                    filename, ext = os.path.splitext(os.path.basename(file))
                    #mod_list["modules"] = [] #put here, so error msg can be sent
                    mod_list["modules"].append(filename)

            except FileNotFoundError: #error msg
                self.status.msg["status"] = "error"
                self.status.msg["message"] = "Modules not found in " + self.module_path + file + ".yaml"
                self.status.msg["data"] = {}
                return self.status.msg
                #return self.status.error(status="error", msg="Module file not found", data=self.module_path + "/" + file + ".yaml")

        #msg
        self.status.msg["status"] = "ok"
        self.status.msg["message"] = {}
        self.status.msg["data"] = mod_list
        return self.status.msg


    def module_info(self, module):
        try:
            with open(self.module_path + module + ".yaml", 'r') as fd: #"/" +
                mod_info = yaml.load(fd, Loader=yaml.FullLoader)
                config = mod_info["configuration"]

                #Update ports for pydocker from docker-compose
                if "ports" in config:
                    ports = config["ports"]
                    newports = {}
                    for p in ports:
                        external,internal = p.split(":", 1)
                        newports[internal]=int(external)
                    config["ports"] = newports
                #Update volumes for pydocker from docker-compose
                if "volumes" in config:
                    vols = config["volumes"]
                    newvols = {}
                    for v in vols:
                        host, container = v.split(":", 1)
                        newvols[host] = {'bind': container, 'mode':'rw'} #what happens here?
                    config["volumes"] = newvols
                #Update restart_policy
                if "restart" in config:
                    config.pop("restart")
                    restart_policy = {"Name":"always"}
                #Update container_name
                if "container_name" in config:
                    config["name"] = config.pop("container_name")
                #Update image
                if "image" in config:
                    config["image"] = config["image"].replace('${ARCH-arm32v7}','arm32v7' )

                #msg
                self.status.msg["status"] = "ok"
                self.status.msg["message"] = {}
                self.status.msg["data"] = mod_info
                return self.status.msg

        except FileNotFoundError: #error msg
            self.status.msg["status"] = "error"
            self.status.msg["message"] = "Module file not found in " + self.module_path + module + ".yaml"
            self.status.msg["data"] = {}
            return self.status.msg
            #return self.status.error(status="error", msg="Module not found", data=self.module_path + module + ".yaml")


#ACTIVE MESSAGING: activation (pull, stop, ...) requests requiring a DockerClient()
    def configuration_set_config(self, config):
        #Get virtually extended config file with module specs
        mod_config = self.configuration_info(config)["data"]
        #msg
        if self.work.set_config(mod_config)["status"] != "busy":
            self.status.msg["status"] = "ok"
            self.status.msg["message"] = {}
            self.status.msg["data"] = self.work.set_config(mod_config)
        else:
            self.status.msg["status"] = "error"
            self.status.msg["message"] = "The device is still busy with process " + str(self.work.set_config(mod_config)["job_id"])
            self.status.msg["data"] = {}
        return self.status.msg


    def pull_image(self, url):
        #url of form {image_url}:{image_tag}
        #msg
        if self.work.pull_image(url)["status"] != "busy":
            self.status.msg["status"] = "ok"
            self.status.msg["message"] = {}
            self.status.msg["data"] = self.work.pull_image(url)
        else:
            self.status.msg["status"] = "error"
            self.status.msg["message"] = "The device is still busy with process " + str(self.work.pull_image(url)["job_id"])
            self.status.msg["data"] = {}
        return self.status.msg


    def monitor_id(self, id):
        #Get current job status, using id=ETag
        if int(id) in self.work.log:
            #msg
            self.status.msg["status"] = "ok"
            self.status.msg["message"] = {}
            self.status.msg["data"] = self.work.log[int(id)]
        else:
            #msg
            self.status.msg["status"] = "ok"
            self.status.msg["message"] = self.work.log.copy()
            self.status.msg["data"] = {}
        return self.status.msg

    def clear_job_log(self):
        return self.work.clear_log()

    def clearance(self):
        return self.work.clearance()

    def get_image_info(self, image):
        '''get public info with ancestry from Docker Hub

        Parameters:
        image(str): name for docker image

        Returns:
        dict: public info about image
        '''
        def get_config(image_name, reference):
            '''public info about image

            Parameters:
            image_name(str): name of image without tag or sha
            reference(str): tag or sha256

            Returns:
            dict: json with public info about image from Docker Hub 
            '''
            try:
                token_response = json.loads(requests.get('https://auth.docker.io/token?scope=repository:{}:pull&service=registry.docker.io'.format(image_name)).text)
                if "errors" in token_response:
                    raise requests.exceptions.RequestException(token_response)
                token = token_response["token"]
                headers = {
                            'Accept': 'application/vnd.docker.distribution.manifest.v2+json',
                            'Authorization': 'Bearer {}'.format(token)
                }
                url = 'https://registry-1.docker.io/v2/{}/manifests/{}'.format(image_name, reference)
                manifest_response = requests.get(url, headers=headers)
                manifest_json = json.loads(manifest_response.text)
                if "errors" in manifest_json:
                    raise requests.exceptions.RequestException(manifest_json)
                digest_image = manifest_response.headers["Docker-Content-Digest"]
                if int(manifest_json["schemaVersion"]) == 2:
                    digest = manifest_json["config"]["digest"]
                    headers = {'Authorization': 'Bearer {}'.format(token)}
                    url = 'https://registry-1.docker.io/v2/{}/blobs/{}'.format(image_name, digest)
                    config_response = json.loads(requests.get(url, headers=headers).text)
                    config = config_response['container_config']
                    config["digest"] = digest_image
                    return config
                else:
                    config = json.loads(manifest_json["history"][0]["v1Compatibility"])["config"]
                    config["digest"] = digest_image
                    return config    
            except json.decoder.JSONDecodeError as e:
                raise requests.exceptions.RequestException("Error. request: {}; image is: {}; error_message: {}".format(url, str(e), image_name))

        def get_image_from_labels(labels):
            '''get image name from array of labels

            Parameters:
            labels(list): array of labels
            
            Returns:
            str: image name
            '''
            image_name, tag = None, None
            labels_keys = labels.keys()
            image_name_key = next(filter(lambda x: "base.image" in x, labels_keys), None)
            tag_key = next(filter(lambda x: "base.tag" in x, labels_keys), None)
            if image_name_key:
                if "ubuntu" in labels[image_name_key]:
                    image_name = labels[image_name_key]
                else:
                    image_name = "duckietown/{}".format(labels[image_name_key])
            if tag_key:
                tag = labels[tag_key]
            if not image_name:
                return None
            if ":" in image_name:
                return image_name
            return "{}:{}".format(image_name, tag if tag else "latest")

        try:
            if "/" not in image:
                image = "duckietown/{}".format(image)
            image_data = self.client.images.get(image)
            labels = image_data.labels
            sha = image_data.attrs["RepoDigests"][0].split("@")[1]
            data = {}        
            data["image"] = image
            data["sha"] = sha
            data["Labels"] = labels
            ancestry = []
            base_image_name = get_image_from_labels(labels)
            while base_image_name:
                if "ubuntu" in base_image_name:
                    ancestry.append(base_image_name)
                    break
                ancestry.append(base_image_name)
                base_image_name, base_tag = base_image_name.split(':', 1)
                base_image_config = get_config(base_image_name, base_tag)
                labels = base_image_config["Labels"]
                base_image_name = get_image_from_labels(labels)
                

            data["ancestry"] = ancestry
            message = {
                        "status": "ok",
                        "message": None,
                        "data": data
                }
            return message
        except (requests.exceptions.RequestException, docker.errors.ImageNotFound) as e:
            error_msg = {}
            error_msg["status"] = "error"
            error_msg["message"] = str(e) 
            error_msg["data"] = None
            return error_msg
    
