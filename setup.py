from setuptools import setup

setup(
    name = 'PySwitchmate',
    packages = ['switchmate'],
    install_requires=['bluepy'],
    version = '0.4.3',
    description = 'A library to communicate with Switchmate',
    author='Daniel Hoyer Iversen',
    url='https://github.com/Danielhiversen/pySwitchmate/',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Home Automation',
        'Topic :: Software Development :: Libraries :: Python Modules'
        ]
)
