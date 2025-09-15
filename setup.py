"""
USB继电器RTU控制软件安装脚本
"""

from setuptools import setup, find_packages
import pathlib

# 读取README文件
here = pathlib.Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")

# 读取版本信息
version_file = here / "src" / "__init__.py"
version = {}
with open(version_file, encoding="utf-8") as f:
    exec(f.read(), version)

setup(
    name="usb-relay-rtu",
    version=version["__version__"],
    description="跨平台USB继电器RTU控制软件",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/usb-relay-rtu",
    author="USB Relay RTU Team",
    author_email="your-email@example.com",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: System :: Hardware",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Environment :: Console",
    ],
    keywords="usb relay modbus rtu serial communication automation",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        "pyserial>=3.5",
        "click>=8.0.0",
        "rich>=12.0.0",
        "PyYAML>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=0.991",
        ],
        "build": [
            "setuptools>=65.0.0",
            "wheel>=0.37.0",
            "build>=0.8.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "usb-relay=src.cli:cli",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/your-username/usb-relay-rtu/issues",
        "Source": "https://github.com/your-username/usb-relay-rtu",
        "Documentation": "https://github.com/your-username/usb-relay-rtu/blob/main/docs/",
    },
    include_package_data=True,
    zip_safe=False,
)
