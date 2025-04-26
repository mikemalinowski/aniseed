import os
import random
import factories


# ------------------------------------------------------------------------------
class Animal(object):
    """
    This represents the blueprint - or abstract - for all animals. Any 
    animal to be registered in the Zoo must inherit from this class
    """
    species = ''
    max_age = 0

    # --------------------------------------------------------------------------
    def __init__(self):
        self.age = 0
        self.is_alive = True

    # --------------------------------------------------------------------------
    def increment_age(self):
        self.age += 1

        if self.age > self.max_age:
            self.is_alive = False

    # --------------------------------------------------------------------------
    @classmethod
    def diet(cls):
        """
        Should return carnivore, herbivore, omnivore or unknown.
        
        :return: 
        """
        return 'unknown'

    # --------------------------------------------------------------------------
    @classmethod
    def required_climate(cls):
        """
        Returns the climate required by this animal, such as temperate,
        tropocal, artic etc.
        
        :return: 
        """
        return 'unknown'

    # --------------------------------------------------------------------------
    @classmethod
    def sound(cls):
        return '...'


# ------------------------------------------------------------------------------
class Zoo(object):

    # --------------------------------------------------------------------------
    def __init__(self, climate=None, regex_filter=None, *args, **kwargs):

        # -- Define the factory which will give us access to
        # -- the available animals
        self.factory = factories.Factory(
            abstract=Animal,
            plugin_identifier='species',
            paths=[
                os.path.join(
                    os.path.dirname(__file__),
                    'animals',
                ),
            ],
            regex_filter=regex_filter,
            *args,
            **kwargs
        )

        # -- Randomly choose a climate
        self.climate = climate or random.choice(
            [
                'tropical',
                'artic',
                'temperate',
            ]
        )

        # -- Define our list of animals
        self._animals = list()
        self._pens = dict()

    # --------------------------------------------------------------------------
    def appropriate_animals(self):
        """
        This gives a list of animals which are appropiate
        for the zoo based on the current climate.
        
        :return: List of animal species
        """
        return [
            animal.species
            for animal in self.factory.plugins()
            if animal.required_climate() == self.climate
        ]

    # --------------------------------------------------------------------------
    def add_animal(self, animal_name):

        # -- If the animal is not available we cannot add it
        if animal_name not in self.factory.identifiers():
            return False

        # -- Instance the animal
        animal = self.factory.request(animal_name)()

        # -- Check if the animal is appropriate for this zoo
        if animal.species not in self.appropriate_animals():
            return False

        # -- Track the animal in the zoo
        self._animals.append(animal)

        # -- Add the animal to the relevent pen
        if animal.species not in self._pens:
            self._pens[animal.species] = list()

        self._pens[animal.species].append(
            animal,
        )

    # --------------------------------------------------------------------------
    def pens(self):
        """
        Returns a list of available pens in the zoo
        
        :return: list(str, str, ...)
        """
        return self._pens.keys()

    # --------------------------------------------------------------------------
    def visit_pen(self, pen):
        """
        Emits a message based on the pen you have asked to visit
        
        :param pen: Name of pen to visit
        :type pen: str
        
        :return: 
        """
        if pen not in self.pens():
            print('Our zoo does not have any %ss' % pen)
            return

        if len(self._pens[pen]) == 0:
            print('Our %s pen is currently closed' % pen)
            return

        print(
            '%s %s\'s all %s as you arrive!' % (
                len(self._pens[pen]),
                self._pens[pen][0].species,
                self._pens[pen][0].sound(),
            )
        )
        return

    # --------------------------------------------------------------------------
    def next_day(self):
        """
        This increments the age of all the animals and removes 
        any which are no longer alive.
        
        :return: 
        """
        for animal in self._animals:

            animal.increment_age()

            if not animal.is_alive:
                self._animals.remove(animal)

    # --------------------------------------------------------------------------
    def animals(self):
        """
        Returns a list of all the animals in the zoo
        
        :return: 
        """
        return [
            animal.species
            for animal in self._animals
        ]
