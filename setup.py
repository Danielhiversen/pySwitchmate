from setuptools import setup

setup(
    name = 'PySeitchmate',
    packages = ['switchmate'],
    install_requires=['cbluepy'],
    version = '0.1',
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
