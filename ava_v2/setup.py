from setuptools import setup, find_packages
from pathlib import Path

if __name__ == "__main__":
    with Path(Path(__file__).parent, "README.md").open(encoding="utf-8") as file:
        long_description = file.read()

    setup(
        name="ava",
        packages=find_packages(),
        include_package_data=True,
        version="1.0.0",
        license="MIT",
        description="",
        long_description=long_description,
        long_description_content_type="text/markdown",
        entry_points={"console_scripts": ["ava = ava:main"]},
        author="Louis Beaumont",
        author_email="louis.beaumont@langa.me",
        url="https://github.com/langa-me/langame-ava",
        data_files=[(".", ["README.md"])],
        install_requires=[
            "grpcio",
            "grpcio-tools"
        ],
        classifiers=[
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "Topic :: Scientific/Engineering :: Artificial Intelligence",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 3.6",
        ],
    )