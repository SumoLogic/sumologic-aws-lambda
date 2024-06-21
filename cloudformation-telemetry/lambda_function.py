from collections import defaultdict
import boto3
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
    lambda_client = boto3.client('lambda')
    try:
        T = telemetryFactory(event, context)
        T.fetch_and_send_telemetry()
        # Self Delete the Telemetry Lambda function
        if event['RequestType']=='Delete':
            print("deleting telemetry lambda")
            response = lambda_client.delete_function(FunctionName=context.invoked_function_arn)
    except Exception as e:
        print(e)
    helper.Status = "SUCCESS"


def lambda_handler(event, context):
    helper(event, context)

def telemetryFactory(event, context):
    # create an obj of default class and return in case of none
    if event['ResourceProperties']['solutionName'] == 'AWSO':
        return awsoTelemetry(event, context)
    else:
        raise NotImplementedError # OR AttributeError
    # elif event['ResourceProperties']['solutionName'] == 'CIS':
    #     return cisTelemetry(event, context)

# Interface
class baseTelemetry(ABC):
    @abstractmethod
    def fetch_and_send_telemetry(self):
        raise NotImplementedError

    # Use clientMixing func from app-client-sdk
    def send_telemetry(self, data, endpoint):
        headers = {'content-type': 'application/json'}
        print("Telemetry enabled")
        r = requests.post(endpoint, data = json.dumps(data), headers=headers)
        
# class cisTelemetry(baseTelemetry): # parentStackSetTelemetry
#     def create_telemetry_data(self):
#         pass

# rename awsoTelemetry to parentStackTelemetry
# in awsoTelemetry only implement enrich_telemetry_data()

class awsoTelemetry(baseTelemetry): # parentStackTelemetry

    def __init__(self, event, context):
        self.event = event
        self.context = context
        self.stackID = event['ResourceProperties']['stackID']
        self.cfclient = boto3.client('cloudformation')
        self.all_resource_statuses=defaultdict(list)
    
    # This function will return True if any of the child resources are *IN_PROGRESS state.
    def __has_any_child_resources_in_progress_state(self):
        print("has_any_child function called")
        all_stacks = self.cfclient.describe_stack_resources(StackName=self.stackID)
        # PrimeInvoke - only responsible for triggering lambda
        # Removing 'Primerinvoke' status from all_stacks status so that it is not considered during status checking else it'll result in endless loop becoz if PriveInvoke is not completed overall stack can't be completed.
        for stack_resource in filter(lambda x: x["LogicalResourceId"] != self.event['LogicalResourceId'] ,all_stacks["StackResources"]): 
            stackStatus = stack_resource["ResourceStatus"]
            if stackStatus.endswith('_IN_PROGRESS'):
                return True
        return False # None of the child resources are in IN_PROGRESS state

    def __create_telemetry_data(self):
        log_data_list=[]
        all_stacks_events = self.cfclient.describe_stack_events(StackName= self.stackID)
        for stack_resource in all_stacks_events["StackEvents"]:
            resourceID = stack_resource["PhysicalResourceId"]
            status = stack_resource["ResourceStatus"]
            resource_status_reason = stack_resource.get('ResourceStatusReason', '')
            if status not in self.all_resource_statuses.get(resourceID, []):
                self.all_resource_statuses[resourceID].append(status)
                log_data = {
                    'requestid': self.context.aws_request_id,
                    'timestamp': stack_resource['Timestamp'].isoformat(timespec='milliseconds'),
                    'data': {
                        'stackId': self.event['StackId'],
                        'resourceType': stack_resource["ResourceType"],
                        'resourceName': stack_resource["LogicalResourceId"],
                        'resourceID': stack_resource["PhysicalResourceId"],
                        'status': stack_resource["ResourceStatus"],
                        'details': resource_status_reason
                    }
                }
                log_data_list.append(log_data)
        return log_data_list

    def enrich_telemetry_data(self, log_data_list):
        static_data = {
            'profile': {
                'sumo': {
                    'deployment': self.event['ResourceProperties']['sumoDeployment'],
                    'orgid': self.event['ResourceProperties']['sumoOrgId'],
                },
                'solution': {
                    'name': self.event['ResourceProperties']['solutionName'],
                    'version': self.event['ResourceProperties']['solutionVersion'],
                },
            }
        }
        for log_data in log_data_list:
            log_data.update(static_data)
        return log_data_list   

    def fetch_and_send_telemetry(self):
        resources_in_progress = True

        while (resources_in_progress):
            resources_in_progress = self.__has_any_child_resources_in_progress_state()
            log_data_list = self.__create_telemetry_data()
            log_data_list = self.enrich_telemetry_data(log_data_list)
            for log_data in log_data_list:
                self.send_telemetry(log_data,self.event['ResourceProperties']['TelemetryEndpoint'])
            # If all child resources are completed except PrimeInvoker, marking PrimeInvoker as completed
            if not resources_in_progress: 
                helper._cfn_response(self.event)
            time.sleep(int(self.event['ResourceProperties']['scanInterval']))
        # If all resources are completed, make final call to know Parent stack status
        if not resources_in_progress :
            log_data_list = self.__create_telemetry_data()
            log_data_list = self.enrich_telemetry_data(log_data_list)
            for log_data in log_data_list:
                print(log_data)
                self.send_telemetry(log_data,self.event['TelemetryEndpoint'])


if __name__=="__main__": 
    event={}
    context = {"aws_request_id":"5678-sxcvbnm-fghjk-123456789"}
    create(event,context)