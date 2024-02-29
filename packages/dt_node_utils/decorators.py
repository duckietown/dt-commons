def sidecar(func):
    # decorate the function
    def decorated(*args, **kwargs):
        return func(*args, **kwargs)

    # mark the function as sidecar
    setattr(decorated, '__sidecar__', True)

    return decorated
