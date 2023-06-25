#!/usr/bin/env python3
import re
import sys
import requests

package_name = "streamlit-base-extras"
version_init_file = "streamlitextras/__init__.py"

def get_local_package_version():
    with open(version_init_file, "r") as file:
        regex_version = r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]'
        version = re.search(regex_version, file.read(), re.MULTILINE).group(1)
    return version

def get_latest_deployed_version(package_name = package_name):
    url = f"https://pypi.org/simple/{package_name}/"
    response = requests.get(url)
    latest_version = response.content.decode("utf-8").split("</a><br />")[-3].split("-")[-1].replace(".tar.gz", "")
    return latest_version

deployed_package_version = get_latest_deployed_version()

def bump_version(version):
    parts = version.split(".")
    bump = int(parts[-1]) + 1
    new_version = ".".join(parts[:-1]) + f".{bump}"
    print(f"Package version changed from {version} to {new_version} in {version_init_file}")
    with open(version_init_file, "r+") as file:
        file_content = file.read()
        new_file_content = file_content.replace(f"__version__ = \"{version}\"", f"__version__ = \"{new_version}\"")
        file.seek(0)
        file.write(new_file_content)
        file.truncate()

version = get_local_package_version()

if deployed_package_version == version:
    print(f"Version number already deployed ({version})")
    response = input("Auto bump version in __init__.py? (y/other) ")
    if response == "y":
        bump_version(version)
    else:
        print("Cancelling deployment. Please reconcile version.")
        sys.exit(1)
