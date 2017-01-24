#!/bin/bash

set -e

RELEASE=$(echo "${CIRCLE_BRANCH}"|sed 's/release_v//g')
# CPU => Circle Project Username
CPU="${CIRCLE_PROJECT_USERNAME}"
# CPR => Circle Project Reponame
CPR="${CIRCLE_PROJECT_REPONAME}"

# Generate Github release with artifacts
if [[ "${CIRCLE_BRANCH}" == release_* ]] ; then
    echo "Creating Github release: v${RELEASE}"

    mkdir release
    cp -a ./dist/* release/
    ./gh-release create "${CPU}"/"${CPR}" "${RELEASE}"
fi
