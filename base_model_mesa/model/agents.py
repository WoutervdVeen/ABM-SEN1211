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

    _income_classes_initialized = False
    _income_class_list = []
    _total_households = 20              # hard coded for now I want this to be a global, will do later

    @classmethod                           # class method
    def generate_income_class(cls):
        if not cls._income_classes_initialized:
            # Calculate the number of households for each income class
            distribution = {
                'lower': 0.20,  # 20%
                'lower-middle': 0.25,  # 25%
                'middle': 0.25,  # 25%
                'upper-middle': 0.15,  # 15%
                'upper': 0.15   # 15%
            }
            income_distribution = []
            for income_class, percentage in distribution.items():                #This function makes sure that the percentage per class is represented in the households.
                count = int(percentage * cls._total_households)                  # But making a list and the popping, it is possible to create the wanted amount per class.
                income_distribution.extend([income_class] * count)

            random.shuffle(income_distribution)
            cls._income_class_list = income_distribution
            cls._income_classes_initialized = True

        return cls._income_class_list.pop() if cls._income_class_list else 'default'

    def __init__(self, unique_id, model, subsidy=0):
        super().__init__(unique_id, model)
        self.income_class = Households.generate_income_class()                    # generates income class for each agent in a different function
        self.is_adapted = False  # Initial adaptation status set to False
        self.final_adaption = False # this boolean makes sure that once an adaption has been made, it doesnt go on adapting again and again
        self.in_danger = False # there is no flood damage estimated yet, no reason to adapt
        self.reduction = 0
        self.subsidy = subsidy # subsidy by government to allow the purchase of a higher flood protection than their current income class would typically allow.


        # add an attribute here that is linked with the likihood to adapt, maybe based on education or knowledge on flood risk


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



        if self.flood_damage_estimated > 0.15 and not self.is_adapted:      ## change this so that the fact that one adapts or not is subject to flood risk knowledge
            self.in_danger = True
            if random.random() < 0.2:                     ##Orginal code
                self.is_adapted = True




        if self.is_adapted and not self.final_adaption:                                                 #verbinden met measure
            # Implement logic for buying protection based on income class and adaptation status
            if self.is_adapted:
                if self.income_class == 'upper':
                    # Logic for upper income class to buy a certain protection
                    self.buy_protection('maximum_protection')
                elif self.income_class == 'upper-middle':
                    # Logic for upper-middle income class to buy a certain protection
                    self.buy_protection('high_protection')
                elif self.income_class == 'middle':
                    # Logic for middle and lower-middle income class to buy a certain protection
                    self.buy_protection('medium_protection')
                elif self.income_class == 'lower-middle':
                    # Logic for lower-middle income class to buy a certain protection
                    self.buy_protection('basic_protection')
                elif self.income_class == 'lower':
                    # Logic for lower income class to buy a certain protection
                    self.buy_protection('minimal_protection')
            else:
                # Logic for households that have not adapted
                pass

    def buy_protection(self, protection_type):                                                #Baseren op literatuur
        # Adjusting the logic to include possible subsidy by the government.
        # Example: if subsidy is 1, the household can buy protection one level higher

        income_classes = ['lower', 'lower-middle', 'middle', 'upper-middle', 'upper']  # available ino
        # Finding the index of the current income class and apply the subsidy
        current_index = income_classes.index(self.income_class)
        new_index = min(current_index + self.subsidy, len(income_classes) - 1)
        new_income_class = income_classes[new_index]

        # Define the percentage reduction in flood damage for each protection type
        damage_reduction = {
            'maximum_protection': 0.60, # 75% reduction for extreme protection
            'high_protection': 0.50,  # 50% reduction for high protection
            'medium_protection': 0.35,  # 35% reduction for medium protection
            'basic_protection': 0.20,  # 20% reduction for basic protection
            'minimal_protection': 0.10  # 10% reduction for minimal protection
        }

        self.reduction = damage_reduction.get(protection_type, 0)

        # Set the protection type
        self.protection_type = protection_type
        # self.final_adaption = True

    # def update_flood_damage(self):                    # IF I DONT USE THIS AGAIN, REMOVE (not in base model, forgot what it was for)
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


    def give_subsidies(self):
        # defines the amount of subsidy the government gives each household
        subsidy_amount = 1
        for agent in self.model.schedule.agents:
            if isinstance(agent,Households):
                agent.subsidy += subsidy_amount
    def step(self):
        # for debugging, at step 1 the government gives the households a subsidy.
        # if self.model.schedule.steps == 1:
        #     self.give_subsidies()


        # if goverment does subsidies: move up all household agents classes by one class.
        pass
# More agent classes can be added here, e.g. for insurance agents.
