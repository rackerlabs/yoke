import json

from fleece.httperror import HTTPError


def load_config():
    with open('config.json', 'r') as config_file:
        raw = config_file.read()
    return json.loads(raw)


def lambda_handler(event, context):
    try:
        config = load_config()
        print(event)
        return {"message": config['message']}
    except Exception as exc:
        print(str(exc))
        raise HTTPError(status=500, message=str(exc))
