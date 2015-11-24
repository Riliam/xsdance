from setuptools import setup

setup(name='xsdance',
      version='0.0.1',
      description='XSD forms HTML rendering and validation',
      url='https://github.com/Riliam/xsdance',
      author='Alexey Milogradov',
      author_email='alexey.milogradov@gmail.com',
      license='MIT',
      install_requires=[
          'lxml',
      ],
      packages=['xsdance'],
      zip_safe=False)
