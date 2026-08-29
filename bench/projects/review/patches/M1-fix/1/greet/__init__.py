def greet(name: str) -> str:
    if not isinstance(name, str):
        raise TypeError('name must be a str')
    return f'Hello, {name}!'
