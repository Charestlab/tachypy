# setup.py

from setuptools import setup, find_packages

requires = []
with open('requirements.txt') as reqfile:
    requires = reqfile.read().splitlines()


setup(
    name='tachypy',
    version='0.1.17',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=requires,
    extras_require={
        'wooting': ['tachywooting>=0.2.0'],
    },
    python_requires='>=3.6',
    author='Ian Charest, Mathias Salvas-Hebert and Frederic Gosselin',
    author_email='charest.ian@gmail.com',
    description='A package for timing-focused psychophysics using GLFW and OpenGL.',
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
    entry_points={
        'console_scripts': [
            'tachypy-clock-demo=tachypy.examples.clock_timer_demo:main',
            'tachypy-wooting-fixation-demo=tachypy.wooting.demos.visual_fixation_demo:main',
            'tachypy-wooting-mini-bw=tachypy.wooting.demos.mini_bw_experiment:main',
        ],
    },
)
