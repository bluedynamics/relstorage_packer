from setuptools import setup, find_packages
import os

version = '1.2'
shortdesc = \
'Converts CSV files to IMS VDEX XML (Vocabulary Definition Exchange Format)'
longdesc = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()
longdesc += open(os.path.join(os.path.dirname(__file__), 'HISTORY.rst')).read()
longdesc += open(os.path.join(os.path.dirname(__file__), 'LICENSE.rst')).read()
tests_require = ['interlude',]

setup(name='vdexcsv',
      version=version,
      description=shortdesc,
      long_description=longdesc,
      classifiers=[
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Topic :: Software Development',
            'License :: OSI Approved :: BSD License',
      ],
      keywords='vdex csv converter xml ims vocabulary',
      author='BlueDynamics Alliance',
      author_email='dev@bluedynamics.com',
      url="http://github.com/bluedynamics/vdexcsv",
      license='Simplified BSD',
      packages=find_packages('src'),
      package_dir = {'': 'src'},
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          'setuptools',
          'lxml',
      ],
      tests_require=tests_require,
      test_suite="vdexcsv.tests.test_suite",
      extras_require = dict(
          test=tests_require,
      ),
      entry_points={
        'console_scripts': ['csv2vdex = vdexcsv.script:run'],
      },      
)
