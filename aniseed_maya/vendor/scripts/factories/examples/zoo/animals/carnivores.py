from factories.examples.zoo import Animal


class Tiger(Animal):
    species = 'tiger'
    max_age = 20

    @classmethod
    def diet(cls):
        return 'steak'

    @classmethod
    def required_climate(cls):
        return 'temperate'

    @classmethod
    def sound(cls):
        return 'roar'


class Crocodile(Animal):
    species = 'crocodile'
    max_age = 70

    @classmethod
    def diet(cls):
        return 'buffalo'

    @classmethod
    def required_climate(cls):
        return 'temperate'

    @classmethod
    def sound(cls):
        return 'snap'


class PolarBear(Animal):
    species = 'polar bear'
    max_age = 25

    @classmethod
    def diet(cls):
        return 'seals'

    @classmethod
    def required_climate(cls):
        return 'artic'

    @classmethod
    def sound(cls):
        return 'grrrr'



class ArticFox(Animal):
    species = 'artic fox'
    max_age = 4

    @classmethod
    def diet(cls):
        return 'rabbits!'

    @classmethod
    def required_climate(cls):
        return 'artic'

    @classmethod
    def sound(cls):
        return 'Aaaahoooo'


class Mosquito(Animal):
    species = 'mosquito'
    max_age = 1

    @classmethod
    def diet(cls):
        return 'anything with blood'

    @classmethod
    def required_climate(cls):
        return 'tropical'

    @classmethod
    def sound(cls):
        return 'buzz'


class Boa(Animal):
    species = 'boa constrictor'
    max_age = 30

    @classmethod
    def diet(cls):
        return 'meat'

    @classmethod
    def required_climate(cls):
        return 'tropical'

    @classmethod
    def sound(cls):
        return 'Hissss'
