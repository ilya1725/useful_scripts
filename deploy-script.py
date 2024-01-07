#!/usr/bin/env python3
#
# @copyright 2021 Archer Aviation, Inc.
#
import argparse
import base64
import logging
import re
import requests
import sys
import http.client as http_client
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import reduce
from itertools import chain
from pprint import pformat as pformat

TIMEOUT = 3000/1000 # 3s connect timeout

class BitBucketApi:
    BASE_URL = 'https://api.bitbucket.org'

    def __init__(self, username='', password='', **kwargs) -> None:
        """Inits API class using bitbucket app username/password"""
        self.authorization = f"Basic {base64.b64encode(f'{username}:{password}'.encode('utf8')).decode('utf8')}"

    def get(self, endpoint, params={}) -> dict:
        """Returns JSON from API call to specified endpoint"""
        logging.info(f'BitBucket API GET request: {endpoint.replace(self.BASE_URL, "")}')
        logging.debug(pformat(api_json := requests.get(
            f'{self.BASE_URL}{endpoint.replace(self.BASE_URL, "")}',
            headers={
                'Accept': 'application/json',
                'Authorization': self.authorization,
            },
            timeout=TIMEOUT,
            params=params
        ).json()))
        return api_json

    def post(self, endpoint, json={}) -> dict:
        """Returns JSON from API call to specified endpoint"""
        logging.info(f'BitBucket API POST request: {endpoint.replace(self.BASE_URL, "")}')
        logging.debug(pformat(api_json := requests.post(
            f'{self.BASE_URL}{endpoint.replace(self.BASE_URL, "")}',
            headers={
                'Accept': 'application/json',
                'Authorization': self.authorization,
            },
            timeout=TIMEOUT,
            json=json
        ).json()))
        return api_json

    def delete(self, endpoint, json={}) -> str:
        """Returns JSON from API call to specified endpoint"""
        logging.info(f'BitBucket API DELETE request: {endpoint.replace(self.BASE_URL, "")}')
        logging.debug(pformat(api_str := requests.delete(
            f'{self.BASE_URL}{endpoint.replace(self.BASE_URL, "")}',
            headers={
                'Accept': 'application/json',
                'Authorization': self.authorization,
            },
            timeout=TIMEOUT,
            json=json
        ).content))
        return api_str

class TeamCityApi:
    BASE_URL = 'https://teamcity.int.archer.com'

    def __init__(self, token='', **kwargs) -> None:
        """Inits API class using teamcity bearer token"""
        self.authorization = f'Bearer {token}'

    def get(self, endpoint, params={}) -> dict:
        """Returns JSON from API call to specified endpoint"""
        logging.info(f'TeamCity API GET request: {endpoint.replace(self.BASE_URL, "")}')
        logging.debug(pformat(api_json := requests.get(
            f'{self.BASE_URL}{endpoint.replace(self.BASE_URL, "")}',
            headers={
                'Accept': 'application/json',
                'Authorization': self.authorization,
            },
            timeout=TIMEOUT,
            params=params
        ).json()))
        return api_json

    def post(self, endpoint, json={}) -> dict:
        """Returns JSON from API call to specified endpoint"""
        logging.info(f'TeamCity API POST request: {endpoint.replace(self.BASE_URL, "")}')
        logging.debug(pformat(api_json := requests.post(
            f'{self.BASE_URL}{endpoint.replace(self.BASE_URL, "")}',
            headers={
                'Accept': 'application/json',
                'Authorization': self.authorization,
            },
            timeout=TIMEOUT,
            json=json
        ).json()))
        return api_json

    def put(self, endpoint, json={}) -> dict:
        """Returns JSON from API call to specified endpoint"""
        logging.info(f'TeamCity API PUT request: {endpoint.replace(self.BASE_URL, "")}')
        logging.debug(pformat(api_json := requests.put(
            f'{self.BASE_URL}{endpoint.replace(self.BASE_URL, "")}',
            headers={
                'Accept': 'application/json',
                'Authorization': self.authorization,
            },
            timeout=TIMEOUT,
            json=json
        ).json()))
        return api_json

