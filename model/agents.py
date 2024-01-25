# Importing necessary libraries
import random
import rasterio as rs
from mesa import Agent
from shapely.geometry import Point
from shapely import contains_xy

# Import functions from functions.py
from functions import get_flood_map_data
from functions import generate_random_location_within_map_domain, get_flood_depth, calculate_basic_flood_damage
from functions import floodplain_multipolygon


# Define the Households agent class
class Households(Agent):
    """
    An agent representing a household in the model.
    Each household has a flood depth attribute which is randomly assigned for demonstration purposes.
    In a real scenario, this would be based on actual geographical data or more complex logic.
    """

    def __init__(self, unique_id, model, fine=0):
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
        # the estimated flood depth is calculated based on the flood map (i.e., past data) so this is not the
        # actual flood depth
        # Flood depth can be negative if the location is at a high elevation
        self.flood_depth_estimated = get_flood_depth(corresponding_map=model.flood_map, location=self.location,
                                                     band=model.band_flood_img)

        flood_map_paths = {'harvey': r'../input_data/floodmaps/Harvey_depth_meters.tif',}
        flood_map_path = flood_map_paths['harvey']
        self.flood_map = rs.open(flood_map_path)
        self.band_flood_img, self.bound_left, self.bound_right, self.bound_top, self.bound_bottom = get_flood_map_data(
            self.flood_map)

        self.flood_depth_Harvey = get_flood_depth(corresponding_map=self.flood_map, location=self.location,
                                                     band=self.band_flood_img)
        # handle negative values of flood depth
        if self.flood_depth_estimated < 0:
            self.flood_depth_estimated = 0

        # calculate the estimated flood damage given the estimated flood depth. Flood damage is a factor between 0 and 1
        self.flood_damage_estimated = calculate_basic_flood_damage(flood_depth=get_flood_depth(corresponding_map=model.flood_map, location=self.location,
                                                     band=model.band_flood_img))

        # Add an attribute for the actual flood depth. This is set to zero at the beginning of the simulation since there is not flood yet
        # and will update its value when there is a shock (i.e., actual flood). Shock happens at some point during the simulation
        self.flood_depth_actual = 0

        # calculate the actual flood damage given the actual flood depth. Flood damage is a factor between 0 and 1
        self.flood_damage_actual = calculate_basic_flood_damage(flood_depth=self.flood_depth_actual)
        self.flood_damage_final = 0
        self.whatif_damage = 0
        self.discount_rate = 0.99
        self.elevation_costs_per_square_metre = 290
        self.max_damage_dol_per_sqm = 1216.65  # extracted from model file

        # range around average house size (159.14 square meters)
        self.size_of_house = random.randrange(120, 200)
        # range around average quarterly income (17078)
        self.income = random.randrange(13000, 22000)
        # start value of saved money (we could also randomize the 1.8)
        self.money_saved = self.income * 1.8

        self.trust_factor = random.uniform(0,0.1)
        self.fine = fine
        self.taken_measures = random.triangular(0,0.8,0.1)
        self.perceived_flood_probability = random.random()
        self.perceived_costs_of_measures = self.elevation_costs_per_square_metre * self.size_of_house
        self.perceived_flood_damage = None
        self.perceived_effectiveness_of_measures = None
        self.desire_to_take_measures = False

    # Function to count friends who can be influential.
    def count_friends(self, radius):
        """Count the number of neighbors within a given radius (number of edges away). This is social relation and not spatial"""
        friends = self.model.grid.get_neighborhood(self.pos, include_center=False, radius=radius)
        return len(friends)

    def save_money(self):
        # print("Money before savings:" + str(self.money_saved))
        # print("Income" + str(self.income))
        self.money_saved += self.income * 0.05
        # print("Money saved after one round: " + str(self.money_saved))

    def construct_perceived_flood_probability(self):
        neighbors = self.model.grid.get_neighbors(self.pos, include_center=False)

        # neighbor_ids = [neighbor.unique_id for neighbor in neighbors]
        # print(f"Neighbors of agent {self.unique_id}: {neighbor_ids}")

        self.perceived_flood_probability = self.discount_rate * self.perceived_flood_probability
        for neighbor in neighbors:
            if isinstance(neighbor, Households):
                self.perceived_flood_probability = (
                    self.perceived_flood_probability * (1 - neighbor.trust_factor) +
                    neighbor.trust_factor * neighbor.perceived_flood_probability)

            #government doet ook hier iets voor, maar dan in de government agent

    def construct_perceived_flood_damage(self):
        self.perceived_flood_damage = self.size_of_house * self.max_damage_dol_per_sqm * self.flood_damage_estimated
        # print("Flood depth:" + str(self.flood_depth_estimated))
        #print("Flood damage:" + str(self.perceived_flood_damage))

    def construct_perceived_effectiveness_of_measures(self):
        # effectiveness ratio: costs of measures divided by damage reduction
        # when above 1, thought to be effective
        # fine is multiplied by 8 to show that households take into account that fines are fines multiple times
        self.perceived_effectiveness_of_measures = ((self.perceived_flood_damage + self.fine*5) / self.perceived_costs_of_measures)

    def reconsider_adaptation_measures(self):
        if self.perceived_effectiveness_of_measures > 4 and self.perceived_flood_probability > 0.2:
            self.desire_to_take_measures = True
        elif self.perceived_effectiveness_of_measures > 3 and self.perceived_flood_probability > 0.4:
            self.desire_to_take_measures = True
        elif self.perceived_effectiveness_of_measures > 2 and self.perceived_flood_probability > 0.6:
            self.desire_to_take_measures = True
        elif self.perceived_effectiveness_of_measures > 1.5 and self.perceived_flood_probability > 0.8:
            self.desire_to_take_measures = True
        elif self.perceived_effectiveness_of_measures > 1 and self.perceived_flood_probability > 0.9:
            self.desire_to_take_measures = True
        else:
            self.desire_to_take_measures = False
        ## willen we nog een fine over een tijd, dus dat de fine bijv 10 keer meeteld omdat je dan 1- jaar een fine betaald?
        adaptation_treshold = 1.2
        leaning_towards_adaptation = (self.perceived_flood_probability*2) * self.perceived_effectiveness_of_measures
        #print(f"probability: {self.perceived_flood_probability}")
        #print(f"flood damage: {self.perceived_flood_damage}")
        #print(f"cost of measures: {self.perceived_costs_of_measures}")
        #print(f"effectiveness: {self.perceived_effectiveness_of_measures}")
        #print(f"leaning towards measures:{leaning_towards_adaptation}")
        # if (self.perceived_flood_probability*2) * self.perceived_effectiveness_of_measures >= adaptation_treshold: #flood probability is multiplied by 2 so that is has more or less equal influence in the decissionmaking as the effectiveness
        #     self.desire_to_take_measures = True
        # #if self.perceived_flood_probability * self.perceived_flood_damage - self.perceived_costs_of_measures + self.fine  >= treshold:
        #
        # else:
        #     self.desire_to_take_measures = False

    def take_adaptation_measures(self):
        if self.taken_measures < 1 and self.desire_to_take_measures == True:
            money_to_spend_on_measures = self.money_saved
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
        #print("Hi, I am agent " + str(self.unique_id) + ".")
        self.save_money()
        self.construct_perceived_flood_probability()
        self.construct_perceived_flood_damage()
        self.construct_perceived_effectiveness_of_measures()
        self.reconsider_adaptation_measures()
        self.take_adaptation_measures()

        if self.taken_measures > 0.8:
            self.is_adapted = True

        #print(f"Desire to take measure: {self.desire_to_take_measures}")
        #print(f"Adapted: {self.is_adapted}")

