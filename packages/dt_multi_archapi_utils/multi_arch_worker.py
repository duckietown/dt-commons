#!/usr/bin/env python3
#This script is part of the DT Architecture Library for dt-commons

import docker
import os
import time
import requests

from multiprocessing import Process, Manager
from dt_archapi_utils.arch_message import ApiMessage, JobLog

'''
    THIS SCRIPT TAKES CARE OF SENDING AND RECEIVING HTTP REQUESTS USING THE
    REQUESTS LIB FROM PYTHON. THE RECEIVED (RAW) MESSAGES ARE STACKED AND SENT
    BACK TO THE MultiArchAPIClient LIB FOR FURTHER PROCESSING.
'''

class MultiApiWorker:
    def __init__(self, fleet=None, port="8083"):
        self.fleet = fleet
        self.port = port

        #Initialize imported classes
        self.status = ApiMessage()

        #Initialize imported classes - default from single worker
        self.manager = Manager()
        self.log = self.manager.dict()
        self.process = None


    def http_get_request(self, device=None, endpoint=None):
        #Can be generalized by specifying a fleet + for loop, instead of device
        #Now chosen as such to avoid piling up any msg here before sending to multi_arch_client
        #Not tested on performance/delay for large fleets

        #Create request url and request object
        url = 'http://' + str(device) + '.local:' + str(self.port) + '/device' + endpoint
        r = requests.get(url)
        if int(r.status_code) != int(200):
            self.status.msg["status"] = "error"
            self.status.msg["message"] = "Bad request for " + str(device) + "with error code " + str(r.status_code)
            self.status.msg["data"] = {}
            return self.status.msg

        try:
            #Save reponse
            response = r.json()
            return response
        except ValueError: #error msg
            self.status.msg["status"] = "error"
            self.status.msg["message"] = "Data cannot be JSON decoded for " + str(device)
            self.status.msg["data"] = {}
            return self.status.msg


    def http_post_request(self, endpoint=None):
        return None
