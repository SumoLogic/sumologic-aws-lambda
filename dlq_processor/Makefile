.PHONY: help zip clean

artifact := dlqprocessor.zip

help:
	@echo
	@printf "help\t Display this help message\n"
	@echo
	@printf "clean\t Clean zip artifact\n"
	@echo
	@printf "zip\t Create zip file for useage in AWS lambda\n"
	@echo

clean:
	rm -f $(artifact)

zip:
	zip -r $(artifact) DLQProcessor.js cloudwatchlogs_lambda.js package.json sumo-dlq-function-utils/
