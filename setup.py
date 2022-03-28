import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="smoot",
    version="0.0.2",
    author="Nathalie Bartoli, Rémi Lafage",
    description="Surrogate based multi-objective optimization tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="BSD-3",
    url="https://github.com/OneraHub/smoot",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
    packages=["smoot"],
    python_requires=">=3.6",
    install_requires=["smt", "pymoo"],
)
