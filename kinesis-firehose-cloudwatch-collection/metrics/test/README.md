# Testing the Template

This section explains how to run the test cases to verify condition based resources and output creation in your CloudFormation template.

Follow below steps to run the test cases in `testtemplate.yaml` file. 

1. Install the [Sumo Logic CloudFormation testing framework](https://pypi.org/project/sumologic-cfn-tester/).
2. Run the command `sumocfntester -f testtemplate.yaml`
3. `report.json` file will be generated with result for each test case.