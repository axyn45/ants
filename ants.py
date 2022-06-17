"""CS 61A presents Ants Vs. SomeBees."""

from dis import dis
import imp
from operator import ne
import random
from select import select
from tkinter.tix import Select
from turtle import distance
from typing import List
from unicodedata import name

from numpy import block
from ucb import main, interact, trace
from collections import OrderedDict
from typing import List

################
# Core Classes #
################

# 蚂蚁与SomeBees的游戏逻辑

class Place:
    """A Place holds insects and has an exit to another Place."""
    is_hive: bool = False

    def __init__(self, name:str, exit=None):
        """Create a Place with the given NAME and EXIT.

        name -- A string; the name of this Place.
        exit -- The Place reached by exiting this Place (may be None).
        """
        self.name: str = name
        self.exit = exit
        self.bees:List = []        # A list of Bees
        self.ant:Ant = None       # An Ant
        self.entrance:Place = None  # A Place
        # Phase 1: Add an entrance to the exit
        # BEGIN Problem 2
        "*** YOUR CODE HERE ***"
        if self.exit:
            exit.entrance = self
        # END Problem 2

    def add_insect(self, insect):
        """
        Asks the insect to add itself to the current place. This method exists so
            it can be enhanced in subclasses.
        """
        insect.add_to(self)

    def remove_insect(self, insect):
        """
        Asks the insect to remove itself from the current place. This method exists so
            it can be enhanced in subclasses.
        """
        insect.remove_from(self)

    def __str__(self):
        return self.name

class GameState:
    """An ant collective that manages global game state and simulates time.

    Attributes:
    time -- elapsed time
    food -- the colony's available food total
    places -- A list of all places in the colony (including a Hive)
    bee_entrances -- A list of places that bees can enter
    """

    def __init__(self, strategy, beehive, ant_types, create_places, dimensions, food=2):
        """Create an GameState for simulating a game.

        Arguments:
        strategy -- a function to deploy ants to places  将蚂蚁部署到地方的功能
        beehive -- a Hive full of bees 蜂巢
        ant_types -- a list of ant classes 蚂蚁类型
        create_places -- a function that creates the set of places 创建地点
        dimensions -- a pair containing the dimensions of the game layout 游戏画面尺寸
        """
        
        self.time = 0
        self.food = food
        self.strategy = strategy
        self.beehive = beehive
        self.ant_types = OrderedDict((a.name, a) for a in ant_types)
        self.dimensions = dimensions
        self.active_bees = []
        self.configure(beehive, create_places)

    def configure(self, beehive, create_places):
        """Configure the places in the colony."""
        self.base = AntHomeBase('Ant Home Base')
        self.places: OrderedDict = OrderedDict()
        self.bee_entrances = []

        def register_place(place, is_bee_entrance):
            self.places[place.name] = place
            if is_bee_entrance:
                place.entrance = beehive
                self.bee_entrances.append(place)
        register_place(self.beehive, False)
        create_places(self.base, register_place, self.dimensions[0], self.dimensions[1])

    def simulate(self):
        """Simulate an attack on the ant colony (i.e., play the game)."""
        num_bees = len(self.bees)
        try:
            while True:
                self.beehive.strategy(self)         # Bees invade
                self.strategy(self)                 # Ants deploy
                for ant in self.ants:               # Ants take actions
                    if ant.health > 0:
                        ant.action(self)
                for bee in self.active_bees[:]:     # Bees take actions
                    if bee.health > 0:
                        bee.action(self)
                    if bee.health <= 0:
                        num_bees -= 1
                        self.active_bees.remove(bee)
                if num_bees == 0:
                    raise AntsWinException()
                self.time += 1
        except AntsWinException:
            print('All bees are vanquished. You win!')
            return True
        except AntsLoseException:
            print('The ant queen has perished. Please try again.')
            return False

    def deploy_ant(self, place_name, ant_type_name):
        """Place an ant if enough food is available.

        This method is called by the current strategy to deploy ants.
        """
        ant_type = self.ant_types[ant_type_name]
        ant = ant_type.construct(self)
        if ant:
            self.places[place_name].add_insect(ant)
            self.food -= ant.food_cost
            return ant

    def remove_ant(self, place_name):
        """Remove an Ant from the game."""
        place = self.places[place_name]
        if place.ant is not None:
            place.remove_insect(place.ant)

    @property
    def ants(self):
        return [p.ant for p in self.places.values() if p.ant is not None]

    @property
    def bees(self):
        return [b for p in self.places.values() for b in p.bees]

    @property
    def insects(self):
        return self.ants + self.bees

    def __str__(self):
        status = ' (Food: {0}, Time: {1})'.format(self.food, self.time)
        return str([str(i) for i in self.ants + self.bees]) + status



