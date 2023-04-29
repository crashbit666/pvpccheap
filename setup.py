from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="pvpccheap",
    version="0.2",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'pvpccheap = pvpccheap:main',
        ],
    },
)
