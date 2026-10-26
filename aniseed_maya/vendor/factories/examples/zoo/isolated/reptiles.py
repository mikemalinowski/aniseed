from factories.examples.zoo import Animal

class TreeFrog(Animal):
    species = 'Tree Frog'
    max_age = 16

    @classmethod
    def diet(cls):
        return 'insects'

    @classmethod
    def required_climate(cls):
        return 'temperate'

    @classmethod
    def sound(cls):
        return 'rebbit'
