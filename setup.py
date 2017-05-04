from setuptools import setup


# Became django-statsd-unleashed because django-statsd and django-statsd-mozilla are taken on Pypi. ;)
setup(
    name='django-statsd-unleashed',
    version='0.4.2',
    url='https://github.com/vikingco/django-statsd',
    license='BSD',
    description='Django interface with statsd',
    long_description=open('README.rst').read(),
    author='Andy McKay',
    author_email='andym@mozilla.com',
    maintainer='Unleashed NV',
    maintainer_email='operations@unleashed.be',
    install_requires=['statsd >= 2.1.2, != 3.2 , <= 4.0'],
    packages=['django_statsd',
              'django_statsd/patches',
              'django_statsd/clients',
              'django_statsd/loggers',
              'django_statsd/management',
              'django_statsd/management/commands'],
    entry_points={
        'nose.plugins.0.10': [
            'django_statsd = django_statsd:NoseStatsd'
        ]
    },
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Operating System :: OS Independent',
        'Environment :: Web Environment',
        'Framework :: Django',
    ],
)
