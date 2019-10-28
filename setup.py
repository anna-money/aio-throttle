import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="aio-throttle",
    version="1.0.1",
    author="Yury Pliner",
    author_email="yury.pliner@gmail.com",
    description="A simple throttling package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Pliner/aio-throttle",
    packages=["aio_throttle"],
    classifiers=[],
    python_requires='>=3.7',
)
