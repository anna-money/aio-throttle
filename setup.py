import pathlib
import re
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()


def read(*parts):
    return pathlib.Path(__file__).resolve().parent.joinpath(*parts).read_text().strip()


def read_version():
    regexp = re.compile(r"^__version__\W*=\W*\"([\d.abrc]+)\"")
    for line in read("aio_throttle", "__init__.py").splitlines():
        match = regexp.match(line)
        if match is not None:
            return match.group(1)
    else:
        raise RuntimeError("Cannot find version in aio_throttle/__init__.py")


setuptools.setup(
    name="aio-throttle",
    version=read_version(),
    author="Yury Pliner",
    author_email="yury.pliner@gmail.com",
    description="A simple throttling package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Pliner/aio-throttle",
    packages=["aio_throttle"],
    classifiers=[],
    python_requires='>=3.7',
    package_data={'aio_throttle': ['py.typed']},
)
