import os
from setuptools import setup, find_packages

setup(
    name='panda',
    version='1.4.6',
    packages=find_packages(),  # Automatically finds all packages like panda_agent, utils
    install_requires=[
        "requests",
        "openai",
        "pandas",
#       "func_timeout",    # timeout control for exec()
        "pdfminer.six",    # for panda.utils.file_utils.convert_pdf_to_text()
        "litellm",	   # expand panda to access Claude
        "matplotlib"	   # 
    ],
    author='Peter Clark',
    description='An AI tool for autonomous scientific research',
    python_requires='>=3.7',
)
