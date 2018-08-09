Dave Gutz's Python tools

10/1/2010

Python is meant to be installed as one giant package at the computer admin level.   Then you should be able to add packages locally using setup.py stuff, otherwise known as "setuptools" sometimes known as "easy_install"  (Windows).

For windows, you need to install the "easy_install" program to complete the top level administrative stuff.   Download and install "easy_install.exe" using other email.


Installing packages:

mac OS X:
sudo python setup.py install --install-scripts=/usr/local/bin

Windows:
pip install --index-url https://test.pypi.org/simple/ pyDAG
or
pip install pyDAG-1.4-py2-none-any.whl
#python setup.py install
in .bashrc
alias my_replace='python -m pyReplace.py'

Linux:
sudo python setup.py install
in .bashrc
alias replace='python pyReplace.py'

UNIX: 
python setup.py install --home=~ --install-scripts=~/bin 
in .bashrc
alias replace='python pyReplace.py'


Building packages:

For some reason this is hard.  I am doing this on my netbook mac OS X at present in ~/source/python.  Take for example pyDAG.   It has a top level that resides in ~/source/python.   Inside that is another pyDAG with all the stuff in it.   This is so the top level can be built and named with versions for installation while keeping the package name pyDAG when used.

cd ~/source/python/pyDAG


To build the MANIFEST file:
-  populate MANIFEST.in
- run following to update the MANIFEST file.   It looks in setup.py for "packages".   It counts on the __init.py__ files to point down into packages.


To construct a scratch build folder:
python setup.py build

To build a tar.gz distribution.  The tar.gz file will be in dist folder:
python setup.py sdist bdist bdist_wheel

Upload for trial ****use Windows CMD for this**********
twine upload --repository-url https://test.pypi.org/legacy/ dist/*
uname=davegutz, pwd=Stevie18g

Test
pip install --index-url https://test.pypi.org/simple/ pyDAG
or for local copy
pip install pyDAG-1.4.1-py2-none-any.whl


Uninstall  ******use Window CMD for this********
pip uninstall pyDAG
or
python -m pip uninstall pyDAG-1.4-py2-none-any.whl



Version number goes into setup.py

python setup.py sdist --manifest-only