class Insect:
    """An Insect, the base class of Ant and Bee, has health and a Place."""

    damage = 0
    # ADD CLASS ATTRIBUTES HERE
    is_waterproof: bool = False

    def __init__(self, health, place:Place=None):
        """Create an Insect with a health amount and a starting PLACE."""
        self.health = health
        self.place:Place = place  # set by Place.add_insect and Place.remove_insect

    def reduce_health(self, amount: int):
        """Reduce health by AMOUNT, and remove the insect from its place if it
        has no health remaining.

        >>> test_insect = Insect(5)
        >>> test_insect.reduce_health(2)
        >>> test_insect.health
        3
        """
        self.health -= amount
        if self.health <= 0:
            self.death_callback()
            self.place.remove_insect(self)

    def action(self, gamestate):
        """The action performed each turn.

        gamestate -- The GameState, used to access game state information.
        """

    def death_callback(self):
        # overriden by the gui
        pass

    def add_to(self, place):
        """Add this Insect to the given Place

        By default just sets the place attribute, but this should be overriden in the subclasses
            to manipulate the relevant attributes of Place
        """
        self.place = place

    def remove_from(self, place):
        self.place = None

    def __repr__(self):
        cname = type(self).__name__
        return '{0}({1}, {2})'.format(cname, self.health, self.place)

class Bee(Insect):
    """A Bee moves from place to place, following exits and stinging ants."""

    name = 'Bee'
    damage = 1
    # OVERRIDE CLASS ATTRIBUTES HERE
    is_waterproof: bool = True
    slow_timer: int = 0 # 为0不减速 不为0减速
    scary_timer: int = 0 # 为0不恐惧  大于0恐惧
    scary_had: bool = False # 恐惧史

    def sting(self, ant):
        """Attack an ANT, reducing its health by 1."""
        ant.reduce_health(self.damage)

    def move_to(self, place):
        """Move from the Bee's current Place to a new PLACE."""
        self.place.remove_insect(self)
        place.add_insect(self)

    def blocked(self):
        """Return True if this Bee cannot advance to the next Place."""
        # Special handling for NinjaAnt
        # BEGIN Problem Optional 1
        if self.place.ant: # 有蚂蚁
            if self.place.ant.blocks_path: # 蚂蚁能阻挡
                return True
        return False
        # return self.place.ant is not None
        # END Problem Optional 1

    def action(self, gamestate: GameState):
        """A Bee's action stings the Ant that blocks its exit if it is blocked,
        or moves to the exit of its current place otherwise.

        gamestate -- The GameState, used to access game state information.
        """
        destination = self.place.exit

        # Extra credit: Special handling for bee direction
        if self.slow_timer > 0 and self.scary_timer > 0:
            if gamestate.time % 2 == 0: # 后退
                destination = self.place.entrance
                if self.blocked():
                    self.sting(self.place.ant)
                if self.health > 0 and destination is not None:
                    self.move_to(destination)
                self.slow_timer -= 1
                self.scary_timer -= 1
            else:
                if self.blocked():
                    self.sting(self.place.ant)
                self.slow_timer -= 1
        elif self.slow_timer > 0: # 减速
            if gamestate.time % 2 == 1: # 奇数不动
                if self.blocked():
                    self.sting(self.place.ant)
            else:  # 偶数前进
                if self.blocked():
                    self.sting(self.place.ant)
                elif self.health > 0 and destination is not None:
                    self.move_to(destination)
            self.slow_timer -= 1
        elif self.scary_timer > 0: # 后退
            destination = self.place.entrance
            if self.blocked():
                self.sting(self.place.ant)
            if self.health > 0 and destination is not None:
                self.move_to(destination)
            self.scary_timer -= 1
        else: # 正常
            if self.blocked():
                self.sting(self.place.ant)
            elif self.health > 0 and destination is not None:
                self.move_to(destination)
                
        # if self.slow_timer > 0:
        #     self.slow_timer -= 1
        # if self.scary_timer > 0:
        #     self.scary_timer -= 1

    def add_to(self, place):
        place.bees.append(self)
        Insect.add_to(self, place)

    def remove_from(self, place):
        place.bees.remove(self)
        Insect.remove_from(self, place)

    def slow(self, length: int):
        """Slow the bee for a further LENGTH turns."""
        # BEGIN Problem EC
        "*** YOUR CODE HERE ***"
        self.slow_timer += length
        # END Problem EC

    def scare(self, length: int):
        """
        If this Bee has not been scared before, cause it to attempt to
        go backwards LENGTH times.
        """
        # BEGIN Problem EC
        "*** YOUR CODE HERE ***"
        if not self.scary_had:
            self.scary_timer = length
            self.scary_had = True
        # END Problem EC

