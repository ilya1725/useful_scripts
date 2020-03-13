#!/bin/bash

#
# Pull the latest and merge current branch with master
#

verbose=0
target_branch=""

usage() {
    echo "Merge with master the current or specified branch"
    echo "usage: `basename $0` [-h][-v] -b <branch-name>"
    echo ""
    exit 1
}

while getopts "hvb:" option; do
    case "${option}" in
        h)
            usage
            ;;
        v)
            verbose=1
            ;;
        b)
            target_branch=$OPTARG
            ;;
        \?)
            usage
            ;;
        :)
            echo "Error: -${OPTARG} requires an argument."
            usage
            ;;

    esac
done

# get the current branch
curr_branch=$(eval "git rev-parse --abbrev-ref HEAD")

# Get the current branch, if needed
if [ "${target_branch}" = "" ]; then
    if [ "${curr_branch}" = "master" ]; then
        echo "Already on master"
        exit 1
    fi
else
    curr_branch="${target_branch}"
fi

# do the work
eval "git checkout master && git pull --rebase"
eval "git checkout ${target_branch}"
result=$(eval "git merge master")

exit "$?"