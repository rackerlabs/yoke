import json


def load_config():
    with open('config.json', 'r') as config_file:
        raw = config_file.read()
    return json.loads(raw)


def lambda_handler(event, context):
    config = load_config()
    print(event)
    return {"message": config['message']}
