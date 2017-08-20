#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
.. currentmodule:: setup.py
.. moduleauthor:: Pat Daburu <pat@daburu.net>

This file is used to create the package uploaded to PyPI.
"""

import cnxman
from setuptools import setup, find_packages  # Always prefer setuptools over distutils
from codecs import open  # To use a consistent encoding
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'README'), encoding='utf-8') as f:
    long_description = f.read()

setup(
  name='cnxman',
  description='A pretty simple framework for managin connections to things.',
  long_description=long_description,
  packages=['cnxman'],
  version=cnxman.__version__,
  install_requires=[
      'automat',
      'PyDispatcher',
      'pyserial'
  ],
  python_requires=">=3.6.1",
  license='MIT',
  author='Pat Daburu',
  author_email='pat@daburu.net',
  url='http://cnxman.readthedocs.io/en/latest/index.html',  # Use the URL to the github repo.
  download_url='https://github.com/pblair/cnxman/archive/{version}.tar.gz'.format(version=cnxman.__version__),
  keywords=['plugin'],  # arbitrary keywords
  # See https://PyPI.python.org/PyPI?%3Aaction=list_classifiers
  classifiers=[
    # How mature is this project? Common values are
    #   3 - Alpha
    #   4 - Beta
    #   5 - Production/Stable
    'Development Status :: 3 - Alpha',

    # Indicate who your project is intended for
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Libraries',

    # Pick your license as you wish (should match "license" above)
    'License :: OSI Approved :: MIT License',

    # Specify the Python versions you support here. In particular, ensure
    # that you indicate whether you support Python 2, Python 3 or both.
    'Programming Language :: Python :: 3.6',
  ],
)
