import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'pyramid',
    'SQLAlchemy',
    'Jinja2',
    'transaction',
    'py-bcrypt',
    'numpy',
    'isodate',
    'pytz',
    'colander',
    'webassets',
    'cssmin',
    'pycassa',
    'Babel',
    'WTForms',
    'psycopg2',
    'yuicompressor',
    'requests',
    'lxml',
    'python-magic',
    'pyramid_tm',
    'pyramid_jinja2',
    'pyramid_debugtoolbar',
    'pyramid_webassets',
    'pyramid_mailer',
    'apscheduler',
    'zope.sqlalchemy',
    'repoze.sendmail',
    'waitress',
    'nose',
]

setup(
    name='sngconnect',
    version='0.0',
    description='sngconnect',
    long_description=README + '\n\n' +  CHANGES,
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    author='',
    author_email='',
    url='',
    keywords='web wsgi bfg pylons pyramid',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    test_suite='sngconnect',
    install_requires=requires,
    entry_points="""\
    [paste.app_factory]
    main = sngconnect:main
    [console_scripts]
    sng_initialize_database = sngconnect.scripts.initialize_database:main
    sng_initialize_cassandra = sngconnect.scripts.initialize_cassandra:main
    sng_generate_random_data = sngconnect.scripts.generate_random_data:main
    sng_create_test_data = sngconnect.scripts.create_test_data:main
    sng_create_test_users = sngconnect.scripts.create_test_users:main
    sng_user = sngconnect.scripts.user:main
    """,
)