# Define the Government agent class
class Government(Agent):
    """
    A government agent that currently doesn't perform any actions.
    """

    def __init__(self, unique_id, model, fine = 0):
        super().__init__(unique_id, model)

        self.flood_warning = "Medium"
        self.subsidies = 0
        self.regulations = 0.2
        self.infrastructure = 0
        loc_x, loc_y = generate_random_location_within_map_domain()
        self.location = Point(loc_x, loc_y)
        self.fine = fine
        self.household_list= []
        self.fined_household_list= []
        self.fined_total = 0
        self.step_counter = 0
    def warn_households(self, schedule_of_households): #gebruik een list van de households, schedule voor volgorde.
        flood_warning_effectiveness = 0
        if self.flood_warning == "Low":
            flood_warning_effectiveness = 0
        elif self.flood_warning == "Medium":
            flood_warning_effectiveness = 0.1
        elif self.flood_warning == "High":
            flood_warning_effectiveness = 0.2

        for agent in schedule_of_households:
            if isinstance(agent, Households):
                agent.perceived_flood_probability = (
                    agent.perceived_flood_probability * (1 - flood_warning_effectiveness) +
                    flood_warning_effectiveness)

    def count_friends(self, radius):
        #to fix the reporting
        return None
    #you are certified if you have a lower flood damage than the regulation. The harvey flood is used as a baseline.
    def complies_with_certification(self, household):
        if calculate_basic_flood_damage(flood_depth= household.flood_depth_Harvey) - household.taken_measures <= self.regulations:
            return True
        else:
            return False

    def fine_household(self, household):
        household.money_saved -= self.fine
        self.fined_household_list.append(household)
        self.fined_total += self.fine

    def check_certification(self, household):
        if not self.complies_with_certification(household):
            self.fine_household(household)

    def check_all_households(self):
        #There is a chance for every household that they are checked.
        for household in self.household_list:
            if isinstance(household, Households):
                self.check_certification(household)

    def step(self):
        self.step_counter += 1

        if (self.step_counter+1) % 8 == 0:
            self.check_all_households()

        if (self.step_counter+1) % 10 == 0:
            self.warn_households(self.household_list)

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

