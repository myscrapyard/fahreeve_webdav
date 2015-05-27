#!/usr/bin/python

from setuptools import setup, find_packages

setup(
    name='webdav-audio',
    version='0.1-alpha',

    author='Eldar Fahreev',
    author_email='fahreeve@yandex.ru',

    url='https://github.com/cs-hse-projects/fahreeve_webdav',
    description='simple webdav audio server',

    packages=find_packages(),
    install_requires='mutagen',

    license='MIT License',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords='webdav audio server',
)
