all: test

install-dev:
	@pip install -r requirements-dev.txt


black: install-dev
	@black aio_throttle


mypy: flake8
	@mypy --strict aio_throttle


flake8: black
	@flake8 --max-line-length 120 --ignore C901,C812,E203 --extend-ignore W503 aio_throttle tests


test: mypy
	@python -m pytest tests/


.PHONY: all mypy flake8 black install-dev test
