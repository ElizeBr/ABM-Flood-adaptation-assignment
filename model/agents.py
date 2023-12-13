# Importing necessary libraries
import random
from mesa import Agent
from shapely.geometry import Point
from shapely import contains_xy

# Import functions from functions.py
from functions import generate_random_location_within_map_domain, get_flood_depth, calculate_basic_flood_damage
from functions import floodplain_multipolygon

discount_rate= 0.98

# Define the Households agent class
class Households(Agent):
    """
    An agent representing a household in the model.
    Each household has a flood depth attribute which is randomly assigned for demonstration purposes.
    In a real scenario, this would be based on actual geographical data or more complex logic.
    """

    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.is_adapted = False  # Initial adaptation status set to False

        # getting flood map values
        # Get a random location on the map
        loc_x, loc_y = generate_random_location_within_map_domain()
        self.location = Point(loc_x, loc_y)

        # Check whether the location is within floodplain
        self.in_floodplain = False
        if contains_xy(geom=floodplain_multipolygon, x=self.location.x, y=self.location.y):
            self.in_floodplain = True

        # Get the estimated flood depth at those coordinates. 
        # the estimated flood depth is calculated based on the flood map (i.e., past data) so this is not the actual flood depth
        # Flood depth can be negative if the location is at a high elevation
        self.flood_depth_estimated = get_flood_depth(corresponding_map=model.flood_map, location=self.location,
                                                     band=model.band_flood_img)
        # handle negative values of flood depth
        if self.flood_depth_estimated < 0:
            self.flood_depth_estimated = 0

        # calculate the estimated flood damage given the estimated flood depth. Flood damage is a factor between 0 and 1
        self.flood_damage_estimated = calculate_basic_flood_damage(flood_depth=self.flood_depth_estimated)

        # Add an attribute for the actual flood depth. This is set to zero at the beginning of the simulation since there is not flood yet
        # and will update its value when there is a shock (i.e., actual flood). Shock happens at some point during the simulation
        self.flood_depth_actual = 0

        # calculate the actual flood damage given the actual flood depth. Flood damage is a factor between 0 and 1
        self.flood_damage_actual = calculate_basic_flood_damage(flood_depth=self.flood_depth_actual)

        self.income = 2

        self.savings = 20

        self.flood_perception = 0.8

        self.taken_measures = 50

        self.money_saved = 30

        self.influence_factor = 0.1

        self.convincing = 0.3

    # Function to count friends who can be influencial.
    def count_friends(self, radius):
        """Count the number of neighbors within a given radius (number of edges away). This is social relation and not spatial"""
        friends = self.model.grid.get_neighborhood(self.pos, include_center=False, radius=radius)
        return len(friends)

    def save_money(self):
        self.money_saved += self.income
        print(self.money_saved)


    def influenced_by_neighbors(self, influence_factor):
        neighbors = self.model.grid.get_neighbors(self.pos, include_center=False)
        neighbor_ids = [neighbor.unique_id for neighbor in neighbors]
        print(f"Neighbors of agent {self.unique_id}: {neighbor_ids}")
        for neighbor in neighbors:
            self.flood_perception = discount_rate * self.flood_perception * (1 - neighbor.influence_factor) + neighbor.influence_factor * neighbor.flood_perception
        print(self.flood_perception)

     #def reconsider_adaptation_measures(self):
           # if self.flood_perception <0.2 and self.taken_measures:
             #self

     #def take_adaptation_measures(self):


    def step(self):
        # hier mogelijk if functie op basis van attributen hoe overtuigend en eigen perception
        print("Hi, I am agent " + str(self.unique_id) + ".")
        self.save_money()
        self.influenced_by_neighbors(self.influence_factor)
        print(f"{self.unique_id}: {self.flood_perception}")
        #self.reconsider_adaptation_measures()
        #self.take_adaptation_measures ()
        # Logic for adaptation based on estimated flood damage and a random chance.
        if self.flood_damage_estimated > 0.15 and random.random() < 0.2:
            self.is_adapted = True  # Agent adapts to flooding



# Define the Government agent class
class Government(Agent):
    """
    A government agent that currently doesn't perform any actions.
    """

    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)

    def step(self):
        # The government agent doesn't perform any actions.
        pass

# define Insurance agent
class Insurance(Agent):
    """
    An insurance agent that currently doesn't perform any actions.
    """
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)

    def step(self):
        # The insurance agent doesn't perform any actions yet.
        pass

# More agent classes can be added here, e.g. for insurance agents.
