def singleton(cls):
    """
    A decorator to enforce the singleton pattern on a class.

    Ensures that only one instance of the decorated class exists during
    the lifetime of the application.

    Usage:
        @singleton
        class MyClass:
            pass
    """
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance
