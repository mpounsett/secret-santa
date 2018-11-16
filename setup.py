#!/usr/bin/env python

from distutils.util import convert_path
from setuptools import setup, find_packages

main_ns = {}
ver_path = convert_path('secret_santa/version.py')
with open(ver_path) as ver_file:
    exec(ver_file.read(), main_ns)

setup(
    name="secret_santa",
    version=main_ns['__VERSION__'],
    packages=find_packages(),

    author="Matthew Pounsett",
    author_email="matt@conundrum.com",
    description="Secret Santa - Randomly Pair Gift Givers",
    license="NONE",
    keywords="",

    long_description="""
    Secret Santa - Randomly Pair Gift Givers

    """,

    entry_points={
        'console_scripts': [
            'secret-santa = secret_santa:setup_app',
        ]
    },

    install_requires=[
        'PyYAML>=3.12',
        'Jinja2>=2.8',
    ],
)
