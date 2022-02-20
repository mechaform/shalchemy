from setuptools import setup, find_packages
# import sys, os

version = '0.9.0'

with open('README.rst') as description_file:
    long_description = description_file.read()

setup(
    name='shalchemy',
    version=version,
    description="A shell scripting toolkit for Python",
    long_description=long_description,
    classifiers=[
        # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'License :: OSI Approved :: MIT License'
    ],
    keywords='sh shell bash',
    author='Payton Yao',
    author_email='payton.yao@gmail.com',
    url='https://github.com/mechaform/shalchemy',
    license='MIT',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
    ],
    entry_points={
        'console_scripts': [
            'shalchemyprobe=shalchemy.probe:probe_main',
        ],
    },
)
