import re
import time

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

with open("streamlitextras/__init__.py", "r") as file:
    regex_version = r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]'
    version = re.search(regex_version, file.read(), re.MULTILINE).group(1)

from make_readme import make_readme
make_readme()
time.sleep(1)
with open("README.md", "r") as f:
    readme = f.read()

setup(
    name="stextras",
    version=version,
    author="BLIPK",
    author_email="BLIPK@BLIPK.com",
    description="Python logging made (stupidly) simple",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/blipk/streamlitextras",
    packages=find_packages(),
    include_package_data=True,

    download_url="https://github.com/blipk/streamlitextras/archive/{}.tar.gz".format(version),
    project_urls={
        "Changelog": "https://github.com/blipk/streamlitextras/commits/",
        "Documentation": "https://streamlitextras.readthedocs.io/en/stable/index.html",
    },
    keywords=["streamlitextras", "streamlit", "router", "authenticator", "javascript", "cookie", "thread"],
    license="MIT license",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "Topic :: Software Development :: Libraries",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    install_requires=[
        "streamlit >= 1.13.0",
    ],
    extras_require={
        "dev": [
            #TODO
            # Docs.
        ]
    },
    python_requires=">=3.9",
)
