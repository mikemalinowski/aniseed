from factories.examples.zoo import Animal


class Goat(Animal):

    # -- Implement species not as a property but as a method
    @classmethod
    def species(cls):
        return 'goat'
