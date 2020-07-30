PYTHON_FILES:=$(shell find . -name '*.py' ! -path './pythonenv/*' ! -path './lib/*')

clean:
	rm -rf pythonenv
	find . -name '*.pyc' -delete

check:
	pep8 -r --ignore=E501 ${PYTHON_FILES}

docs:
	docco ${PYTHON_FILES}

pythonenv:
	virtualenv --python=python2.5 --no-site-packages pythonenv
	pythonenv/bin/pip install -r requirements.txt

test: pythonenv
	pythonenv/bin/nosetests tests


.PHONY: clean check docs test test