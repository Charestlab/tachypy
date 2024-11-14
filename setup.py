# setup.py

from setuptools import setup, find_packages

requires = []
with open('requirements.txt') as reqfile:
    requires = reqfile.read().splitlines()


setup(
    name='tachypy',
    version='0.1.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=requires,
    python_requires='>=3.6',
    author='Ian Charest and Frederic Gosselin',
    author_email='charest.ian@gmail.com',
    description='A package for OpenGL drawing using Pygame.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/CharestLab/tachypy',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: OS Independent',
    ],
)