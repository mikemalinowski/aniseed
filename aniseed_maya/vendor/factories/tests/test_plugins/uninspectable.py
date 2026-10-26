from factories.examples.zoo import Animal


class Kangaroo(Animal):
    """
    This plugin exists to test the factory code designed to handle items
    which will fail inspections
    """

    species = 'kangaroo'

    def __class__(self):
        print(123)
        raise Exception('Forced Failure')


def __getattr__(name):
    print(13123)
