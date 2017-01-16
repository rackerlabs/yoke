# flake8: noqa

APPLICATION_JSON_RESPONSE_FMT = (
    '{"error": {"code": %(rc)s, "message": $input.json(\'$.errorMessage\')}}'
)
RESPONSE_CODES = [
    300,
    301,
    302,
    303,
    304,
    305,
    307,
    400,
    401,
    402,
    403,
    404,
    405,
    406,
    407,
    408,
    409,
    410,
    411,
    412,
    413,
    414,
    415,
    416,
    417,
    418,
    422,
    423,
    500,
    501,
    502,
    503,
    504,
    505,
]
DEFAULT_RESPONSES = {
    '^{rc}:.*'.format(rc=resp_code): {
        'responseTemplates': {
            'application/json': (
                APPLICATION_JSON_RESPONSE_FMT % dict(rc=resp_code)
            ),
        },
        'statusCode': '{rc}'.format(rc=resp_code),
    }
    for resp_code in RESPONSE_CODES
}
DEFAULT_RESPONSES['default'] = {
    'responseTemplates': {
        'application/json': '__passthrough__'
    },
    'statusCode': '200',
}

APPLICATION_JSON_REQUEST = """\
{
  "rawContext": {
    "apiId": "$context.apiId",
    "authorizer": {
      "principalId": "$context.authorizer.principalId",
      "claims": {
        "property": "$context.authorizer.claims.property"
      }
    },
    "httpMethod": "$context.httpMethod",
    "identity": {
      "accountId": "$context.identity.accountId",
      "apiKey": "$context.identity.apiKey",
      "caller": "$context.identity.caller",
      "cognitoAuthenticationProvider": "$context.identity.cognitoAuthenticationProvider",
      "cognitoAuthenticationType": "$context.identity.cognitoAuthenticationType",
      "cognitoIdentityId": "$context.identity.cognitoIdentityId",
      "cognitoIdentityPoolId": "$context.identity.cognitoIdentityPoolId",
      "sourceIp": "$context.identity.sourceIp",
      "user": "$context.identity.user",
      "userAgent": "$context.identity.userAgent",
      "userArn": "$context.identity.userArn"
    },
    "requestId": "$context.requestId",
    "resourceId": "$context.resourceId",
    "resourcePath": "$context.resourcePath",
    "stage": "$context.stage"
  },
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
