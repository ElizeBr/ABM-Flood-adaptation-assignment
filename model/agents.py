# Importing necessary libraries
import random
from mesa import Agent
from shapely.geometry import Point
from shapely import contains_xy

# Import functions from functions.py
from functions import generate_random_location_within_map_domain, get_flood_depth, calculate_basic_flood_damage
from functions import floodplain_multipolygon


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

        self.discount_rate = 0.98
        self.elevation_costs_per_square_metre = 220.982  # argumented in report
        self.max_damage_dol_per_sqm = 1216.65  # extracted from model file

        # range around average house size (159.14 square meters)
        self.size_of_house = random.randrange(120, 200)
        # range around average quarterly income (17078)
        self.income = random.randrange(13000, 22000)
        # start value of saved money (we could also randomize the 1.8)
        self.money_saved = self.income * 1.8

        self.trust_factor = random.uniform(0,0.1)

        self.taken_measures = random.random()
        self.taken_measures_list = []
        self.perceived_flood_probability = random.random()
        self.perceived_costs_of_measures = self.elevation_costs_per_square_metre * self.size_of_house
        self.perceived_flood_damage = None
        self.perceived_effectiveness_of_measures = 5
        self.desire_to_take_measures = False

    # Function to count friends who can be influential.
    def count_friends(self, radius):
        """Count the number of neighbors within a given radius (number of edges away). This is social relation and not spatial"""
        friends = self.model.grid.get_neighborhood(self.pos, include_center=False, radius=radius)
        return len(friends)

    def save_money(self):
        # print("Money before savings:" + str(self.money_saved))
        # print("Income" + str(self.income))
        self.money_saved += self.income * 0.05  # assumming that 5% of income are savings
        # print("Money saved: " + str(self.money_saved))

    def construct_perceived_flood_probability(self):
        neighbors = self.model.grid.get_neighbors(self.pos, include_center=False)

        # neighbor_ids = [neighbor.unique_id for neighbor in neighbors]
        # print(f"Neighbors of agent {self.unique_id}: {neighbor_ids}")

        # @ Fin, discount rate moet voor de for-loop, want nu wordt de discount rate afgetrokken voor elke neighbour,
        # en het moet maar 1 keer per ronde

        for neighbor in neighbors:
            self.perceived_flood_probability = (
                    self.discount_rate * self.perceived_flood_probability * (1 - neighbor.trust_factor) +
                    neighbor.trust_factor * neighbor.perceived_flood_probability)

        # TO DO: write part of function where perceived flood probability is influenced by government.
        # Bij government agent optie maken om de floodwarning op 1 van deze 3 waardes te zetten en dat heeft bepaalde invloed op perceived_flood_probability
        # weet zelf even niet hoe dit codetechnisch moet, variabele vanuit andere agent
        # Ik wil dat deze waarde bij de eerste timestep gelijk erbij wordt opgeteld en daarna niet meer. Op deze manier blijft de perceived flood probability niet oneindig stijgen. Ik weet alleen niet hoe dit moet
        # if government.flood_warning = "Low":
            #self.perceived_flood_probability = self.perceived_flood_probability + 0

        # elif government.flood_warning = "Medium":
            #self.perceived_flood_probability = self.perceived_flood_probability + 0.2
        # elif government.flood_warning = "High":
            # self.perceived_flood_probability = self.perceived_flood_probability + 0.4

    def construct_perceived_costs_of_measures(self):
        neighbors = self.model.grid.get_neighbors(self.pos, include_center=False)

        for neighbor in neighbors:
            self.perceived_costs_of_measures = (self.perceived_costs_of_measures * (1 - neighbor.trust_factor) +
                                                neighbor.trust_factor * neighbor.perceived_costs_of_measures)

        # TO DO: write part of function where perceived costs of measures is influenced by government
        # kan soortgelijk iets als bij flood_probability gedaan worden
    def construct_perceived_flood_damage(self):
        self.perceived_flood_damage = self.size_of_house * self.max_damage_dol_per_sqm * self.flood_damage_estimated
        # print("Flood depth:" + str(self.flood_depth_estimated))
        # print("Flood damage:" + str(self.perceived_flood_damage))

    def construct_perceived_effectiveness_of_measures(self):
        # effectiveness ratio: costs of measures divided by damage reducement
        self.perceived_effectiveness_of_measures = (self.perceived_costs_of_measures /
                                                    self.perceived_flood_damage)

    def consider_fine(self):
        print("Considering fine")
        # building block where household takes into account the fine of the government if it doesnt adapt

    def reconsider_adaptation_measures(self):
        if self.perceived_flood_probability > 0.4 and random.random() > 0.3:
            if self.perceived_effectiveness_of_measures < 1 and random.random() > 0.3:
        # of ipv de if functies kunnen we een soort formule schrijven
                self.desire_to_take_measures = True
            else:
                return
        else:
            return

    def take_adaptation_measures(self):
        if self.taken_measures < 1 and self.desire_to_take_measures == True:
            # ervan uitgaande dat mensen 80% van hun spaargeld aan adaptation uit willen geven
            money_to_spend_on_measures = self.money_saved * 0.8
            elevation_costs = self.size_of_house * self.elevation_costs_per_square_metre
            if money_to_spend_on_measures >= elevation_costs:
                self.taken_measures = 1
                self.money_saved -= elevation_costs
            elif 1.000 < money_to_spend_on_measures < elevation_costs:
                # adds a ratio of the complete elevation to the level of adaption, based on how much someone is able to spend
                self.taken_measures += (money_to_spend_on_measures / elevation_costs)
            else:
                return
        else:
            return

    def step(self):
        print("Hi, I am agent " + str(self.unique_id) + ".")
        self.save_money()
        self.construct_perceived_flood_probability()
        self.construct_perceived_flood_damage()
        # self.construct_perceived_costs_of_measures()
        # self.construct_perceived_flood_damage()
        # self.construct_perceived_effectiveness_of_measures()
        # self.consider_fine()
        # self.reconsider_adaptation_measures()
        # self.take_adaptation_measures ()

        # Logic for adaptation based on estimated flood damage and a random chance.
        # dit kan wel weggehaald worden
        if self.flood_damage_estimated > 0.15 and random.random() < 0.2:
            self.is_adapted = True  # Agent adapts to flooding


# Define the Government agent class
class Government(Agent):
    """
    A government agent that currently doesn't perform any actions.
    """

    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)

        self.flood_warning = "Low"
        self.subsidies = 0
        self.regulations = 0
        self.infrastructure = 0

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
