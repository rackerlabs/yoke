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

DOCKER_BUILD_SCRIPT = """\
#!/bin/bash

set -e -x

OPENSSL_VERSION="1.0.2l"
LIBFFI_VERSION="3.2.1"
LIBXML_VERSION="2.9.2"
LIBXSLT_VERSION="1.1.29"

# Some commonly used dependencies (cryptography, lxml, etc.) require newer
# versions of certain libraries that aren't available for CentOS 5, which is
# the base distro of the Docker image used for building Python packages. Let's
# install these from source, when requested.
yum install -y libtool texinfo

# Symlink all the existing autoconf macros into the installed tool's directory
for MACRO in `ls /usr/share/aclocal`; do
    ln -s /usr/share/aclocal/${MACRO} /usr/local/share/aclocal/${MACRO}
done

# Build source libxml2 and libxslt RPMs
if [[ "${BUILD_LIBXML}" == "1" ]]; then
    yum install -y rpm-build python-devel libgcrypt-devel xz-devel zlib-devel
    curl -O http://xmlsoft.org/sources/libxml2-${LIBXML_VERSION}-1.fc19.src.rpm
    rpm -ivh libxml2-${LIBXML_VERSION}-1.fc19.src.rpm --nomd5
    rpmbuild -ba /usr/src/redhat/SPECS/libxml2.spec
    rpm -ivh --force /usr/src/redhat/RPMS/x86_64/libxml2-${LIBXML_VERSION}-1.x86_64.rpm
    rpm -ivh --force /usr/src/redhat/RPMS/x86_64/libxml2-devel-${LIBXML_VERSION}-1.x86_64.rpm
    rpm -ivh --force /usr/src/redhat/RPMS/x86_64/libxml2-python-${LIBXML_VERSION}-1.x86_64.rpm
    curl -O http://xmlsoft.org/sources/libxslt-${LIBXSLT_VERSION}-1.fc23.src.rpm
    rpm -ivh libxslt-${LIBXSLT_VERSION}-1.fc23.src.rpm --nomd5
    rpmbuild -ba /usr/src/redhat/SPECS/libxslt.spec
    rpm -ivh --force /usr/src/redhat/RPMS/x86_64/libxslt-${LIBXSLT_VERSION}-1.x86_64.rpm
    rpm -ivh --force /usr/src/redhat/RPMS/x86_64/libxslt-devel-${LIBXSLT_VERSION}-1.x86_64.rpm
fi

# Build OpenSSL from source
if [[ "${BUILD_OPENSSL}" == "1" ]]; then
    curl -O https://www.openssl.org/source/openssl-${OPENSSL_VERSION}.tar.gz
    tar xf openssl-${OPENSSL_VERSION}.tar.gz
    cd openssl-${OPENSSL_VERSION}
    ./config no-shared no-ssl2 -fPIC --prefix=/openssl
    make && make install
    cd ..
    export CFLAGS="${CFLAGS} -I/openssl/include"
    export LDFLAGS="${LDFLAGS} -L/openssl/lib"
fi

# Build libffi from source
if [[ "${BUILD_LIBFFI}" == "1" ]]; then
    curl -L -o libffi-${LIBFFI_VERSION}.tar.gz https://github.com/libffi/libffi/archive/v${LIBFFI_VERSION}.tar.gz
    tar xf libffi-${LIBFFI_VERSION}.tar.gz
    cd libffi-${LIBFFI_VERSION}
    ./autogen.sh
    ./configure --prefix=/libffi
    make && make install
    cd ..
    export CFLAGS="${CFLAGS} -I/libffi/lib/libffi-${LIBFFI_VERSION}/include"
    export LDFLAGS="${LDFLAGS} -L/libffi/lib64"
    export LD_LIBRARY_PATH="/libffi/lib64"
fi

# Install extra build dependencies, if specified
if [ -n "${EXTRA_PACKAGES}" ]; then
    yum install -y ${EXTRA_PACKAGES}
fi

PYBIN="/opt/python/${PY_VERSION}/bin"

${PYBIN}/pip wheel --no-binary :all: -w /wheelhouse -r /src/requirements.txt

# Make sure we're using the latest version of auditwheel
/opt/python/cp36-cp36m/bin/pip install -U auditwheel
# We only want to repair platform wheels that were compiled - not universal
# wheels.
find /wheelhouse -type f \\
    -name "*.whl" \\
    -not -name "*none-any.whl" \\
    -exec auditwheel repair {} -w /wheelhouse/ \; \\
    -exec rm {} \;

# Provide SHA1-sum file that we can check against to see if dependencies should
# be rebuilt.
sha1sum /src/requirements.txt | cut -d " " -f 1 > /wheelhouse/sha1sum
"""

DOCKER_INSTALL_SCRIPT = """\
#!/bin/bash

set -e -x -u

# First make sure that the target directory is clean, this way we can avoid
# the contamination of Lambda packages when building locally.
rm -rf /src/${INSTALL_DIR}

PYBIN="/opt/python/${PY_VERSION}/bin"

${PYBIN}/pip install -t /src/${INSTALL_DIR} \\
    --no-compile \\
    --no-index \\
    --find-links /wheelhouse \\
    -r /lambda/requirements.txt
"""