def main() -> int:
    # set up argument parsing
    parser = argparse.ArgumentParser(description='Generate changelog between two build numbers')
    parser.add_argument('-q', '--quiet', action='count', default=0, help='Decrease logging verbosity')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase logging verbosity')
    parser.add_argument('--build', required=True, help='Build number to be released')
    parser.add_argument('--release', required=True, help='Version number for this release; consult Software Plans doc')
    parser.add_argument('--bb-username', required=True, help='BitBucket app username', dest='username')
    parser.add_argument('--bb-password', required=True, help='BitBucket app password', dest='password')
    parser.add_argument('--tc-token', required=True, help='TeamCity bearer token', dest='token')
    parser.add_argument('--delete', default=False, action='store_true')
    args = parser.parse_args()

    # translate verbosity flag count to logging level
    loglevel = logging.INFO - ((10 * args.verbose) if args.verbose > 0 else 0) + ((10 * args.quiet) if args.quiet > 0 else 0)

    logging.basicConfig(
        level=loglevel,
        format='%(levelname)s: %(message)s',
    )
    logging.debug(pformat(vars(args)))

    if loglevel <= logging.DEBUG:
        http_client.HTTPConnection.debuglevel = 1
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True
        logging.debug('Enabled HTTP debug output')

    # not getting fucked by GIL using threads instead of processes since we'll be network I/O bound
    logging.debug('Setting up thread pool with default 5x logical cores')
    executor = ThreadPoolExecutor()

    logging.info('Initializing API classes')
    tc = TeamCityApi(**vars(args))
    bb = BitBucketApi(**vars(args))

    logging.info(f'Getting build {args.build} metadata') # produces dict of { name: value } from properties
    logging.debug(pformat(bundle_props := dict(reduce(
        lambda x, y: x.update({y.get('name'): y.get('value')}) or x,
        tc.get(f'/app/rest/builds/buildType:flight_sw__m000_eec_control_sw_controlwin,number:{args.build}/resulting-properties').get('property')
    ))))

    logging.info(f'Tagging build {args.build} as release')
    logging.debug(pformat(bundle_tags := dict(tc.post(f'/app/rest/builds/buildType:flight_sw__m000_eec_control_sw_controlwin,number:{args.build}/tags', json={'count': 1, 'tag': [{'name': 'release'}]}))))

    logging.info('Determining unique build types in build') # produces set of { buildType }
    logging.debug(pformat(build_types := set(map(
        lambda d: d.split('.')[1],
        filter(
            lambda p: re.search(r'^dep\..*\.system\.build\.(vcs\.)?number$', p),
            bundle_props.keys()
        )
    ))))

    # request body for build pinning
    pin_timestamp = datetime.now(timezone.utc).strftime("%%Y%%m%%dT%%H%%M%%S%%z")

    # for each artifact dependency, pin the build with the release version as the comment
    logging.info(f'Pinning build {args.build} and all artifact dependency builds')
    logging.debug(pformat(list(executor.map(
        lambda p: tc.put(p, json={
            'comment': {
                'text': f'Release {args.release}',
                'timestamp': pin_timestamp,
            },
            'status': not args.delete,
        }),
        map(
            lambda b: f"{b.get('href')}/pinInfo",
            tc.get('/app/rest/builds', params={
                'locator': f'artifactDependency:(to:(buildType:flight_sw__m000_eec_control_sw_controlwin,number:{args.build}),includeInitial:true)'
            }).get('build')
        )
    ))))

    logging.info(f'Getting latest revision for each snapshot dependency')
    logging.debug(pformat(bundle_revs := filter(
        lambda r: r.get('vcs-root-instance').get('vcs-root-id') != 'avionics_firmware',
        chain(*executor.map(
            lambda p: tc.get(p).get('revisions').get('revision'),
            [
                b.get('href')
                for b in tc.get('/app/rest/builds', params={
                    'locator': f'snapshotDependency:(to:(buildType:flight_sw__m000_eec_control_sw_controlwin,number:{args.build}),includeInitial:true)'
                }).get('build')
            ]
        ))))
    )

    logging.info('Getting hash to tag as release for each VCS')
    logging.debug(pformat(vcs_hashes := reduce(
        lambda x, y: x.update(y) or x,
        executor.map(
            lambda r: {
                re.sub(r'.*bitbucket\.org:(.*)/(.*)\.git', r'/2.0/repositories/\g<1>/\g<2>/refs/tags', {
                    p.get('name'): p.get('value')
                    for p in tc.get(r.get('vcs-root-instance').get('href')).get('properties').get('property')
                }.get('url')):
                r.get('version')
            },
            bundle_revs
        )
    )))

    logging.info(f'Tagging release as rel/{args.release}')
    if args.delete:
        logging.info(pformat(tag_response := list(executor.map(
            lambda v: bb.delete(f'{v}/rel/{args.release}'),
            vcs_hashes.keys()
        ))))
    else:
        logging.info(pformat(tag_response := list(executor.map(
            lambda v: bb.post(v, json={
                'name': f'rel/{args.release}',
                'target': {
                    'hash': vcs_hashes.get(v)
                },
            }),
            vcs_hashes.keys()
        ))))

if __name__ == '__main__':
    sys.exit(main())