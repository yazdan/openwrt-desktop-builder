from time import sleep
from typing import List
import os
import requests
import tqdm
import typer
from typing_extensions import Annotated




class ASU:
  def __init__(self, base_url: str):
    self.base_url = base_url

  def get_latest_versions(self):
      url = self.base_url + 'api/v1/latest'
      response = requests.get(url)
      response_json = response.json()
      return response_json  # A GET request to the API


  def get_revision(self, version, target, sub_target):
      url = self.base_url + f'api/v1/revision/{version}/{target}/{sub_target}'
      response = requests.get(url)
      response_json = response.json()
      return response_json

  def post_build(self, 
                    version: str,
                    revision: str,
                    target: str,
                    sub_target: str,
                    profile: str,
                    packages: List[str] = [],
                    defaults: str = None,
                    rootfs_size_mb: int = 256,
                    repositories: dict[str, str] = {},
                    repository_keys: List[str] = []):
      url = self.base_url + f'api/v1/build'
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

  def get_build_status(self, build_id):
      url = self.base_url + f'api/v1/build/{build_id}'
      response = requests.get(url)
      response_json = response.json()
      return response.status_code, response_json

  def download_build(self, build_id,file_name, output_dir="."):
      if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
      url = self.base_url + f'store/{build_id}/{file_name}'
      response = requests.get(url, stream=True)
      with open(os.path.join(output_dir, file_name), "wb") as handle:
          for data in tqdm.tqdm(response.iter_content(chunk_size=1024), unit="kB"):
              handle.write(data)

def wait_animation(seconds: int):
  animation = "|/-\\"
  for idx in range(seconds * 8):
    print(animation[idx % len(animation)], end="\r")
    sleep(0.125)

def main(
      version: Annotated[str, typer.Argument(envvar="OPENWRT_VERSION")] = "24.10.0",
      target: Annotated[str, typer.Argument(envvar="OPENWRT_TARGET")] = "x86",
      sub_target: Annotated[str, typer.Argument(envvar="OPENWRT_SUBTARGET")] = "64",
      profile: Annotated[str, typer.Argument(envvar="OPENWRT_PROFILE")] = "generic",
      base_url: Annotated[str, typer.Option(envvar="OPENWRT_BASE_URL")] = "https://sysupgrade.openwrt.org/"
      ):
  asu = ASU(base_url)
  latest_versions = asu.get_latest_versions()
  print(latest_versions)
  revision = asu.get_revision(version, target, sub_target)
  print(revision)
  status, build_response = asu.post_build(version, 
                                          revision['revision'],
                                          target,
                                          sub_target,
                                          profile,
                                          packages=['tailscale'],)
  print(f'build requested: {build_response['request_hash']} - response :{status}')
  code = 202
  while code == 202:
    code , build_last_response = asu.get_build_status(build_response['request_hash'])
    if code == 202:
      wait_animation(5)
    else:
      print(f'build ended with status {build_last_response['imagebuilder_status']}')

  if code != 200:
    print(f'STDOUT: {build_last_response["stdout"]}')
    print(f'STDERR: {build_last_response["stderr"]}')
    exit(1)

  for image in build_last_response['images']:
    print(f'Downlading {image['name']}')
    asu.download_build(build_response['request_hash'], image['name'], output_dir=os.path.join("downloads", f"openwrt-{version}-{target}-{sub_target}-{profile}"))
    # TODO: verify the checksum of the downloaded file

if __name__ == "__main__":
  typer.run(main)