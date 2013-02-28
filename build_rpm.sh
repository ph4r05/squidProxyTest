#!/bin/bash
python setup.py bdist_rpm
sed -i 's/python setup.py install/python setup.py install -O1 /g' build/bdist.linux-x86_64/rpm/SPECS/ph4backuplib.spec
rpmbuild -ba --define "_topdir `pwd`/build/bdist.linux-x86_64/rpm/"   build/bdist.linux-x86_64/rpm/SPECS/ph4backuplib.spec
