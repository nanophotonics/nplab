import setuptools
import thorlabs_tsi_sdk.version as ver

with open("README.md", "r") as file:
    long_description = file.read()

setuptools.setup(
    name="thorlabs_tsi_sdk",
    version=ver.version_number,
    author="Thorlabs Scientific Imaging",
    description="Python wrapper of the Thorlabs TSI SDK",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=['thorlabs_tsi_sdk'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: THORLABS SOFTWARE EULA",
        "Operating System :: Windows"
    ],
    python_requires='>=2.7, <4',
    install_requires=[
        'numpy',
        'enum34;python_version<"3.4"',
        'typing;python_version<"3.5"',

    ]
)
