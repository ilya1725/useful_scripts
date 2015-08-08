#!/bin/bash
#
# Curl ftp wrapper
#
# ftp to/from system as user ftp
 
verbose=0
 
usage() {
    echo "Transfer files using ftp"
    echo "usage: `basename $0` [-v] get <system> <remote file> <local file>"
    echo "       `basename $0` [-v] put <system> <local file> <remote file>"
    exit 1
}
 
if [ "$1" == "-h" -o "$1" == "-?" ]; then
    usage
    exit 1
fi
 
if [ "$1" == "-v" ]; then
    verbose=1
fi
 
num_arg=`expr $# - $verbose`
if [ $num_arg != 4 ]; then
    usage
fi
 
args=("$@")
cmd=${args[`expr $verbose + 0`]}
target=${args[`expr $verbose + 1`]}
file1=${args[`expr $verbose + 2`]}
file2=${args[`expr $verbose + 3`]}
 
if [ "$cmd" != "get" ] &amp;&amp; [ "$cmd" != "put" ]; then
    echo "Invalid command '$cmd'"
    usage
fi
if [ "$cmd" == "put" ] &amp;&amp; [ ! -e $file1 ]; then
    echo "Source file $file1 doesn't exist"
    exit 1
fi
 
# set the verbose variable
curl_verbose="-s"
if [ $verbose == 1 ]; then
    curl_verbose="-v"
fi
 
if [ $cmd == "get" ]; then
    if [ $verbose == 1 ]; then
        echo "Copying file from $target:$file1 to $file2"
    fi
 
    curl $curl_verbose ftp://$target/$file1 --user ftp:ftp -o $file2
 
else
    if [ $cmd == "put" ]; then
        if [ $verbose == 1 ]; then
            echo "Copying file from $file1 to ftp://$target/$file2"
        fi
 
        curl $curl_verbose -T $file1 ftp://$target/$file2 --user ftp:ftp
 
    else
        echo "Invalid command"
        if [ $verbose == 1 ]; then
            usage
        fi
        exit 1
    fi
fi