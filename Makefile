all: deps lint test

deps:
	@python3 -m pip install --upgrade pip && pip3 install -r requirements-dev.txt

black:
	@black --line-length 120 aio_throttle tests

mypy:
	@mypy --strict --ignore-missing-imports aio_throttle

flake8:
	@flake8 --max-line-length 120 --ignore C901,C812,E203 --extend-ignore W503 aio_throttle tests

lint: black flake8 mypy

test:
	@python3 -m pytest -vv --rootdir tests .
