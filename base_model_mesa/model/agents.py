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
    def __init__(self, unique_id, model):                # Remove unnecessary self.statements here, do i even need to do it here or is in the text also oke?
        super().__init__(unique_id, model)
        unique_seed = model.seed + unique_id
        self.random_generator = random.Random(unique_seed)           # setting the seed to the seed set in the model initialization
        self.is_adapted = False
        self.income_class = Households.generate_income_class()      # Generates income class for each agent in a different function
        self.willingness = 0                                        # Willingness to adapt starts of at 0, this can be affected by friends and awareness
        self.awareness = self.random_generator.uniform(0.2, 1)               # Randomizer for the awareness of the household, class does not determine awareness.
        self.final_adaption = False                                 # This boolean makes sure that once an adaption has been made, it doesnt go on adapting again and again
        self.reduction = 0                                          # No initial reduction.
        self.adapted_friends_percentage = 0                         # Initially the households have no friends that are adapetd, this needs to be an attribute so that it can be used to calculate willingness
        self.subsidy = 0                                            # Intially there is no subsidy, Government can change this value to 1, this is not a Boolean so that the government could potentiall increase subsidy to 2


        unique_seed = model.seed + unique_id                        # so that each agent is individually randomized to be adapted in the next code
        self.local_random = random.Random(unique_seed)
        if self.local_random.random() > 0.90:                                  # There is a 10 percent chance that a household is already adapted
            self.is_adapted = True
            self.initial_adaptation_setup()                         # Prior adapted households still need to get their bought protection, but adding this function (which is a but dubbel op) this can be assured.
        else:
            self.is_adapted = False  # Initial adaptation status set to False

        # add an attribute here that is linked with the likihood to adapt, maybe based on awareness or knowledge on flood risk


        # getting flood map values
        # Get a random location on the map
        loc_x, loc_y = generate_random_location_within_map_domain(model.seed, self.unique_id)       #generates a location with the random unique to respect the seed
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
        self.initial_damage_estimated = self.flood_damage_estimated       #for the result analysis this is necessary.

        # Add an attribute for the actual flood depth. This is set to zero at the beginning of the simulation since there is not flood yet
        # and will update its value when there is a shock (i.e., actual flood). Shock happens at some point during the simulation
        self.flood_depth_actual = 0
        
        #calculate the actual flood damage given the actual flood depth. Flood damage is a factor between 0 and 1
        self.flood_damage_actual = calculate_basic_flood_damage(flood_depth=self.flood_depth_actual)


    _income_classes_initialized = False
    _income_class_list = []
    _total_households = 100              # hard coded for now I want this to be a global, will do later

    @classmethod                           # class method
    def generate_income_class(cls):
        if not cls._income_classes_initialized:
            # Calculate the number of households for each income class        #Distribution is based on literature, see report. Values have been rounded so that the model can be run.
            distribution = {
                'lower': 0.20,  # 20%
                'lower-middle': 0.15,  # 25%
                'middle': 0.30,  # 25%
                'upper-middle': 0.30,  # 15%
                'upper': 0.05   # 15%
            }
            income_distribution = []
            for income_class, percentage in distribution.items():                #This function makes sure that the percentage per class is represented in the households.
                count = int(percentage * cls._total_households)                  # But making a list and the popping, it is possible to create the wanted amount per class.
                income_distribution.extend([income_class] * count)               # distribution hoeft niet gerandomiseerd te worden aangezien er met seeds experimenten worden gerunt, voor een gerandomiseerd model zou het wel van belang zijn.

            # # Create a local random generator for this method
            # local_random = random.Random(seed)
            #
            # # Shuffle the income distribution list using the local random generator
            # local_random.shuffle(income_distribution)

            # random.shuffle(income_distribution)
            cls._income_class_list = income_distribution
            cls._income_classes_initialized = True

        return cls._income_class_list.pop() if cls._income_class_list else 'default'

    def count_friends(self, radius):
        """Count the number of adapted neighbors within a given radius."""
        # at step 0, each Agent has no adapted friends, but due to the fact that the agent steps are executed one by one, agents that are executed later have a chance to have adapted friends.
        # To mitigate the effect that this has on the calculatd willingness, agents will by activated Simultaneously (SimultaneousActivation) instead of Randomly (RandomActivation)
        # Due to the fact that

        # Retrieve all neighbor nodes within the specified radius
        neighbor_nodes = self.model.grid.get_neighborhood(self.pos, include_center=False, radius=radius)

        # Retrieve agents in these nodes
        neighbor_agents = [self.model.grid.get_cell_list_contents([node])[0] for node in neighbor_nodes]

        # Count the number of adapted neighbors
        adapted_friends_count = sum(agent.is_adapted for agent in neighbor_agents)

        # Calculate the total number of friends
        total_friends_count = len(neighbor_agents)

        # Calculate the percentage of adapted friends
        if total_friends_count > 0:
            self.adapted_friends_percentage = (adapted_friends_count / total_friends_count)       # the attribute of a household will now be changed in to a percentage
        else:
            adapted_percentage = 0


    def calculate_friend_influence(self):
        # the percentage of friends who are adapted influences the willingess, a lot of adapted friends increase the willingness with 2 points, more than half is 1 point etc.
        if self.adapted_friends_percentage > 0.75:                       # if all almost all youre friends are adapting to floodrisk you will want to do it too ( see report)
            return 2  # High Positive influence
        elif self.adapted_friends_percentage >= 0.50:
            return 1  # Positive influence
        elif self.adapted_friends_percentage < 0.50:
            return -1
        elif self.adapted_friends_percentage > 0.25:                     # if none of your friends are adapting to floodrisk, you will not be likely to make this investment.
            return -2  # Low influence
        else:
            return 0  # No influence

    def calculate_flood_damage_estimated_influence(self):
        if self.flood_damage_estimated >= 0.68:                  # this damage factor is equal to a water depth of 1.5 meter (see report)
            return 3 # high positive influence
        elif self.flood_damage_estimated >= 0.58:                # this damage factor is equal to 1 meter water depth
            return 2 # medium influence
        elif self.flood_damage_estimated >= 0.20:                # this damage factor is equal to water depth higher than 0 -> so a base risk
            return 1 # influence
        elif self.flood_damage_estimated == 0:                   # if there is no flood damage estimated, then it is highly unlikely a household will adapt
            return -2
        else:
            return 0 # little to no risk -> no influence

    def calculate_awareness_influence(self):
        #how mare aware a household is of floods and the dangers, the more a household will be willing
        # awareness is hightened by government class with their awareness campaign.
        # this method means that a household has a chance of 1/8 exceeding the maximum awarness and reaping the max benfits of the  awareness.
        if self.awareness >= 0.8:
            return 2
        elif self.awareness >=0.50:
            return 1
        else:
            return 0 # awareness is not high enough to influence the willingness


        pass
    def calculate_willingness(self):
        """" willingness is calculated with the awareness, the network and estimated_flood_damage"""
        # A Households willingness to adapt is influenced by three factors: estimated flood damages, how many of their friends are adapted and how aware the household is of the floodrisk
        # -> see report

        friend_influence = self.calculate_friend_influence()
        damage_influence = self.calculate_flood_damage_estimated_influence()
        awareness_influence = self.calculate_awareness_influence()
        self.willingness = friend_influence + damage_influence + awareness_influence

        # print(f"Agent {self.unique_id} is_adapted: {self.is_adapted} friends:{friend_influence}, damage:{damage_influence}, awareness:{awareness_influence}           total willingness: {self.willingness}")

    def buy_protection(self, protection_type):                                                #Baseren op literatuur
        # Household buys damage reduction according to its income class, if subsidy = 1 a household buys a damage reduction a class higher.

        # Adjust the protection type if subsidy is provided
        if self.subsidy == 1:
            # Define a mapping from one protection type to a higher one
            upgrade_mapping = {
                'minimal_protection': 'basic_protection',
                'basic_protection': 'medium_protection',
                'medium_protection': 'high_protection',
                'high_protection': 'maximum_protection',
                'maximum_protection': 'maximum_protection'  # already the highest level
            }
            # Upgrade the protection type
            protection_type = upgrade_mapping.get(protection_type, protection_type)


        # Define the percentage reduction in flood damage for each protection type
        damage_reduction = {
            'maximum_protection': 0.60, # 60% reduction for extreme protection
            'high_protection': 0.50,    # 50% reduction for high protection
            'medium_protection': 0.35,  # 35% reduction for medium protection
            'basic_protection': 0.20,   # 20% reduction for basic protection
            'minimal_protection': 0.10  # 10% reduction for minimal protection
        }



        self.reduction = damage_reduction.get(protection_type, 0)

        # Set the protection type
        self.protection_type = protection_type

    def initial_adaptation_setup(self):                                                         #possibly uneccesarry

        if self.is_adapted == True:
            # Determine the protection type based on the income class and subsidy
            if self.income_class == 'upper':
                self.buy_protection('maximum_protection')
            elif self.income_class == 'upper-middle':
                self.buy_protection('high_protection')
            elif self.income_class == 'middle':
                self.buy_protection('medium_protection')
            elif self.income_class == 'lower-middle':
                self.buy_protection('basic_protection')
            elif self.income_class == 'lower':
                self.buy_protection('minimal_protection')

    def step(self):

        self.count_friends(2)  # use last steps percentage of adapted friends, otherwise certain households have an unfair advantage
        self.calculate_willingness()  # goes to the calculate willingness

        if self.willingness >= 3:                                      # this is subject to change ## HERCHECKEN -> dicht bij gemiddelde
            # if random.random() < 0.85:    add later when im sure the model is working properly        #0.2         # There is always a 15% chance that someone doesnt adapt, eventhough they are willing. ->REPORT-WRITE
            self.is_adapted = True

        if self.is_adapted and not self.final_adaption:                                                 #verbinden met measure
            # Implement logic for buying protection based on income class and adaptation status
            if self.is_adapted:
                if self.income_class == 'upper':# or (self.income_class == 'upper-middle' and self.subsidy == 1):              #REMOVE THIS LINE IF THE OTHER SUBSIDY WORKS
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

