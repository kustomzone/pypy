from pypy.interpreter.baseobjspace import W_Root


class Ellipsis(W_Root):
    def __init__(self, space):
        self.space = space

    def descr__repr__(self, space):
        return space.wrap('Ellipsis')


class NotImplemented(W_Root):
    def __init__(self, space):
        self.space = space

    def descr__repr__(self, space):
        return space.wrap('NotImplemented')
