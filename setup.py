from setuptools import setup, find_packages

setup(
    name="NFL_machinelearn",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "selenium>=4.10.0",
        "beautifulsoup4>=4.12.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "scikit-learn>=1.3.0",
        "joblib>=1.3.0",
        "html5lib>=1.1",
        "pathlib>=1.0.1",
        "typing>=3.7.4",
        "python-dateutil>=2.8.2",
        "requests>=2.31.0",
        "matplotlib>=3.8.0",
        "seaborn>=0.13.0",
    ],
    python_requires=">=3.8",
    author="Jordan Levy",
    description="NFL Player Statistics Machine Learning Project",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
) 