# ************************************************************************************** #
# ************************************************************************************** #
# **************************  --- RESUABLE BUILDING BLOCK --- ************************** #
# ************************************************************************************** #
# ************************************************************************************** #

class Government(Agent):             # make this a function.
    """
    A government agent that has two possible actions: Subsidizing (A) and Awareness Campaign (B)
    """
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.gov_action_A_sub = model.gov_action_A_sub
        self.gov_action_B_awa = model.gov_action_B_awa


    def give_subsidies(self):
        '''Government Action A: Subsidize Flood adaptations, giving houeholds money so that they can purchase better flood adaptations'''
        # defines the amount of subsidy the government gives each household
        # if goverment does subsidies: move up all household agents classes by one class.
        subsidy_amount = 1

        for agent in self.model.schedule.agents:
            if isinstance(agent, Households):
                agent.subsidy += subsidy_amount
        pass

    def awareness_campaign(self):   # only works one step later,
        '''Goverment Action B: Awareness Campaign, informing households on floodrisks and stimulating them to take action and adapt.'''
        #Increase the awareness of each household by a random value between 0 and 1
        # so in the end, a households awareness is decided by the addition of two randomly generated values between 0 and 1                      -> REPORT-WRITE
        for agent in self.model.schedule.agents:
            if isinstance(agent, Households):
                unique_seed = self.model.seed + agent.unique_id
                local_random = random.Random(unique_seed)

                increase = local_random.uniform(0,1)
                agent.awareness = agent.awareness + increase
        pass

    def step(self):

        if self.gov_action_A_sub == True:                           #
            if self.model.schedule.steps == 0:              # households that are already adapted are too late for the subsidy and thus dont get it.
                self.give_subsidies()

        if self.gov_action_B_awa == True:                      #boolean to turn on and off,
            if self.model.schedule.steps == 3:              #
                self.awareness_campaign()
            pass


# ************************************************************************************** #
# ************************************************************************************** #
# **************************  --- RESUABLE BUILDING BLOCK --- ************************** #
# ************************************************************************************** #
# ************************************************************************************** #