class Ant(Insect):
    """An Ant occupies a place and does work for the colony."""

    implemented = False  # Only implemented Ant classes should be instantiated
    food_cost = 0
    is_container = False
    # ADD CLASS ATTRIBUTES HERE
    buffed: bool = False
    ant_contained = None
    blocks_path: bool = True

    def __init__(self, health=1):
        """Create an Insect with a HEALTH quantity."""
        super().__init__(health)

    @classmethod
    def construct(cls, gamestate):
        """Create an Ant for a given GameState, or return None if not possible."""
        if cls.food_cost > gamestate.food:
            print('Not enough food remains to place ' + cls.__name__)
            return
        return cls()

    def can_contain(self, other):
        return False

    def store_ant(self, other):
        assert False, "{0} cannot contain an ant".format(self)

    def remove_ant(self, other):
        assert False, "{0} cannot contain an ant".format(self)

    def add_to(self, place: Place):
        if place.ant is None:
            place.ant = self
        else:
            # BEGIN Problem 8
            if self.is_container and self.can_contain(place.ant):
                self.store_ant(place.ant)
                place.ant = self
            elif place.ant.is_container and place.ant.can_contain(self):
                place.ant.store_ant(self)
            else:
                assert place.ant is None, 'Two ants in {0}'.format(place)
            # END Problem 8
        Insect.add_to(self, place)

    def remove_from(self, place):
        if place.ant is self:
            place.ant = None
        elif place.ant is None:
            assert False, '{0} is not in {1}'.format(self, place)
        else:
            place.ant.remove_ant(self)
        Insect.remove_from(self, place)

    def double(self):
        """Double this ants's damage, if it has not already been doubled."""
        # BEGIN Problem 12
        "*** YOUR CODE HERE ***"
        self.damage *= 2
        # END Problem 12




class HarvesterAnt(Ant):
    """HarvesterAnt produces 1 additional food per turn for the colony."""

    name = 'Harvester'
    implemented = True
    # OVERRIDE CLASS ATTRIBUTES HERE
    food_cost: int = 2

    def action(self, gamestate: GameState):
        """Produce 1 additional food for the colony.

        gamestate -- The GameState, used to access game state information.
        """
        # BEGIN Problem 1
        "*** YOUR CODE HERE ***"
        gamestate.food += 1
        # END Problem 1


class ThrowerAnt(Ant):
    """ThrowerAnt throws a leaf each turn at the nearest Bee in its range."""

    name:str = 'Thrower'
    implemented = True
    damage:int = 1
    # ADD/OVERRIDE CLASS ATTRIBUTES HERE
    food_cost:int = 3
    min_range, max_range = 0, float('inf')

    def nearest_bee(self):
        """Return the nearest Bee in a Place that is not the HIVE, connected to
        the ThrowerAnt's Place by following entrances.

        This method returns None if there is no such Bee (or none in range).
        """
        # BEGIN Problem 3 and 4
        next_place:Place = self.place
        distance = 0
        while not next_place.is_hive:
            if self.min_range <= distance <= self.max_range and next_place.bees:
                return random_bee(next_place.bees)  # REPLACE THIS LINE
            next_place = next_place.entrance
            distance += 1
        return None
        # END Problem 3 and 4

    def throw_at(self, target):
        """Throw a leaf at the TARGET Bee, reducing its health."""
        if target is not None:
            target.reduce_health(self.damage)

    def action(self, gamestate):
        """Throw a leaf at the nearest Bee in range."""
        self.throw_at(self.nearest_bee())


