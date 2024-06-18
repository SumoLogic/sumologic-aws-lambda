from collections import defaultdict
from re import T
import boto3
from datetime import datetime
import os
import json
import requests
import time
from crhelper import CfnResource
from abc import ABC, abstractmethod


helper = CfnResource(json_logging=False, log_level='INFO', sleep_on_delete=30)

@helper.create
def create(event, context):
    try:
        T = telemetryFactory(event, context)
        T.fetch_and_send_telemetry()
    except Exception as e:
        print(e)
        return "Telemetry failed to sent for Create Stack"    
    helper.Status = "SUCCESS"
    return "Telemetry sent for Create Stack"


@helper.update
def update(event, context):
    try:
        T = telemetryFactory(event, context)
        T.fetch_and_send_telemetry()
    except Exception as e:
        print(e)
        return "Telemetry failed to sent for Update Stack"    
    helper.Status = "SUCCESS"
    return "Telemetry sent for Update Stack"


@helper.delete
def delete(event, context):
    try:
        T = telemetryFactory(event, context)
        T.fetch_and_send_telemetry()
    except Exception as e:
        print(e)
    helper.Status = "SUCCESS"


def lambda_handler(event, context):
    helper(event, context)

def telemetryFactory(event, context):
    if os.getenv['solutionName'] == 'AWSO':
        return awsoTelemetry(event, context)
    else:
        return None
    # elif os.environ['solutionName'] == 'CIS':
    #     return cisTelemetry(event, context)

# Interface
class baseTelemetry(ABC):
    @abstractmethod
    def fetch_and_send_telemetry(self):
        raise NotImplementedError

    def send_telemetry(self, data):
        # paramaterise url variable
        url = 'https://collectors.sumologic.com/receiver/v1/http/ZaVnC4dhaV24CA_LXFO0iHFPLWH8VaEczkwtk-GZYMlTG_Dl2CPQ6YNbmKXf9K3dZQ2aAjTREC_C3TECzVQc1XN7zw5CI5lIR4O4-uYsk4bTELB1MU57AQ=='
        headers = {'content-type': 'application/json'}
        print("Telemetry enabled")
        r = requests.post(url, data = json.dumps(data), headers=headers)
        
# class cisTelemetry(baseTelemetry):
#     def create_telemetry_data(self):
#         pass

class awsoTelemetry(baseTelemetry):

    def __init__(self, event, context):
        self.event = event
        self.context = context
        self.stackID = os.getenv('stackID')
        self.cfclient = boto3.client('cloudformation')
    
    # This function will return True if any of the child resources are *IN_PROGRESS state.
    def __has_any_child_resources_in_progress_state(self): # test
        print("has_any_child function called")
        all_stacks = self.cfclient.describe_stack_resources(StackName=self.stackID)
        # PrimeInvoke - only responsible for triggering lambda
        # Removing 'Primerinvoke' status from all_stacks status so that it is not considered during status checking else it'll result in endless loop becoz if PriveInvoke is not completed overall stack can't be completed.
        for stack_resource in filter(lambda x: x["LogicalResourceId"] != 'Primerinvoke' ,all_stacks["StackResources"]):
            stackStatus = stack_resource["ResourceStatus"]
            if stackStatus.endswith('_IN_PROGRESS'):
                return True
        return False # None of the child resources are in IN_PROGRESS state

    def __create_telemetry_data(self):
        print("create_telemetry_data function called",self.context)
        all_resource_statuses=defaultdict(list) # check where to declare -> if state is persisted between function calls
        log_data_list=[]
        all_stacks_events = self.cfclient.describe_stack_events(StackName= self.stackID)
        for stack_resource in all_stacks_events["StackEvents"]:
            resourceID = stack_resource["PhysicalResourceId"]
            status = stack_resource["ResourceStatus"]
            resource_status_reason = stack_resource.get('ResourceStatusReason', '')
            if status not in all_resource_statuses.get(resourceID, []):
                all_resource_statuses[resourceID].append(status)
                log_data = {
                    'uuid': self.context['aws_request_id'],
                    'timestamp': stack_resource['Timestamp'].isoformat(timespec='milliseconds'),
                    'profile': {
                        'sumo': {
                            'deployment': os.getenv('sumoDeployment'),
                            'orgid': os.getenv('sumoOrgId'),
                        },
                        'solution': {
                            'name': os.getenv('solutionName'),
                            'version': os.getenv('solutionVersion'),
                        },
                    },
                    'data': {
                        'stackId': os.getenv('stackID'),
                        'resourceType': stack_resource["ResourceType"],
                        'resourceName': stack_resource["LogicalResourceId"],
                        'resourceID': stack_resource["PhysicalResourceId"],
                        'status': stack_resource["ResourceStatus"],
                        'details': resource_status_reason
                    }
                }
                log_data_list.append(log_data)
        return log_data_list

    def fetch_and_send_telemetry(self):
        print("fetch_and_send_telemetry function called")
        resources_in_progress = True

        while (resources_in_progress):
            resources_in_progress = self.__has_any_child_resources_in_progress_state()
            log_data_list = self.__create_telemetry_data()
            for log_data in log_data_list:
                self.send_telemetry(log_data)

            time.sleep(int(os.getenv('scanInterval','60')))

if __name__=="__main__": 
    event={}
    context = {"aws_request_id":"5678-sxcvbnm-fghjk-123456789"}
    create(event,context)