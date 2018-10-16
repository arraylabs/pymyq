from setuptools import setup


with open('LICENSE') as f:
    license = f.read()

setup(
    name='pymyq',
    version='0.0.16',
    description='Python package for controlling MyQ-Enabled Garage Door',
    author='Chris Campbell',
    author_email='chris@arraylabs.com',
    url='https://github.com/arraylabs/pymyq',
    license=license,
    packages=['pymyq'],
    package_dir={'pymyq': 'pymyq'}
)
