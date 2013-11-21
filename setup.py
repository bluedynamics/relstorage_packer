from setuptools import setup, find_packages
import os

version = '1.0'
shortdesc = \
'Packs a History Free PostgreSQL RelStorage for ZODB.'
longdesc = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()
longdesc += open(os.path.join(os.path.dirname(__file__), 'HISTORY.rst')).read()
longdesc += open(os.path.join(os.path.dirname(__file__), 'LICENSE.rst')).read()
tests_require = ['interlude']

setup(
    name='relstorage_packer',
    version=version,
    description=shortdesc,
    long_description=longdesc,
    classifiers=[
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development',
        'License :: OSI Approved :: BSD License',
    ],
    keywords='postgresql zodb pack zope',
    author='BlueDynamics Alliance',
    author_email='dev@bluedynamics.com',
    url="http://pypi.python.org/pypi/relstorage_packer",
    license='Simplified BSD',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=True,
    install_requires=[
        'setuptools',
        'RelStorage'
    ],
    tests_require=tests_require,
    extras_require=dict(
        test=tests_require,
    ),
    entry_points={
      'console_scripts': [
          'relstorage_pack = relstorage_packer.refcount:run',
      ],
    },
)