def random_bee(bees) -> Bee:
    """Return a random bee from a list of bees, or return None if bees is empty."""
    assert isinstance(bees, list), "random_bee's argument should be a list but was a %s" % type(bees).__name__
    if bees:
        return random.choice(bees)

##############
# Extensions #
##############


class ShortThrower(ThrowerAnt):
    """A ThrowerAnt that only throws leaves at Bees at most 3 places away."""

    name = 'Short'
    food_cost = 2
    # OVERRIDE CLASS ATTRIBUTES HERE
    food_cost: int = 2
    min_range, max_range = 0, 3
    # BEGIN Problem 4
    implemented = True   # Change to True to view in the GUI
    # END Problem 4


class LongThrower(ThrowerAnt):
    """A ThrowerAnt that only throws leaves at Bees at least 5 places away."""

    name = 'Long'
    food_cost = 2
    # OVERRIDE CLASS ATTRIBUTES HERE
    min_range, max_range = 5, float('inf')
    # BEGIN Problem 4
    implemented = True   # Change to True to view in the GUI
    # END Problem 4


class FireAnt(Ant):
    """FireAnt cooks any Bee in its Place when it expires."""

    name = 'Fire'
    damage = 3
    food_cost = 5
    # OVERRIDE CLASS ATTRIBUTES HERE
    # BEGIN Problem 5
    implemented = True   # Change to True to view in the GUI
    # END Problem 5

    def __init__(self, health=3):
        """Create an Ant with a HEALTH quantity."""
        super().__init__(health)

    def reduce_health(self, amount: int):
        """Reduce health by AMOUNT, and remove the FireAnt from its place if it
        has no health remaining.

        Make sure to reduce the health of each bee in the current place, and apply
        the additional damage if the fire ant dies.
        """
        # BEGIN Problem 5
        "*** YOUR CODE HERE ***"
        self.health -= amount 
        for bee in self.place.bees[:]:
                bee.reduce_health(amount)
        if self.health <= 0: # 自爆
            for bee in self.place.bees[:]:
                bee.reduce_health(self.damage)
        super().reduce_health(0)
        # END Problem 5

# BEGIN Problem 6
# The WallAnt class
class WallAnt(Ant):
    name = 'Wall'
    implemented = True
    food_cost = 4
    
    def __init__(self, health=4):
        super().__init__(health)
# END Problem 6

# BEGIN Problem 7
# The HungryAnt Class
class HungryAnt(Ant):
    name = 'Hungry'
    implemented = True
    food_cost = 4
    time_to_chew = 3
    
    def __init__(self, health=1):
        super().__init__(health)
        self.chew_timer: int = 0
    
    def action(self, gamestate):
        if self.chew_timer == 0 and self.place.bees[:]:
            random_bee_random = random_bee(self.place.bees)
            random_bee_random.health = 0
            random_bee_random.reduce_health(0)
            self.chew_timer = self.time_to_chew
        else:
            if self.chew_timer != 0:
                self.chew_timer -= 1
# END Problem 7


class ContainerAnt(Ant):
    """
    ContainerAnt can share a space with other ants by containing them.
    """
    is_container = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ant_contained: Ant = None

    def can_contain(self, other: Ant):
        # BEGIN Problem 8
        "*** YOUR CODE HERE ***"
        if self.ant_contained is None and not other.is_container:
            return True
        return False
        # END Problem 8

    def store_ant(self, ant: Ant):
        # BEGIN Problem 8
        "*** YOUR CODE HERE ***"
        self.ant_contained = ant
        # END Problem 8
        
    def add_to(self, place: Place):
        # if place.
        return super().add_to(place)

    def remove_ant(self, ant: Ant):
        if self.ant_contained is not ant:
            assert False, "{} does not contain {}".format(self, ant)
        self.ant_contained = None

    def remove_from(self, place):
        # Special handling for container ants (this is optional)
        if place.ant is self:
            # Container was removed. Contained ant should remain in the game
            place.ant = place.ant.ant_contained
            Insect.remove_from(self, place)
        else:
            # default to normal behavior
            Ant.remove_from(self, place)

    def action(self, gamestate: GameState):
        # BEGIN Problem 8
        "*** YOUR CODE HERE ***"
        if self.ant_contained:
            self.ant_contained.action(gamestate)
        # END Problem 8


