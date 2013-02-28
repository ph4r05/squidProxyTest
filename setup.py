#!/usr/bin/env python

from distutils.core import setup

setup(name='ph4squidProxyCheck',
      version='1.0',
      description='Ph4r05 SQUID proxy check daemon',
      author='Dusan (ph4r05) Klinec',
      author_email='dusan.klinec@gmail.com',
      packages=['squid_proxy_check'],
      license='GPLv3',
      #data_files=[('scripts', ['build_rpm.sh'])],
     )
