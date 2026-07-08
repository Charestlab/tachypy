# setup.py

from setuptools import setup, find_packages

requires = []
with open('requirements.txt') as reqfile:
    requires = reqfile.read().splitlines()


setup(
    name='tachypy',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=requires,
    extras_require={
        'test': ['pytest>=7.0', 'pytest-cov>=5.0', 'ruff>=0.6'],
        'text': ['Pillow>=10.0'],
        'system_text': ['freetype-py>=2.4', 'uharfbuzz>=0.39'],
        'glfw': ['glfw>=2.7'],
        'audio': [],
        'wooting': ['tachywooting>=0.2.1'],
    },
    python_requires='>=3.10',
    author='Ian Charest, Mathias Salvas-Hebert and Frederic Gosselin',
    author_email='charest.ian@gmail.com',
    description='A package for timing-focused psychophysics using GLFW and OpenGL.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/CharestLab/tachypy',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3.14',
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