class BodyguardAnt(ContainerAnt):
    """BodyguardAnt provides protection to other Ants."""

    name = 'Bodyguard'
    food_cost = 4
    # OVERRIDE CLASS ATTRIBUTES HERE
    def __init__(self, health = 2):
        super().__init__(health)
    # BEGIN Problem 8
    implemented = True   # Change to True to view in the GUI
    # END Problem 8

# BEGIN Problem 9
# The TankAnt class
class TankAnt(ContainerAnt):
    name = 'Tank'
    food_cost = 6
    damage = 1
    implemented = True
    
    def __init__(self, health = 2):
        super().__init__(health)
        
    def action(self, gamestate: GameState):
        if self.ant_contained:
            self.ant_contained.action(gamestate)
        for bee in self.place.bees[:]:
            bee.reduce_health(self.damage)
# END Problem 9


class Water(Place):
    """Water is a place that can only hold waterproof insects."""

    def add_insect(self, insect: Insect):
        """Add an Insect to this place. If the insect is not waterproof, reduce
        its health to 0."""
        # BEGIN Problem 10
        "*** YOUR CODE HERE ***"
        super().add_insect(insect)
        if not insect.is_waterproof:
            insect.reduce_health(insect.health)
        # END Problem 10

# BEGIN Problem 11
# The ScubaThrower class
class ScubaThrower(ThrowerAnt):
    name: str = 'Scuba'
    food_cost: int = 6
    implemented = True
    is_waterproof: bool = True
# END Problem 11

# BEGIN Problem 12


class QueenAnt(ScubaThrower):  # You should change this line
# END Problem 12
    """The Queen of the colony. The game is over if a bee enters her place."""

    name = 'Queen'
    food_cost = 7
    # OVERRIDE CLASS ATTRIBUTES HERE
    is_truequeen = True
    instance = None
    # BEGIN Problem 12
    implemented = True   # Change to True to view in the GUI
    # END Problem 12
    
    def __init__(self, health=1):
        super().__init__(health)

    @classmethod
    def construct(cls, gamestate):
        """
        Returns a new instance of the Ant class if it is possible to construct, or
        returns None otherwise. Remember to call the construct() method of the superclass!
        """
        # BEGIN Problem 12
        "*** YOUR CODE HERE ***"
        if cls.food_cost > gamestate.food:
            print('Not enough food remains to place ' + cls.__name__)
            return
        elif hasattr(cls, '_instance'):
            return
        cls._instance = super(QueenAnt, cls).construct(gamestate)
        return cls._instance
        # return cls()
        # END Problem 12

    def action(self, gamestate):
        """A queen ant throws a leaf, but also doubles the damage of ants
        in her tunnel.
        """
        # BEGIN Problem 12
        "*** YOUR CODE HERE ***"
        self.throw_at(self.nearest_bee())
        behind: Place = self.place.exit
        while behind:
            if behind.ant:
                if not behind.ant.buffed:
                    behind.ant.double()
                    behind.ant.buffed = True
                if behind.ant.is_container and behind.ant.ant_contained:
                    if not behind.ant.ant_contained.buffed:
                        behind.ant.ant_contained.double()
                        behind.ant.ant_contained.buffed = True
            behind = behind.exit
        # END Problem 12

    def reduce_health(self, amount):
        """Reduce health by AMOUNT, and if the QueenAnt has no health
        remaining, signal the end of the game.
        """
        # BEGIN Problem 12
        "*** YOUR CODE HERE ***"
        self.health -= amount
        if self.health <= 0:
            ants_lose()
        # END Problem 12
        
    def remove_from(self, place):
        return 


class AntRemover(Ant):
    """Allows the player to remove ants from the board in the GUI."""

    name = 'Remover'
    implemented = False

    def __init__(self):
        super().__init__(0)





