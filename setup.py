from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(name='BRIAR',
      version='1.3.0',
      description='',
      long_description=long_description,
      author='BRIAR T&E Team',
      url='https://code.ornl.gov/briar1/briar-api',
      packages=['briar', 'briar.briar_grpc', 'briar.tests', 'briar.cli', 
                'briar.media', 'briar.sigset','briar.timing'],
      package_dir={'briar': 'lib/python/briar'}
     )
