#!/usr/bin/env python3
#This script is part of the DT Architecture Library for dt-commons

import yaml
import docker
import os
import git
import glob
import requests
import json

from .multi_arch_worker import MultiApiWorker
from .clean_fleet import CleanFleet
#from .listener import FleetScanner

#Import from another folder within dt-commons (no base image)
from dt_archapi_utils.arch_client import ArchAPIClient
from dt_archapi_utils.arch_message import ApiMessage

'''
    THIS LIB INCLUDES FUNCTIONS THAT ALLOW TO COMMUNICATE WITH AN EXTENDED
    ARCHITECTURE API RUNNING ON A SINGLE (PRIVILEGED) ROBOT AND ALLOW TO CONTROL
    A SO CALLED FLEET THROUGH THIS ROBOT BY PASSING A SINGLE HTTP COMMAND. NOTE
    THAT THIS LIB DOES NOT SPECIFY THE REQUIRED API, I.E. THE REQUIRED SERVER IS
    NOT RUNNING WITHIN THE LIBRARY.
'''

class MultiArchAPIClient:
    def __init__(self, client=None, port="8083"): #fleet as yaml file without .yaml
        self.client = client
        self.port = port

        #Initialize folders and classes
        self.current_configuration = "none"
        self.dt_version = "ente"
        self.status = ApiMessage()
        self.cl_fleet = CleanFleet()
        #self.scan = FleetScanner()

        #Define robot_type
        self.robot_type = "none"
        if os.path.isfile("/data/config/robot_type"):
            self.robot_type = open("/data/config/robot_type").readline()
        elif os.path.isfile("/data/stats/init_sd_card/parameters/robot_type"):
            self.robot_type = open("/data/stats/init_sd_card/parameters/robot_type").readline()
        else: #error upon initialization
            self.status("error", "Could not find robot type in expected paths", None)

        #Give main robot an ArchAPIClient
        self.main_name = os.environ['VEHICLE_NAME']
        self.main_api = ArchAPIClient(hostname=self.main_name, robot_type=self.robot_type, client=self.client)
        self.config_path = self.main_api.config_path
        self.module_path = self.main_api.module_path
        self.id_list = dict() #store process log - replace with multiprocessing.Manager()?


    #RESPONSE MESSAGES: extended with device info from fleet file
    def default_response(self, fleet):
        #Initialize worker with fleet and port
        fleet = self.cl_fleet.clean_list(fleet)
        self.work = MultiApiWorker(fleet=fleet, port=self.port)

        #Initialize with main response
        def_response_list = {}
        main_response = self.main_api.default_response()

        if main_response["status"] == "error": #error for main robot
            #error msg
            self.status.msg["status"] = main_response["status"]
            self.status.msg["message"] = main_response["message"]
            self.status.msg["data"] = main_response["data"]
            return self.status.msg
        else: #healthy
            def_response_list["data"] = {}
            def_response_list["data"][self.main_name] = main_response
            #Include messages from fleet
            for name in fleet:
                def_response_list["data"][name] = self.work.http_get_request(device=name, endpoint='/')
                if def_response_list["data"][name]["status"] == "error":
                    self.status.msg["status"] = "error"
                    self.status.msg["message"] = "A fleet device encountered an error"
                else:
                    self.status.msg["status"] = "ok"
                    self.status.msg["message"] = {}
            #msg
            self.status.msg["data"] = def_response_list["data"]
            return self.status.msg


    def configuration_status(self, fleet):
        #Initialize worker with fleet and port
        fleet = self.cl_fleet.clean_list(fleet)
        self.work = MultiApiWorker(fleet=fleet, port=self.port)

        #Initialize with main response
        config_status_list = {}
        config_status_list["data"] = {}
        config_status_list["data"][self.main_name] = self.main_api.configuration_status()

        for name in fleet:
            config_status_list["data"][name] = self.work.http_get_request(device=name, endpoint='/configuration/status')
        #msg
        self.status.msg["status"] = "ok"
        self.status.msg["message"] = {}
        self.status.msg["data"] = config_status_list["data"]
        return self.status.msg


    """
    def configuration_list(self, fleet):
        #Initialize worker with fleet and port
        fleet = self.cl_fleet.clean_list(fleet)
        self.work = MultiApiWorker(fleet=fleet, port=self.port)
        fleet_scan = self.scan.device_list

        #available robot_types in current fleet
        type_list = []
        for name in fleet:
            if name in fleet_scan["duckiebot"]:
                if "duckiebot" not in type_list:
                    type_list = type_list.append("duckiebot")
            if name in fleet_scan["watchtower"]:
                if "watchtower" not in type_list:
                    type_list = type_list.append("watchtower")
            if name in fleet_scan["greenstation"]:
                if "greenstation" not in type_list:
                    type_list = type_list.append("greenstation")
            if name in fleet_scan["duckiedrone"]:
                if "duckiedrone" not in type_list:
                    type_list = type_list.append("duckiedrone")
            if name in fleet_scan["town"]:
                if "town" not in type_list:
                    type_list = type_list.append("town")

        #check which configurations are possible for the present robot_types
        config_list = {}
        if self.config_path is not None:
            config_paths = glob.glob(self.config_path + "/*.yaml")
            config_list["configurations"] = [os.path.splitext(os.path.basename(f))[0] for f in config_paths]
            #open all and check device requirements
            for config in config_list["configurations"]:
                try:
                    with open(self.config_path + "/" + config + ".yaml", 'r') as file:
                        config_info = yaml.load(file, Loader=yaml.FullLoader)
                        if "devices" in config_info:
                            for type in config_info["devices"]:
                                if type not in type_list:
                                    #as soon as type is not present in fleet, remove configuration possiblity
                                    del config_list["configurations"][config]

                except FileNotFoundError: #error msg
                    self.status.msg["status"] = "error"
                    self.status.msg["message"] = "Configuration file not found in " + self.config_path + "/" + config + ".yaml"
                    self.status.msg["data"] = {}
                    return {}
        else: #error msg
            self.status.msg["status"] = "error"
            self.status.msg["message"] = "could not find configurations for " + self.robot_type + " in dt-architecture-data"
            self.status.msg["data"] = {}
            return {}

        #only list possible configurations for the robot_types in fleet
        return config_list
    """

    def configuration_info(self, config):
        #Initialize worker with fleet and port
        #fleet = self.cl_fleet.clean_list(fleet)
        #self.work = MultiApiWorker(fleet=fleet, port=self.port)

        #Initialize with main response
        config_info_list = self.main_api.configuration_info(config)
        if config_info_list["status"] == "error": #error msg
            #Do not proceed with messages from fleet
            self.status.msg["status"] = config_info_list["status"]
            self.status.msg["message"] = config_info_list["message"]
            self.status.msg["data"] = config_info_list["data"]
            return self.status.msg
        else: #healthy
            try:
                with open(self.config_path + "/" + config + ".yaml", 'r') as file: #"/data/assets/dt-architecture-data/configurations/town/"
                    device_info = yaml.load(file, Loader=yaml.FullLoader)
                    #print(device_info)
                    #print("devices" in device_info)
                    if "devices" in device_info:
                        for device in device_info["devices"]:
                            if "configuration" in device_info["devices"][device]:
                                c_name = device_info["devices"][device]["configuration"] #save config name
                                if c_name is not {}:
                                    device_info["devices"][device]["configuration"] = {} #initialize for config info
                                    #dt-architecture-data configurations depend on robot_type
                                    new_robot_type_as_device = ArchAPIClient(robot_type=device)
                                    device_info["devices"][device]["configuration"][c_name] = {}
                                    device_info["devices"][device]["configuration"][c_name] = new_robot_type_as_device.configuration_info(config=c_name)

                        config_info_list["data"]["devices"] = device_info["devices"]
                        #msg
                        self.status.msg["status"] = config_info_list["status"]
                        self.status.msg["message"] = config_info_list["message"]
                        self.status.msg["data"] = config_info_list["data"]
                    return self.status.msg

            except FileNotFoundError: #error msg
                self.status.msg["status"] = "error"
                self.status.msg["message"] = "Configuration file not found in " + self.config_path + "/" + config + ".yaml"
                self.status.msg["data"] = {}
                return self.status.msg


    def configuration_set_config(self, config, fleet):
        #Initialize worker with fleet and port
        fleet = self.cl_fleet.clean_list(fleet)
        fleet_name = self.cl_fleet.fleet
        self.work = MultiApiWorker(fleet=fleet, port=self.port)

        #Check if there is any busy process in the fleet
        cl_list = self.clearance_list(fleet)
        nogo = {}
        for name in fleet:
            if cl_list[name]["status"] == "busy":
                nogo[name] = cl_list[name]
        if nogo != {}:
            self.status.msg["status"] = "error"
            self.status.msg["message"] = "One or more fleet devices are still busy with another process, cannot proceed"
            self.status.msg["data"] = cl_list
            return self.status.msg

        #Initialize with main response
        main_response = self.main_api.configuration_set_config(config)
        #Create list for logging
        self.id_list[fleet_name] = main_response
        print(self.id_list)
        self.id_list[fleet_name]["data"] = {}
        for name in fleet:
            self.id_list[fleet_name]["data"][name] = self.work.http_get_request(device=name, endpoint='/configuration/set/' + config)

        #Create response message
        set_config_list = {}
        set_config_list["data"] = self.id_list[fleet_name]
        print("debug_checkpoint")

        self.status.msg["status"] = "ok"
        self.status.msg["message"] = {}
        self.status.msg["data"] = set_config_list
        return self.status.msg


    def monitor_id(self, id, fleet):
        #Initialize worker with fleet and port
        fleet = self.cl_fleet.clean_list(fleet)
        fleet_name = self.cl_fleet.fleet
        self.work = MultiApiWorker(fleet=fleet, port=self.port)

        #Initialize with main response
        main_response = self.main_api.monitor_id(id)


        #This is only required outside of Dashboard, as Dashboard automatically uses most recent id (coupled with 'set' requests)
        #Clean up self.id_list working after integration in Dashboard
        ########################################################################################################
        #Is there a process going on?
        if fleet_name in self.id_list:
            #Check if id is a match with most recent process on main device
            if int(self.id_list[fleet_name]['job_id']) == int(id):
                #Initialize list
                monitor_list = main_response
                monitor_list["data"] = {}
                #Include messages from fleet
                id_list = self.id_list[fleet_name]["data"]
                for name in fleet:
                    monitor_list["data"][name] = self.work.http_get_request(device=name, endpoint='/monitor/' + str(id_list[name]["job_id"]))
                    monitor_list["data"][name] = monitor_list["data"][name]["data"]

                #msg
                monitor_id_list = {}
                monitor_id_list["data"] = monitor_list["data"]
                monitor_id_list["data"][self.main_name] = main_response

                self.status.msg["status"] = "ok"
                self.status.msg["message"] = {}
                self.status.msg["data"] = monitor_id_list["data"]
                return self.status.msg
            else: #false id
                self.status.msg["status"] = "error"
                self.status.msg["message"] = "The specified id " + str(id) + " does not match most recent process for fleet " + fleet_name
                self.status.msg["data"] = {}
                return self.status.msg
        else: #no process
            self.status.msg["status"] = "error"
            self.status.msg["message"] = "There is no process for fleet " + fleet_name
            self.status.msg["data"] = {}
            return self.status.msg
        ########################################################################################################


    def info_fleet(self, fleet):
        #Initialize worker with fleet and port
        fleet = self.cl_fleet.clean_list(fleet)
        fleet_name = self.cl_fleet.fleet
        self.work = MultiApiWorker(fleet=fleet, port=self.port)

        #Initialize with main response
        try:
            with open(self.cl_fleet.fleet_path + fleet_name + ".yaml", 'r') as file: #replace with data/config/fleets/...
                info_fleet = yaml.load(file, Loader=yaml.FullLoader)
                self.status.msg["status"] = "ok"
                self.status.msg["message"] = {}
                self.status.msg["data"] = info_fleet
                return self.status.msg
        except FileNotFoundError: #error msg
            self.status.msg["status"] = "error"
            self.status.msg["message"] = "Fleet file not found in /data/assets/.../lists/" + fleet_name + ".yaml" #replace with data/config/fleets/...
            self.status.msg["data"] = {}
            return {}


    #def fleet_scan(self):
    #    return self.scan.device_list #see configuration_info as well for use!
    #    FleetScanner(service_in_callback=cb)
    #    #don't use a fleet, just return all available devices on the network,
    #    #as a function that can be used by calling the architecture API
    #    self.available_devices = {}
    #    self.available_devices["available devices"], self.appear_msgs = self.scan.listen_to_network()
    #    return self.available_devices


    def clearance_list(self, cl_fleet):
        #Note: this already takes in a clean fleet list
        #Initialize with main response
        cl_list = {}
        cl_list[self.main_name] = self.main_api.clearance()

        #Proceed with fleet devices
        for name in cl_fleet:
            cl_list[name] = self.work.http_get_request(device=name, endpoint='/clearance')
        return cl_list



