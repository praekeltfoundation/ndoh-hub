from setuptools import setup, find_packages

setup(
    name="ndoh-hub",
    version="0.2.8",
    url='http://github.com/praekeltfoundation/ndoh-hub',
    license='BSD',
    author='Praekelt Foundation',
    author_email='dev@praekeltfoundation.org',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Django==1.11.10',
        'djangorestframework==3.7.7',
        'dj-database-url==0.3.0',
        'psycopg2==2.7.1',
        'raven==5.10.0',
        'django-filter==1.0.2',
        'whitenoise==3.3.1',
        'celery==3.1.19',
        'django-celery==3.1.17',
        'redis==2.10.5',
        'pytz==2015.7',
        'six==1.10.0',
        'django-rest-hooks==1.3.1',
        'requests==2.18.4',
        'seed-services-client==0.33.0',
        'drfdocs==0.0.11',
        'demands==3.0.0',
        'structlog==16.1.0',
        'phonenumberslite==8.9.0',
        'channels==2.0.2',
        'channels_redis==2.1.0',
        'django-simple-history==2.0',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Django',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
