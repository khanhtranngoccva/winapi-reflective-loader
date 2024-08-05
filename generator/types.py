from clang import cindex


class Loader:
    def __init__(self, name, mangled_name, implementation, header, extra_includes=None):
        self.name = name
        self.mangled_name = mangled_name
        self.implementation = implementation
        self.header = header
        self.extra_includes = extra_includes or []


class FunctionMatch:
    def __init__(self, node: cindex.Cursor, header: str):
        self.node = node
        self.header = header
        self.loader = None

    def set_loader(self, loader: Loader):
        self.loader = loader
