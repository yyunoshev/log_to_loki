from setuptools import setup, find_packages
import os

# Читаем содержимое README.md для длинного описания
def read_long_description():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Читаем requirements из файла
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="log-to-loki",
    version="0.1.0",
    author="Yunoshev Yaroslav",
    author_email="yunoshev.dev@gmail.com",
    description="Python library for sending logs to Grafana Loki with batching support",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/yyunoshev/log-to-loki",
    project_urls={
        "Documentation": "https://github.com/yyunoshev/log-to-loki#readme",
        "Source Code": "https://github.com/yyunoshev/log-to-loki",
    },
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: System :: Logging",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov",
            "black",
            "flake8",
            "twine",
            "build",
        ],
    },
    keywords="logging loki grafana observability monitoring",
    include_package_data=True,
)