############
# Optional #
############

class NinjaAnt(Ant):
    """NinjaAnt does not block the path and damages all bees in its place.
    This class is optional.
    """

    name = 'Ninja'
    damage = 1
    food_cost = 5
    # OVERRIDE CLASS ATTRIBUTES HERE
    blocks_path: bool = False
    # BEGIN Problem Optional 1
    implemented = True   # Change to True to view in the GUI
    # END Problem Optional 1

    def action(self, gamestate):
        # BEGIN Problem Optional 1
        "*** YOUR CODE HERE ***"
        for bee in self.place.bees[:]:
            bee.reduce_health(self.damage)
        # END Problem Optional 1

############
# Statuses #
############


class SlowThrower(ThrowerAnt):
    """ThrowerAnt that causes Slow on Bees."""

    name = 'Slow'
    food_cost = 4
    # BEGIN Problem EC
    implemented = True   # Change to True to view in the GUI
    # END Problem EC
    
    def __init__(self, health=1):
        super().__init__(health)

    def throw_at(self, target: Bee):
        if target:
            target.slow(3)


class ScaryThrower(ThrowerAnt):
    """ThrowerAnt that intimidates Bees, making them back away instead of advancing."""

    name = 'Scary'
    food_cost = 6
    # BEGIN Problem EC
    implemented = True   # Change to True to view in the GUI
    # END Problem EC

    def __init__(self, health=1):
        super().__init__(health)

    def throw_at(self, target: Bee):
        # BEGIN Problem EC
        "*** YOUR CODE HERE ***"
        if target:
            target.scare(2)
        # END Problem EC


class LaserAnt(ThrowerAnt):
    # This class is optional. Only one test is provided for this class.

    name = 'Laser'
    food_cost = 10
    # OVERRIDE CLASS ATTRIBUTES HERE
    damage = 2
    # BEGIN Problem Optional 2
    implemented = True   # Change to True to view in the GUI
    # END Problem Optional 2

    def __init__(self, health=1):
        super().__init__(health)
        self.insects_shot = 0

    def insects_in_front(self):
        # BEGIN Problem Optional 2
        insects_and_distances: dict[Select, int] = {};
        next_place:Place = self.place
        distance = 0
        while next_place and not next_place.is_hive:
            if next_place.ant and next_place.ant != self: # ant
                insects_and_distances[next_place.ant] = distance
                if next_place.ant.ant_contained:
                    insects_and_distances[next_place.ant_contained] = distance
                    
            if next_place.bees: # bee
                for bee in next_place.bees[:]:
                    insects_and_distances[bee] = distance
                    
            distance += 1
            next_place = next_place.entrance
        
        return insects_and_distances
        # END Problem Optional 2

    def calculate_damage(self, distance: int):
        # BEGIN Problem Optional 2
        damage_calculate = self.damage - 0.0625 * self.insects_shot - 0.25 * distance
        return damage_calculate if damage_calculate > 0 else 0
        # return 0.5
        # END Problem Optional 2

    def action(self, gamestate):
        insects_and_distances = self.insects_in_front()
        for insect, distance in insects_and_distances.items():
            damage = self.calculate_damage(distance)
            insect.reduce_health(damage)
            if damage:
                self.insects_shot += 1


##################
# Bees Extension #
##################

class Wasp(Bee):
    """Class of Bee that has higher damage."""
    name = 'Wasp'
    damage = 2


class Hornet(Bee):
    """Class of bee that is capable of taking two actions per turn, although
    its overall damage output is lower. Immune to statuses.
    """
    name = 'Hornet'
    damage = 0.25

    def action(self, gamestate):
        for i in range(2):
            if self.health > 0:
                super().action(gamestate)

    def __setattr__(self, name, value):
        if name != 'action':
            object.__setattr__(self, name, value)


class NinjaBee(Bee):
    """A Bee that cannot be blocked. Is capable of moving past all defenses to
    assassinate the Queen.
    """
    name = 'NinjaBee'

    def blocked(self):
        return False


