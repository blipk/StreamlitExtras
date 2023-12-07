import re

package_name = "streamlit-base-extras"
version_init_file = "streamlitextras/__init__.py"

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages


with open(version_init_file, "r") as file:
    regex_version = r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]'
    version = re.search(regex_version, file.read(), re.MULTILINE).group(1)

with open("README.md", "r") as f:
    readme = f.read()

setup(
    name=package_name,
    version=version,
    author="blipk",
    author_email="blipk+@github.com",
    description="Make building with streamlit easier.",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/blipk/streamlitextras",
    packages=find_packages(),
    include_package_data=True,
    download_url=f"https://github.com/blipk/streamlitextras/archive/{version}.tar.gz",
    project_urls={
        "Changelog": "https://github.com/blipk/streamlitextras/commits/",
        "Documentation": "https://streamlitextras.readthedocs.io/en/stable/index.html",
    },
    keywords=[
        "streamlitextras",
        "streamlit",
        "router",
        "authenticator",
        "javascript",
        "cookie",
        "thread",
    ],
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
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    install_requires=[
        "streamlit >= 1.23.1",
        "streamlit-javascript",
        "loguru",
        "requests",
        "gcloud",
        "pyjwt",
        "firebase",
        "pyrebase4",
        "sseclient",
        "PyCryptodome",
        "requests_toolbelt",
        "firebase-admin",
        "google-cloud-storage",
    ],
    extras_require={
        "dev": [
            # Docs
            "Sphinx==5.2.3 ; python_version>='3.10'",
            "sphinx-autobuild==2021.3.14 ; python_version>='3.10'",
            "sphinx-rtd-theme==1.0.0 ; python_version>='3.10'",
            "docutils==0.16 ; python_version>='3.10'",
            "sphinxcontrib-apidoc ; python_version>='3.10'",
        ]
    },
    python_requires=">=3.10",
)
