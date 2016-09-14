DEFAULT_RESPONSES = {
  '^300:.*': {'responseTemplates': {'application/json': '{"error": {"code": 300, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '300'},
  '^301:.*': {'responseTemplates': {'application/json': '{"error": {"code": 301, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '301'},
  '^302:.*': {'responseTemplates': {'application/json': '{"error": {"code": 302, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '302'},
  '^303:.*': {'responseTemplates': {'application/json': '{"error": {"code": 303, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '303'},
  '^304:.*': {'responseTemplates': {'application/json': '{"error": {"code": 304, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '304'},
  '^305:.*': {'responseTemplates': {'application/json': '{"error": {"code": 305, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '305'},
  '^307:.*': {'responseTemplates': {'application/json': '{"error": {"code": 307, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '307'},
  '^400:.*': {'responseTemplates': {'application/json': '{"error": {"code": 400, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '400'},
  '^401:.*': {'responseTemplates': {'application/json': '{"error": {"code": 401, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '401'},
  '^402:.*': {'responseTemplates': {'application/json': '{"error": {"code": 402, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '402'},
  '^403:.*': {'responseTemplates': {'application/json': '{"error": {"code": 403, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '403'},
  '^404:.*': {'responseTemplates': {'application/json': '{"error": {"code": 404, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '404'},
  '^405:.*': {'responseTemplates': {'application/json': '{"error": {"code": 405, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '405'},
  '^406:.*': {'responseTemplates': {'application/json': '{"error": {"code": 406, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '406'},
  '^407:.*': {'responseTemplates': {'application/json': '{"error": {"code": 407, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '407'},
  '^408:.*': {'responseTemplates': {'application/json': '{"error": {"code": 408, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '408'},
  '^409:.*': {'responseTemplates': {'application/json': '{"error": {"code": 409, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '409'},
  '^410:.*': {'responseTemplates': {'application/json': '{"error": {"code": 410, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '410'},
  '^411:.*': {'responseTemplates': {'application/json': '{"error": {"code": 411, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '411'},
  '^412:.*': {'responseTemplates': {'application/json': '{"error": {"code": 412, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '412'},
  '^413:.*': {'responseTemplates': {'application/json': '{"error": {"code": 413, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '413'},
  '^414:.*': {'responseTemplates': {'application/json': '{"error": {"code": 414, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '414'},
  '^415:.*': {'responseTemplates': {'application/json': '{"error": {"code": 415, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '415'},
  '^416:.*': {'responseTemplates': {'application/json': '{"error": {"code": 416, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '416'},
  '^417:.*': {'responseTemplates': {'application/json': '{"error": {"code": 417, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '417'},
  '^418:.*': {'responseTemplates': {'application/json': '{"error": {"code": 418, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '418'},
  '^422:.*': {'responseTemplates': {'application/json': '{"error": {"code": 422, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '422'},
  '^423:.*': {'responseTemplates': {'application/json': '{"error": {"code": 423, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '423'},
  '^500:.*': {'responseTemplates': {'application/json': '{"error": {"code": 500, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '500'},
  '^501:.*': {'responseTemplates': {'application/json': '{"error": {"code": 501, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '501'},
  '^502:.*': {'responseTemplates': {'application/json': '{"error": {"code": 502, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '502'},
  '^503:.*': {'responseTemplates': {'application/json': '{"error": {"code": 503, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '503'},
  '^504:.*': {'responseTemplates': {'application/json': '{"error": {"code": 504, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '504'},
  '^505:.*': {'responseTemplates': {'application/json': '{"error": {"code": 505, "message": $input.json(\'$.errorMessage\')}}'},
   'statusCode': '505'},
  'default': {'responseTemplates': {'application/json': '__passthrough__'},
   'statusCode': '200'}
}

APPLICATION_JSON_REQUEST = """\
{
  "operation": "{{ operation }}",
  "parameters": {
    "gateway": {
      "id": "$context.apiId",
      "stage": "$context.stage",
      "request-id" : "$context.requestId",
      "resource-path" : "$context.resourcePath",
      "http-method": "$context.httpMethod",
      "stage-data": {
        #foreach($param in $stageVariables.keySet())
        "$param": "$util.escapeJavaScript($stageVariables.get($param))" #if($foreach.hasNext),#end
        #end
      }
    },
    "requestor": {
      "source-ip": "$context.identity.sourceIp",
      "user-agent": "$context.identity.userAgent",
      "account-id" : "$context.identity.accountId",
      "api-key" : "$context.identity.apiKey",
      "caller": "$context.identity.caller",
      "user": "$context.identity.user",
      "user-arn" : "$context.identity.userArn"
    },
    "request": {
      "querystring": {
        #foreach($param in $input.params().querystring.keySet())
        "$param": "$util.escapeJavaScript($input.params().querystring.get($param))"#if($foreach.hasNext),#end
        #end
      },
      "path": {
        #foreach($param in $input.params().path.keySet())
        "$param": "$util.escapeJavaScript($input.params().path.get($param))" #if($foreach.hasNext),#end
        #end
      },
      "header": {
        #foreach($param in $input.params().header.keySet())
        "$param": "$util.escapeJavaScript($input.params().header.get($param))" #if($foreach.hasNext),#end
        #end
      },
      "body": $input.json('$')
    }
  }
}
"""

DEFAULT_REQUESTS = {
    'application/json': APPLICATION_JSON_REQUEST,
}

AWS_INTEGRATION = {
    'credentials': "arn:aws:iam::{{ accountId }}:role/{{ apiGateway['role'] }}",
    'httpMethod': 'POST',
    'type': 'aws',
    'uri': "arn:aws:apigateway:{{ region }}:lambda:path/2015-03-31/functions/arn:aws:lambda:{{ region }}:{{ accountId }}:function:{{ Lambda['config']['name'] }}:{{ stage }}/invocations"
}
