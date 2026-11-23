"""
Tests the inline StaticIpConfigLookupFunction code of the AWS Observability master template.

Usage: python test_network_config_retrieval.py <path to sumologic_observability.master.template.yaml>
Needs moto, boto3 and cfn-flip.
"""
import os, sys, types, unittest
from unittest import mock
os.environ.update(AWS_DEFAULT_REGION="us-east-1", AWS_ACCESS_KEY_ID="x", AWS_SECRET_ACCESS_KEY="x")
import boto3
from cfn_flip import load_yaml
from moto import mock_aws

P = "/sumologic/awso/network"
TEMPLATE = sys.argv.pop(1)


def load_function_module():
    with open(TEMPLATE) as f:
        code = load_yaml(f.read())["Resources"]["StaticIpConfigLookupFunction"]["Properties"]["Code"]["ZipFile"]
    module = types.ModuleType("network_config_retrieval")
    exec(compile(code, "StaticIpConfigLookupFunction", "exec"), module.__dict__)
    return module


@mock_aws
class NetCfgTest(unittest.TestCase):
    def setUp(self):
        self.m = load_function_module()
        self.sent = []
        self.m.send_response = lambda e, c, status, data, reason=None: self.sent.append((status, data, reason))
        ec2 = boto3.client("ec2"); self.ssm = boto3.client("ssm")
        self.vpc = ec2.create_vpc(CidrBlock="10.0.0.0/24")["Vpc"]["VpcId"]
        self.sub = ec2.create_subnet(VpcId=self.vpc, CidrBlock="10.0.0.0/26")["Subnet"]["SubnetId"]
        self.sg = ec2.create_security_group(GroupName="g", Description="d", VpcId=self.vpc)["GroupId"]
        other = ec2.create_vpc(CidrBlock="10.1.0.0/24")["Vpc"]["VpcId"]
        self.other_sub = ec2.create_subnet(VpcId=other, CidrBlock="10.1.0.0/26")["Subnet"]["SubnetId"]

    def put(self, **vals):
        for k, v in vals.items():
            self.ssm.put_parameter(Name=f"{P}/{k.replace('_', '-')}", Value=v,
                                   Type="StringList" if k == "private_subnet_ids" else "String")

    def run_event(self, rtype="Create"):
        self.m.handler({"RequestType": rtype, "ResourceProperties": {"SSMPrefix": P}}, mock.MagicMock())
        return self.sent[-1]

    def test_not_configured(self):
        status, data, _ = self.run_event()
        self.assertEqual(status, "SUCCESS")
        self.assertEqual(data, {"SubnetIds": "", "SecurityGroupId": "", "NatPublicIp": "Not configured", "VpcId": ""})

    def test_configured(self):
        self.put(private_subnet_ids=self.sub, security_group_id=self.sg, nat_public_ip="1.2.3.4", vpc_id=self.vpc)
        status, data, _ = self.run_event("Update")
        self.assertEqual((status, data["SubnetIds"], data["SecurityGroupId"], data["NatPublicIp"]),
                         ("SUCCESS", self.sub, self.sg, "1.2.3.4"))

    def test_partial(self):
        self.put(nat_public_ip="1.2.3.4")
        status, _, reason = self.run_event()
        self.assertEqual(status, "FAILED")
        self.assertIn("Incomplete static outbound IP configuration", reason)

    def test_customer_inputs_only_is_not_configured(self):
        # inputs published for static_outbound_ip.template.yaml must not break an AWSO install
        self.put(vpc_id=self.vpc, private_subnet_ids=self.sub, security_group_id=self.sg)
        self.ssm.put_parameter(Name=f"{P}/elastic-ip-allocation-id", Value="eipalloc-0123456789abcdef0", Type="String")
        status, data, _ = self.run_event()
        self.assertEqual(status, "SUCCESS")
        self.assertEqual(data["NatPublicIp"], "Not configured")
        self.assertEqual(data["SubnetIds"], "")

    def test_subnet_wrong_vpc(self):
        self.put(private_subnet_ids=self.other_sub, security_group_id=self.sg, nat_public_ip="1.2.3.4", vpc_id=self.vpc)
        status, _, reason = self.run_event()
        self.assertEqual(status, "FAILED")
        self.assertIn("does not belong to VPC", reason)

    def test_delete_noop(self):
        status, data, _ = self.run_event("Delete")
        self.assertEqual((status, data), ("SUCCESS", {}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
