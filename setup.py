from setuptools import find_packages, setup

setup(
    name="ndoh-hub",
    version="0.10.7",
    url="http://github.com/praekeltfoundation/ndoh-hub",
    license="BSD",
    author="Praekelt Foundation",
    author_email="dev@praekeltfoundation.org",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Django==4.1.7",
        "djangorestframework==3.14.0",
        "coreapi==2.3.3",
        "Markdown==3.1.1",
        "dj-database-url==1.2.0",
        "django-environ==0.10.0",
        "psycopg2-binary==2.8.6",
        "raven==6.9.0",
        "django-filter==2.4.0",
        "celery==5.2.3",
        "six==1.11.0",
        "requests==2.28.2",
        "demands==3.0.0",
        "structlog==18.2.0",
        "phonenumberslite==8.9.15",
        "django-simple-history==3.3.0",
        "openpyxl==2.5.9",
        "iso-639==0.4.5",
        "django-prometheus==2.2.0",
        "rapidpro-python==2.6.1",
        "pycountry==19.8.18",
        "attrs",
        "iso6709==0.1.5",
        "redis==4.5.4",
        "django-redis==5.2.0",
        "celery_batches==0.7",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Django",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.9.9",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
