# FastMessage

[![stars](https://badgen.net/github/stars/Avivsalem/FastMessage)](https://github.com/Avivsalem/FastMessage/stargazers)
[![license](https://badgen.net/github/license/Avivsalem/FastMessage/)](https://github.com/Avivsalem/FastMessage/blob/main/LICENSE)
[![last commit](https://badgen.net/github/last-commit/Avivsalem/FastMessage/main)](https://github.com/Avivsalem/FastMessage/commit/main)
[![tests](https://github.com/AvivSalem/FastMessage/actions/workflows/tests.yml/badge.svg)](https://github.com/AvivSalem/FastMessage/actions/workflows/tests.yml?query=branch%3Amain)
[![Documentation Status](https://readthedocs.org/projects/fastmessage/badge/?version=latest)](https://fastmessage.readthedocs.io/en/latest/?badge=latest)
[![pypi version](https://badgen.net/pypi/v/FastMessage)](https://pypi.org/project/fastmessage/)
[![python compatibility](https://badgen.net/pypi/python/FastMessage)](https://pypi.org/project/fastmessage/)
[![downloads](https://img.shields.io/pypi/dm/fastmessage)](https://pypi.org/project/fastmessage/)


FastMessage is a powerful Python framework that empowers you to build message processing services rapidly. Drawing inspiration from the acclaimed FastAPI, FastMessage provides a seamless and efficient platform for developing messaging applications. By leveraging the capabilities of Pydantic, FastMessage ensures robustness and reliability in your message processing workflows.

Whether you're working on real-time chat applications, data streaming services, or any other message-driven systems, FastMessage simplifies the development process and allows you to focus on crafting efficient and feature-rich applications.

## Key Features

- **Rapid Development**: FastMessage streamlines the development process, enabling you to create message processing services quickly and efficiently.

- **Inspired by FastAPI**: Drawing inspiration from the highly regarded FastAPI framework, FastMessage follows its design principles to offer a familiar development experience.

- **Pydantic Integration**: FastMessage seamlessly integrates with Pydantic, enhancing the validation and serialization of messages for improved reliability.

- **Flexible Routing**: Define message routes effortlessly and manage message flows with ease.

- **Extensive Documentation**: FastMessage comes with comprehensive documentation and examples to guide you through the framework's functionalities.

- **Scalable Architecture**: Built with scalability in mind, FastMessage supports the growth of your message processing services as your application demands increase.

## Requirements

Before you get started with FastMessage, make sure you have the following requirements in place:

- Python 3.7+
- Pip (Python package installer)

## Installation

You can install FastMessage using pip:

```bash
pip install fastmessage
```

## Example
### Create it

- Create a file main.py with:


```python
from pydantic import BaseModel

from fastmessage import FastMessage

fm = FastMessage()

@fm.map()
def do_something(x: int, y: str):
    pass  # do something with x and y

class SomeModel(BaseModel):
    x: int
    y: str

@fm.map(output_device='some_output_queue')
def do_something_else(m: SomeModel, a: int):
    return "some_value"  # do somthing with m and a

```

## Run it

Run the message processing service with:


```bash
$ messageflux main:fm --reload

INFO:     MessageFlux service loaded with default configuration. (Press CTRL+C to quit)
INFO:     Input Device Manager: FileInputDeviceManager (Base Path: /temp)
INFO:     Output Device Manager: ConsoleOutputDeviceManager
INFO:     Started reloader process [28720]
INFO:     Started server process [28722]
INFO:     Waiting for application startup.
INFO:     Application startup complete.

```

## Check it

TODO


For more detailed information and advanced usage, refer to our [documentation](https://fastmessage.readthedocs.io/en/latest).


## License

FastMessage is released under the [MIT License](LICENSE).

---

Experience the speed and simplicity of FastMessage for your message processing needs. Get started today and build efficient and robust message-driven applications in no time!`~