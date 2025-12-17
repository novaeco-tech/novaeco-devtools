from setuptools import setup, find_packages

setup(
    name="novaeco-cli", 
    version="0.1.1",
    
    url="https://github.com/novaeco-tech/ecosystem-devtools",

    package_dir={"": "src"},
    packages=find_packages(where="src"),
    
    install_requires=[
        "grpcio-tools>=1.60.0",  # Required for 'novaeco build client'
        "build>=1.0.0",          # Required for building wheels
    ],

    entry_points={
        'console_scripts': [
            'novaeco=novaeco_cli.main:main',
        ],
    },
)