from setuptools import setup, find_packages

setup(
    name="fnos-exporter",
    version="0.1.0",
    packages=find_packages(),
    py_modules=['main'],
    install_requires=[
        "prometheus-client>=0.20.0",
        "fnos>=0.7.0",
    ],
    entry_points={
        'console_scripts': [
            'fnos-exporter=main:main',
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="Prometheus Exporter for fnOS",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Timandes/fnos-prometheus-exporter",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
)