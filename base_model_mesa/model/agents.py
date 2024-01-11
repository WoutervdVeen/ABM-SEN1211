# Importing necessary libraries
import random
from mesa import Agent
from shapely.geometry import Point
from shapely import contains_xy

# Import functions from functions.py
from functions import generate_random_location_within_map_domain, get_flood_depth, calculate_basic_flood_damage, floodplain_multipolygon


# Define the Households agent class
class Households(Agent):
    """
    An agent representing a household in the model.
    Each household has a flood depth attribute which is randomly assigned for demonstration purposes.
    In a real scenario, this would be based on actual geographical data or more complex logic.
    """

    def __init__(self, unique_id, model, income_class_usage = True):
        super().__init__(unique_id, model)
        self.is_adapted = False  # Initial adaptation status set to False
        self.final_adaption = False # this boolean makes sure that once an adaption has been made, it doesnt go on adapting again and again
        self.in_danger = False # there is no flood damage estimated yet, no reason to adapt
        self.reduction = 0
        if income_class_usage:
        # self.income_class = random.choice(['low', 'middle', 'high'])   ## gives random income class to the households

            income_distribution = ['lower'] * 20 + ['lower-middle'] * 25 + ['middle'] * 25 + ['upper-middle'] * 15 + ['upper'] * 15  ## percentage based on literature (see report)
            random.shuffle(income_distribution)                                     ## assigns random distribution of the values
            self.income_class = income_distribution.pop()                           ## assigns income_class to agents
        else:
            self.income_class = None              #if boolean is off, dont use income class


        self.base_likelihood = 0.5  ##base likelihood variable that will impact the chance to get adapted. The likelihood gets affected by the income class of a household.

        ## to determine the likelihood per income class, for all the reasoning behind the chosen values see chapter ....
        self.income_likelihood = {
            'lower': 0.3,
            'lower-middle': 0.4,
            'middle': 0.5,
            'upper-middle': 0.6,              # very likely to
            'upper': 0.8                      # Super rich
        }


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
        self.flood_depth_estimated = get_flood_depth(corresponding_map=model.flood_map, location=self.location, band=model.band_flood_img)
        # handle negative values of flood depth
        if self.flood_depth_estimated < 0:
            self.flood_depth_estimated = 0
        
        # calculate the estimated flood damage given the estimated flood depth. Flood damage is a factor between 0 and 1
        self.flood_damage_estimated = calculate_basic_flood_damage(flood_depth=self.flood_depth_estimated)

        # Add an attribute for the actual flood depth. This is set to zero at the beginning of the simulation since there is not flood yet
        # and will update its value when there is a shock (i.e., actual flood). Shock happens at some point during the simulation
        self.flood_depth_actual = 0
        
        #calculate the actual flood damage given the actual flood depth. Flood damage is a factor between 0 and 1
        self.flood_damage_actual = calculate_basic_flood_damage(flood_depth=self.flood_depth_actual)


    
    # Function to count friends who can be influencial.
    def count_friends(self, radius):
        """Count the number of neighbors within a given radius (number of edges away). This is social relation and not spatial"""
        friends = self.model.grid.get_neighborhood(self.pos, include_center=False, radius=radius)
        return len(friends)

    def step(self):
        # Logic for adaptation based on estimated flood damage and a random chance.
        # These conditions are examples and should be refined for real-world applications.



        if self.flood_damage_estimated > 0.15 and not self.is_adapted:
            self.in_danger = True
            if random.random() < 0.2:                     ##Orginal code
                self.is_adapted = True

        # This code makes agents adapted based on their likeliness, based on their income class, it is not good yet.

        # if self.flood_damage_estimated > 0.15:
        #     self.in_danger = True              #
        #     if self.income_class in self.income_likelihood:
        #         likelihood = self.income_likelihood[self.income_class]
        #     else:
        #         likelihood = self.base_likelihood
        #
        #     if likelihood + 0.5 > 1: #random.random() > 1:
        #         self.is_adapted = True  # Agent adapts to flooding
        # else:
        #     self.is_adapted = False

        if self.is_adapted and not self.final_adaption:
            # Implement logic for buying protection based on income class and adaptation status
            if self.is_adapted:
                if self.income_class == 'upper':
                    # Logic for upper income class to buy a certain protection
                    self.buy_protection('high_protection')
                elif self.income_class == 'upper-middle':
                    # Logic for upper-middle income class to buy a certain protection
                    self.buy_protection('medium_protection')
                elif self.income_class in ['middle', 'lower-middle']:
                    # Logic for middle and lower-middle income class to buy a certain protection
                    self.buy_protection('basic_protection')
                elif self.income_class == 'lower':
                    # Logic for lower income class to buy a certain protection
                    self.buy_protection('minimal_protection')
            else:
                # Logic for households that have not adapted
                pass

    def buy_protection(self, protection_type):
        # Define the percentage reduction in flood damage for each protection type
        damage_reduction = {
            'high_protection': 0.50,  # 50% reduction for high protection
            'medium_protection': 0.35,  # 35% reduction for medium protection
            'basic_protection': 0.20,  # 20% reduction for basic protection
            'minimal_protection': 0.10  # 10% reduction for minimal protection
        }

        self.reduction = damage_reduction.get(protection_type, 0)

        # Set the protection type
        self.protection_type = protection_type
        # self.final_adaption = True

    # def update_flood_damage(self):
    #     # Calculate the actual flood depth as a random number between 0.5 and 1.2 times the estimated flood depth
    #     self.flood_depth_actual = random.uniform(0.5, 1.2) * self.flood_depth_estimated
    #     # calculate the actual flood damage given the actual flood depth
    #     agent.flood_damage_actual = calculate_basic_flood_damage(agent.flood_depth_actual)


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


        # if goverment does subsidies: move up all household agents classes by one class.

# More agent classes can be added here, e.g. for insurance agents.
