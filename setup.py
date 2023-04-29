from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in custom_doctypes/__init__.py
from custom_doctypes import __version__ as version

setup(
	name="custom_doctypes",
	version=version,
	description="Custom Doctypes",
	author="gabriel@lans.gt",
	author_email="gabriel@lans.gt",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
