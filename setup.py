from setuptools import setup, find_packages

def parse_requirements(filename):
    """ load requirements from a pip requirements file """
    lineiter = (line.strip() for line in open(filename))
    return [line for line in lineiter if line and not line.startswith("#")]

# # TO-DO
# with open('README.rst') as readme_file:
#     readme = readme_file.read()

# with open('HISTORY.rst') as history_file:
#     history = history_file.read()

requirements = parse_requirements("requirements.txt")

setup_requirements = ['pytest-runner', ]

test_requirements = parse_requirements("requirements_dev.txt")

setup(
    author="Caio de Souza Barbosa Costa",
    author_email='csbc326@gmail.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Internet :: XMPP',
    ],
    description="Plugin for SPADE 3 MAS platform to implement games.",
    install_requires=requirements,
    license="MIT License v3",
    # long_description=readme + '\n\n' + history, # TO-DO
    include_package_data=True,
    keywords='spade_game',
    name='spade_game',
    packages=find_packages(include=['spade_game']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/C4i0kun/spade_game.git',
    version='0.0.1',
    zip_safe=False,
)