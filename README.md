# Pydref - Idref access through Python
Pydref is a Python library that provides access to idref through the idref API.

## Features
This library takes care of the following for you:

- Query idref using solr api
- Download idref xml notice
- Parse some informations from the notice
- Help identify an idref from a simple full name

## Examples
You only need to import the `Pydref` class, instantiate it, and use it to query:

```python
from pydref import Pydref
pydref = Pydref()
result = pydref.identify("eric jeangirard")
```
