from setuptools import setup, find_packages

if __name__ == "__main__":
    setup(
        name="ava",
        packages=find_packages(),
        include_package_data=True,
        version="1.0.0",
        entry_points={"console_scripts": ["ava = ava:main"]},
        author="Louis Beaumont",
        author_email="louis.beaumont@langa.me",
        url="https://github.com/langa-me/langame-ava",
        install_requires=[
            "grpcio==1.40.0",
            "grpcio-tools==1.40.0",
            "grpc-gateway-protoc-gen-openapiv2",
            "gcloud",
            "google-api-python-client",
            "protobuf",
            "grpcio-reflection",
            "grpcio-status",
            "openai",
            "transformers",
            "firebase_admin",
            "sentencepiece",
            "torch",
            "fire"
        ],
        classifiers=[
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "Topic :: Scientific/Engineering :: Artificial Intelligence",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 3.6",
        ],
    )
