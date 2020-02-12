from crhelper import CfnResource
from sumoresource import SumoResource
from awsresource import AWSResource

from resourcefactory import ResourceFactory

helper = CfnResource(json_logging=False, log_level='DEBUG')


def get_resource(event):
    resource_type = event.get("ResourceType").split("::")[-1]
    resource_class = ResourceFactory.get_resource(resource_type)
    props = event.get("ResourceProperties")
    resource = resource_class(props)
    params = resource.extract_params(event)
    if isinstance(resource, SumoResource):
        params["remove_on_delete_stack"] = props.get("RemoveOnDeleteStack") == 'true'
    print(params)
    return resource, resource_type, params


@helper.create
def create(event, context):
    # Test with failure cases should not get stuck in progress
    # Optionally return an ID that will be used for the resource PhysicalResourceId,
    # if None is returned an ID will be generated. If a poll_create function is defined
    # return value is placed into the poll event as event['CrHelperData']['PhysicalResourceId']
    resource, resource_type, params = get_resource(event)
    data, resource_id = resource.create(**params)
    print(data)
    print(resource_id)
    helper.Data.update(data)
    helper.Status = "SUCCESS"
    print("Created %s" % resource_type)
    return "%s/%s" % (event.get('LogicalResourceId', ''), resource_id)


@helper.update
def update(event, context):
    resource, resource_type, params = get_resource(event)
    data, resource_id = resource.create(**params)
    print(data)
    print(resource_id)
    helper.Data.update(data)
    helper.Status = "SUCCESS"
    print("Updated %s" % resource_type)
    return "%s/%s" % (event.get('LogicalResourceId', ''), resource_id)
    # If the update resulted in a new resource being created, return an id for the new resource.
    # CloudFormation will send a delete event with the old id when stack update completes


@helper.delete
def delete(event, context):
    if "/" not in event.get('PhysicalResourceId', ""):
        print("%s resource_id not found" % event.get('PhysicalResourceId'))
        return
    resource, resource_type, params = get_resource(event)
    resource.delete(**params)
    helper.Status = "SUCCESS"
    print("Deleted %s" % resource_type)
    # Delete never returns anything. Should not fail if the underlying resources are already deleted. Desired state.


def handler(event, context):
    helper(event, context)

if __name__ == "__main__":
    event = {}
    create(event, None)