"""
    def something(self):
                ########################################################################################################
                #All processes on this device have been stored in self.id_list
                if self.id_list != {}:
                    #First go through all main device information
                    for any_fleet_so_far in self.id_list:
                        #Check if main device has process running - avoid expensive status loop for fleet devices
                        if self.id_list[any_fleet_so_far] != "busy": #should never happen here
                            if self.id_list[any_fleet_so_far]["status"] in {"pending", "processing", "error"}:
                                busy_id = self.id_list[any_fleet_so_far]['job_id']
                                self.status.msg["status"] = "error"
                                self.status.msg["message"] = "Cannot set " + config + " while" + self.main_name + " has a process going on - use device/monitor/" + busy_id
                                self.status.msg["data"] = {}
                                return "busy"
                        else: #should never happen, as you don't ask it to start a new process
                            self.status.msg["status"] = "error"
                            self.status.msg["message"] = "Cannot set " + config + " while" + self.main_name " is busy"
                            self.status.msg["data"] = {}
                            return "busy"
                        #note, do not name two different fleets with the same name!
                        #should give error from Dashboard

                    #Only now, when main not busy, go through all fleet information belonging to this device
                    for any_fleet_so_far in self.id_list:
                        #Was device in fleet part of any previous fleet or process?
                        for name in fleet:
                            if name in self.id_list[any_fleet_so_far]["data"]:
                                if self.id_list[any_fleet_so_far]["data"][name] != "busy": #should never happen here
                                    if self.id_list[any_fleet_so_far]["data"][name]["status"] in {"pending", "processing", "error"}:
                                        busy_id = self.id_list[any_fleet_so_far]["data"][name]['job_id']
                                        self.status.msg["status"] = "error"
                                        self.status.msg["message"] = "Cannot set " + config + " while" + name + " in fleet has a process going on - use fleet/monitor/" + busy_id +"/" + fleet_name
                                        self.status.msg["data"] = {}
                                        return "busy"
                                else: #should never happen, as you don't ask it to start a new process
                                    self.status.msg["status"] = "error"
                                    self.status.msg["message"] = "Cannot set " + config + " while" + name " in fleet is busy"
                                    self.status.msg["data"] = {}
                                    return "busy"
                ########################################################################################################

    def fleet(self):
        #Check if any device is busy from last process where it was part of any fleet so far
        current_id = main_set_config['job_id']
        monitor_check = self.monitor_id(current_id, fleet_name)
        #Check if there was a previous process for this fleet and device that was saved
        #Note: if another fleet was used with overlapping devices, there will be no check - cannot be!!
        for any_fleet_so_far in self.id_list:
            #note, do not name two different fleets with the same name!
            for name in fleet:
                if self.id_list[any_fleet_so_far]["data"][name]:
                if self.ok is no:
                    self.not_ok
                    #as soon as there is a device from THIS fleet busy, abort
                    return {}
        if fleet_name in self.id_list:
            #if so, check if there is any process 'busy'
            for name in fleet:
                if self.id_list[fleet_name]["data"][""] == "busy":
                    self.status.msg["status"] = "error"
                    self.status.msg["message"] = "Could not set " + config + " while a fleet device is busy - use fleet/monitor/<" + main_set_config['job_id'] +">/<" + fleet_name + ">"
                    self.status.msg["data"] = {}
                    return {}


    def configuration_list(self, fleet=None):
        #Initialize worker with fleet and port
        fleet = self.cl_fleet.clean_list(fleet)
        self.work = MultiApiWorker(fleet=fleet, port=self.port)

        #SCAN FLEET = LISTEN TO AVAHI SERVICES
        config_list = {} #re-initialize every time called for (empty when error)
        current_fleet = self.scan.for_devices
        config_list[str(self.main_name)] = self.main_api.configuration_list
        if self.config_path is not None:
            config_paths = glob.glob(self.config_path + "/*.yaml")
            config_list["configurations"] = [os.path.splitext(os.path.basename(f))[0] for f in config_paths]
        else: #error msg
            self.status["status"] = "error"
            self.status["message"].append("could not find configurations (dt-docker-data)")
            return self.status
        return config_list
"""
