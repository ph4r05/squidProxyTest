#!/bin/bash
srv=$1
fname=ph4squidProxyCheck-1.0
if [ "x$srv" == "x" ]; then
	echo "Usage: $0 serverName"
	exit 1
fi

echo "Using server: $srv"

# get current directory 
DIR="$( cd -P "$( dirname "$0" )" && pwd )";

#mkdirs
mkdir dist rpms
#clean
/bin/rm dist/* rpms/*
# build dist tar file
python setup.py sdist
# copy
echo "Copy dist file to server"
scp "dist/${fname}.tar.gz" "$srv:/tmp"
# execute magic
echo "Compile on server"
ssh "$srv" "cd /tmp
	sudo /bin/rm -rf /tmp/${fname}
	tar -xzvf '${fname}.tar.gz' && cd $fname && \
	python setup.py bdist_rpm
	sed -i 's/python setup.py install/python setup.py install -O1 /g' build/bdist.linux-x86_64/rpm/SPECS/ph4squidProxyCheck.spec
	rpmbuild -ba --define \"_topdir \`pwd\`/build/bdist.linux-x86_64/rpm/\"   build/bdist.linux-x86_64/rpm/SPECS/ph4squidProxyCheck.spec
	mkdir rpms
	cp \`find build/bdist.linux-x86_64/rpm/RPMS/ -type f\` rpms/
	"
# copy back
echo "Copying back home"
mkdir ./rpms/
scp "$srv:/tmp/${fname}/rpms/*" ./rpms/
echo "files: "
find ./rpms -type f

echo "Cleaning server"
ssh "$srv" "sudo /bin/rm -rf /tmp/${fname} /tmp/${fname}.tar.gz"

