# FastMessage

[![stars](https://badgen.net/github/stars/Avivsalem/FastMessage)](https://github.com/Avivsalem/FastMessage/stargazers)
[![license](https://badgen.net/github/license/Avivsalem/FastMessage/)](https://github.com/Avivsalem/FastMessage/blob/main/LICENSE)
[![last commit](https://badgen.net/github/last-commit/Avivsalem/FastMessage/main)](https://github.com/Avivsalem/FastMessage/commit/main)
[![tests](https://github.com/AvivSalem/FastMessage/actions/workflows/tests.yml/badge.svg)](https://github.com/AvivSalem/FastMessage/actions/workflows/tests.yml?query=branch%3Amain)
[![Documentation Status](https://readthedocs.org/projects/fastmessage/badge/?version=latest)](https://fastmessage.readthedocs.io/en/latest/?badge=latest)
[![pypi version](https://badgen.net/pypi/v/fastmessage)](https://pypi.org/project/fastmessage/)
[![python compatibility](https://badgen.net/pypi/python/FastMessage)](https://pypi.org/project/fastmessage/)
[![downloads](https://img.shields.io/pypi/dm/fastmessage)](https://pypi.org/project/fastmessage/)

FastMessage is an easy framework to create PipelineHandlers for [MessageFlux](https://messageflux.readthedocs.io)

You can find the full documentation [here](https://fastmessage.readthedocs.io/)

## Requirements

Python 3.7+

## Installation

```console
$ pip install fastmessage
```

## Examples

```python
from fastmessage import FastMessage, OtherMethodOutput
from messageflux.iodevices.rabbitmq import RabbitMQInputDeviceManager, RabbitMQOutputDeviceManager

fm = FastMessage()


@fm.map()
def hello(name: str, birthYear: int):
    age = 2023 - birthYear
    print(f'Hello {name}. your age is {age}')
    return OtherMethodOutput(next_year, age=age)  # this sends its output to 'next_year' method


@fm.map()
def next_year(age: int):
    print(f'next year you will be {age + 1}')


if __name__ == "__main__":
    input_device_manager = RabbitMQInputDeviceManager(hosts='my.rabbit.host',
                                                      user='username',
                                                      password='password')

    output_device_manager = RabbitMQOutputDeviceManager(hosts='my.rabbit.host',
                                                        user='username',
                                                        password='password')

    service = fm.create_service(input_device_manager=input_device_manager,
                                output_device_manager=output_device_manager)
    service.start()  # this runs the PipelineService and blocks
```

This example shows two methods: ```hello``` and ```next_year```, each listening on its own queue
(with the same name)

the ```__main__``` creates an input and output device managers (```RabbitMQ``` in this case), and starts the service
with these devices.

every message that is sent to the ```hello``` queue should have the following format:

```json
{
  "name": "john",
  "birthYear": 1999
}
```

in that case the process will print (in 2023...):

```
Hello john. your age is 24
next year you will be 25
```


