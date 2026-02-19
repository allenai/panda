import os
from setuptools import setup, find_packages

setup(
    name='panda',
    version='1.5.0',
    packages=find_packages(),  # Automatically finds all packages like panda_agent, utils
    install_requires=[
        "requests",
        "openai",
        "pandas",
        "func_timeout",    # timeout control for exec()
#        "pdfminer.six",    # for panda.utils.file_utils.convert_pdf_to_text()
        "litellm",	   # expand panda to access Claude
        "matplotlib",      # handle mention of plotting in panda_agent/panda_agent.py
        "unidecode",	   # for utils.ask_llm.call_llm to replace non-standard characters
        "mcp"
#        "flask",           # web interface for superpanda_interactive
#        "flask-socketio",  # real-time updates for superpanda_interactive web UI
#        "python-socketio"  # socketio support
    ],
    author='Peter Clark',
    description='An AI tool for autonomous scientific research',
    python_requires='>=3.7',
    entry_points={
        'console_scripts': [
            'panda = panda.run_panda:main'  # adjust if you rename the file
        ]
    }
)
