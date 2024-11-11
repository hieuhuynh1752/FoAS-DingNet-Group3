import pprint, time
from UPISAS.exemplar import Exemplar
import logging
import requests

pp = pprint.PrettyPrinter(indent=4)
logging.getLogger().setLevel(logging.INFO)


class DINGNET(Exemplar):
    """
    A class which encapsulates a self-adaptive exemplar run in a docker container.
    """
    _container_name = ""
    def __init__(self, auto_start: "Whether to immediately start the container after creation" =False, container_name = "dingnet"
                 ):
        '''Create an instance of the SWIM exemplar'''
        dingnet_docker_kwargs = {
            "name":  container_name,
            "image": "dingnet",
            "ports" : {8080:8080}}

        super().__init__("http://localhost:8080", dingnet_docker_kwargs, auto_start)
    
    def start_run(self):
        response = requests.get(f"{self.base_endpoint}/start_run")
        if response.status_code == 200:
            print("start_run endpoint called, response: ", response.status_code)
            return ""
        else:
            print("Failed to start run", response.status_code)
            return []

