from time import sleep
from typing import List
import requests
import tqdm

# The API endpoint
base_url = "http://localhost:8000/"


def asu_get_latest_versions():
    url = base_url + 'api/v1/latest'
    response = requests.get(url)
    response_json = response.json()
    return response_json
# A GET request to the API


def asu_get_revision(version, target, sub_target):
    url = base_url + f'api/v1/revision/{version}/{target}/{sub_target}'
    response = requests.get(url)
    response_json = response.json()
    return response_json

def asu_post_build(version: str,
                   revision: str,
                   target: str,
                   sub_target: str,
                   profile: str,
                   packages: List[str] = [],
                   defaults: str = None,
                   rootfs_size_mb: int = 256,
                   repositories: dict[str, str] = {},
                   repository_keys: List[str] = []):
    url = base_url + f'api/v1/build'
    payload= {
      "distro": "openwrt",
      "version": f"{version}",
      "version_code": f"{revision}",
      "target": f"{target}/{sub_target}",
      "profile": f"{profile}",
      "packages": packages,
      "packages_versions": {},
      "diff_packages": False,
      "defaults": defaults,
      "rootfs_size_mb": rootfs_size_mb,
      "repositories": repositories,
      "repository_keys": repository_keys,
      "client": "desktop-builder/0.0.0"
    }
    response = requests.post(url, json=payload)
    return response.status_code, response.json()

def asu_get_build_status(build_id):
    url = base_url + f'api/v1/build/{build_id}'
    response = requests.get(url)
    response_json = response.json()
    return response.status_code, response_json

def asu_download_build(build_id,file_name):
    url = base_url + f'store/{build_id}/{file_name}'
    response = requests.get(url, stream=True)
    with open(file_name, "wb") as handle:
        for data in tqdm.tqdm(response.iter_content(chunk_size=1024), unit="kB"):
            handle.write(data)


version = '24.10.0'
target = 'x86'
sub_target = '64'
profile = 'generic'


latest_versions = asu_get_latest_versions()
print(latest_versions)
revision = asu_get_revision(version, target, sub_target)
print(revision)
status, build_response = asu_post_build(version, 
                                        revision['revision'],
                                        target,
                                        sub_target,
                                        profile)
print(f'build requested: {build_response['request_hash']} - response :{status}')
code = 202
animation = "|/-\\"
idx = 0
while code == 202:
  code , build_last_response = asu_get_build_status(build_response['request_hash'])
  if code == 202:
    # This is a hack to show a spinner while the build is running waiting 5 seconds
    for idx in range(50):
      print(animation[idx % len(animation)], end="\r")
      sleep(0.1)
  else:
    print(f'build ended with status {build_last_response['imagebuilder_status']}')

if code != 200:
  print(f'STDOUT: {build_last_response["stdout"]}')
  print(f'STDERR: {build_last_response["stderr"]}')
  exit(1)

for image in build_last_response['images']:
  print(f'Downlading {image['name']}')
  asu_download_build(build_response['request_hash'], image['name'])
  # TODO: verify the checksum of the downloaded file

