from ants import *
beehive, layout = Hive(AssaultPlan()), dry_layout
dimensions = (1, 9)
gamestate = GameState(None, beehive, ant_types(), layout, dimensions)

ant = ShortThrower()
ant.name = 'short2'
ant.max_range = 10   # Buff the ant's range
gamestate.places["tunnel_0_0"].add_insect(ant)
bee = Bee(2)
gamestate.places["tunnel_0_6"].add_insect(bee)
ant.action(gamestate)
print(bee.health)