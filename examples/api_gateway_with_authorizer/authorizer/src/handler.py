import json
import sys
import traceback

import policy


def load_config():
    with open('config.json', 'r') as config_file:
        raw = config_file.read()
    return json.loads(raw)


def lambda_handler(event, context):  # pylint: disable=unused-argument
    try:
        tmp = event['methodArn'].split(':')
        api_gateway_arn = tmp[5].split('/')
        account_id = tmp[4]

        config = load_config()

        expected_token = config['expected_token']
        token = event['authorizationToken']

        authpolicy = policy.AuthPolicy(token, account_id)
        authpolicy.rest_api_id = api_gateway_arn[0]
        authpolicy.region = tmp[3]
        authpolicy.stage = api_gateway_arn[1]

        if token == expected_token:
            authpolicy.allow_all_methods()
        else:
            authpolicy.deny_all_methods()

        return authpolicy.build()
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        raise Exception("Unauthorized")
