GAE_VERSION=1.4.1
PYTHON_FILES:=$(shell find . -name '*.py' ! -path './pythonenv/*' ! -path './lib/*')

clean:
	rm -rf pythonenv
	find . -name '*.pyc' -delete

check:
	pep8 -r --ignore=E501 ${PYTHON_FILES}

docs:
	docco ${PYTHON_FILES}

test: pythonenv
	pythonenv/bin/nosetests -v --with-gae --without-sandbox tests/*.py

pythonenv:
	virtualenv --python=python2.5 --no-site-packages pythonenv
	pythonenv/bin/pip install -r requirements.txt

	# gaetk kann nicht per requirements.txt installiert werden, da sie keine setup.py hat
	git clone ssh://gerrit.hudora.biz:29418/appengine-toolkit pythonenv/lib/python2.5/site-packages/gaetk
	echo './gaetk' >> pythonenv/lib/python2.5/site-packages/makefile.pth

	# appengine kann nicht per requirements.txt installiert werden, da sie kein repo hat
	curl -O http://googleappengine.googlecode.com/files/google_appengine_$(GAE_VERSION).zip
	unzip google_appengine_*.zip -d pythonenv/lib/python2.5/site-packages/
	rm google_appengine_*.zip
	echo './google_appengine' >> pythonenv/lib/python2.5/site-packages/makefile.pth

.PHONY: check test clean dependencies docs