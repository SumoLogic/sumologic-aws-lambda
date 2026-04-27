import logging
import json
from sumoresource import SumoResource
from resourcefactory import ResourceFactory

try:
    from crhelper import CfnResource
    helper = CfnResource(json_logging=False, log_level='INFO', sleep_on_delete=30)
    USE_CRHELPER = True
except ImportError:
    helper = None
    USE_CRHELPER = False

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_resource(event):
    """Factory method to get a resource object and parameters."""
    resource_type = event.get("ResourceType", "").split("::")[-1]
    resource_class = ResourceFactory.get_resource(resource_type)
    props = event.get("ResourceProperties", {})
    resource = resource_class(props)
    params = resource.extract_params(event)

    if isinstance(resource, SumoResource):
        params["remove_on_delete_stack"] = props.get("RemoveOnDeleteStack") == 'true'

    return resource, resource_type, params


# --------------------------
# CFN path (crhelper managed)
# --------------------------
if USE_CRHELPER:

    @helper.create
    def create(event, context):
        resource, resource_type, params = get_resource(event)
        try:
            data, resource_id = resource.create(**params)
        except Exception as e:
            logger.error(f"Create failed for {resource_type}: {e}")
            raise
        helper.Data.update(data)
        helper.Status = "SUCCESS"
        logger.info(f"Created {resource_type} with ID {resource_id}")
        return f"{event.get('LogicalResourceId', '')}/{resource_id}"

    @helper.update
    def update(event, context):
        resource, resource_type, params = get_resource(event)
        data, resource_id = resource.update(**params)
        helper.Data.update(data)
        helper.Status = "SUCCESS"
        logger.info(f"Updated {resource_type} with ID {resource_id}")
        return f"{event.get('LogicalResourceId', '')}/{resource_id}"

    @helper.delete
    def delete(event, context):
        phys_id = event.get("PhysicalResourceId", "")
        if "/" not in phys_id:
            logger.warning(f"{phys_id} resource_id not found")
            return
        resource, resource_type, params = get_resource(event)
        resource.delete(**params)
        helper.Status = "SUCCESS"
        logger.info(f"Deleted {resource_type}")


def handler(event, context):
    """
    Common handler (CF + TF)
    """
    logger.info(f"Received event: {json.dumps(event)}")

    # CloudFormation event → delegate to crhelper
    if "RequestType" in event and USE_CRHELPER:
        return helper(event, context)

    # Terraform/direct invoke path
    action = event.get("action")
    logger.info(f"Terraform action detected: {action}")

    if action in ["create", "update", "delete"]:
        resource, resource_type, params = get_resource(event)
        try:
            if action == "create":
                data, resource_id = resource.create(**params)
            elif action == "update":
                data, resource_id = resource.update(**params)
            elif action == "delete":
                resource.delete(**params)
                return {"status": "success", "deleted": True}
        except Exception as e:
            logger.error(f"{action} failed for {resource_type}: {e}")
            return {"status": "failed", "reason": str(e)}

        return {"status": "success", "id": resource_id, "data": data}

    return {"status": "failed", "reason": f"Unknown action {action}"}


if __name__ == "__main__":
    # Example local test
    test_event = {
        "action": "create",
        "ResourceType": "Custom::MyResource",
        "ResourceProperties": {
            "BucketName": "my-bucket",
            "RemoveOnDeleteStack": "true"
        }
    }
    print(handler(test_event, None))
