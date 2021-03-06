unit:
	python3 -m unittest discover -s mpf/tests

unit-verbose:
	python3 -m unittest discover -v -s mpf/tests 2>&1

coverage:
	coverage3 run -m unittest discover -s mpf/tests
	coverage3 html