class Boss(Wasp, Hornet):
    """The leader of the bees. Combines the high damage of the Wasp along with
    status immunity of Hornets. Damage to the boss is capped up to 8
    damage by a single attack.
    """
    name = 'Boss'
    damage_cap = 8
    action = Wasp.action

    def reduce_health(self, amount):
        super().reduce_health(self.damage_modifier(amount))

    def damage_modifier(self, amount):
        return amount * self.damage_cap / (self.damage_cap + amount)


class Hive(Place):
    """The Place from which the Bees launch their assault.

    assault_plan -- An AssaultPlan; when & where bees enter the colony.
    """
    # 这是蜜蜂起源的地方。蜜蜂离开蜂巢进入蚁群。
    
    is_hive = True

    def __init__(self, assault_plan):
        self.name = 'Hive'
        self.assault_plan = assault_plan
        self.bees = []
        for bee in assault_plan.all_bees:
            self.add_insect(bee)
        # The following attributes are always None for a Hive
        self.entrance = None
        self.ant = None
        self.exit = None

    def strategy(self, gamestate):
        exits = [p for p in gamestate.places.values() if p.entrance is self]
        for bee in self.assault_plan.get(gamestate.time, []):
            bee.move_to(random.choice(exits))
            gamestate.active_bees.append(bee)


class AntHomeBase(Place):
    """AntHomeBase at the end of the tunnel, where the queen resides."""

    def add_insect(self, insect):
        """Add an Insect to this Place.

        Can't actually add Ants to a AntHomeBase. However, if a Bee attempts to
        enter the AntHomeBase, a AntsLoseException is raised, signaling the end
        of a game.
        """
        assert isinstance(insect, Bee), 'Cannot add {0} to AntHomeBase'
        raise AntsLoseException()


def ants_win():
    """Signal that Ants win."""
    raise AntsWinException()


def ants_lose():
    """Signal that Ants lose."""
    raise AntsLoseException()


def ant_types():
    """Return a list of all implemented Ant classes."""
    all_ant_types = []
    new_types = [Ant]
    while new_types:
        new_types = [t for c in new_types for t in c.__subclasses__()]
        all_ant_types.extend(new_types)
    return [t for t in all_ant_types if t.implemented]


class GameOverException(Exception):
    """Base game over Exception."""
    pass


class AntsWinException(GameOverException):
    """Exception to signal that the ants win."""
    pass


class AntsLoseException(GameOverException):
    """Exception to signal that the ants lose."""
    pass


def interactive_strategy(gamestate):
    """A strategy that starts an interactive session and lets the user make
    changes to the gamestate.

    For example, one might deploy a ThrowerAnt to the first tunnel by invoking
    gamestate.deploy_ant('tunnel_0_0', 'Thrower')
    """
    print('gamestate: ' + str(gamestate))
    msg = '<Control>-D (<Control>-Z <Enter> on Windows) completes a turn.\n'
    interact(msg)

###########
# Layouts #
###########


def wet_layout(queen, register_place, tunnels=3, length=9, moat_frequency=3):
    """Register a mix of wet and and dry places."""
    for tunnel in range(tunnels):
        exit = queen
        for step in range(length):
            if moat_frequency != 0 and (step + 1) % moat_frequency == 0:
                exit = Water('water_{0}_{1}'.format(tunnel, step), exit)
            else:
                exit = Place('tunnel_{0}_{1}'.format(tunnel, step), exit)
            register_place(exit, step == length - 1)


def dry_layout(queen, register_place, tunnels=3, length=9):
    """Register dry tunnels."""
    wet_layout(queen, register_place, tunnels, length, 0)


#################
# Assault Plans #
#################

class AssaultPlan(dict):
    """The Bees' plan of attack for the colony.  Attacks come in timed waves.

    An AssaultPlan is a dictionary from times (int) to waves (list of Bees).

    >>> AssaultPlan().add_wave(4, 2)
    {4: [Bee(3, None), Bee(3, None)]}
    """

    def add_wave(self, bee_type, bee_health, time, count):
        """Add a wave at time with count Bees that have the specified health."""
        bees = [bee_type(bee_health) for _ in range(count)]
        self.setdefault(time, []).extend(bees)
        return self

    @property
    def all_bees(self):
        """Place all Bees in the beehive and return the list of Bees."""
        return [bee for wave in self.values() for bee in wave]
