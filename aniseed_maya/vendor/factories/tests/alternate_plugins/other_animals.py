from factories.examples.zoo import Animal


class Snake(Animal):

    # -- Implement species not as a property but as a method
    @classmethod
    def species(cls):
        return 'snake'
