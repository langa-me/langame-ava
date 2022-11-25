from setuptools import setup, find_packages
import os

# Langame should be a sibling directory to this project
path_to_langame = f"{os.getcwd()}/../langame-worker"

if __name__ == "__main__":
    setup(
        name="ava",
        packages=find_packages(),
        include_package_data=True,
        version="1.2.5",
        entry_points={"console_scripts": ["ava = ava:main"]},
        author="Louis Beaumont",
        author_email="louis@langa.me",
        url="https://github.com/langa-me/langame-ava",
        install_requires=[
            "fire",
            "torch",
            "transformers",
            "sentencepiece",
            "langame[all]",
        ],
        classifiers=[
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "Topic :: Scientific/Engineering :: Artificial Intelligence",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 3.6",
        ],
    )
