from setuptools import setup, find_packages

setup(
    name="nova-ecosystem-cli", 
    version="0.1.2",
    
    url="https://github.com/nova-ecosystem/ecosystem-devtools",

    package_dir={"": "src"},
    packages=find_packages(where="src"),
    entry_points={
        'console_scripts': [
            'nova=nova_cli.main:main',
        ],
    },
)