# Importing necessary libraries
import networkx as nx
from mesa import Model, Agent
from mesa.time import RandomActivation
from mesa.time import SimultaneousActivation
from mesa.space import NetworkGrid
from mesa.datacollection import DataCollector
import geopandas as gpd
import rasterio as rs
import matplotlib.pyplot as plt
import random

# Import the agent class(es) from agents.py
from agents import Households
from agents import Government

# Import functions from functions.py
from functions import get_flood_map_data, calculate_basic_flood_damage
from functions import map_domain_gdf, floodplain_gdf


# Define the AdaptationModel class
class AdaptationModel(Model):
    """
    The main model running the simulation. It sets up the network of household agents,
    simulates their behavior, and collects data. The network type can be adjusted based on study requirements.
    """

    def __init__(self, 
                 seed = None,
                 number_of_households = 20, # number of household agents
                 # Simplified argument for choosing flood map. Can currently be "harvey", "100yr", or "500yr".
                 flood_map_choice='harvey',
                 # ### network related parameters ###
                 # The social network structure that is used.
                 # Can currently be "erdos_renyi", "barabasi_albert", "watts_strogatz", or "no_network"
                 network = 'barabasi_albert', # 'watts_strogatz',
                 # likeliness of edge being created between two nodes
                 probability_of_network_connection = 0.4,
                 # number of edges for BA network
                 number_of_edges = 3,
                 # number of nearest neighbours for WS social network
                 number_of_nearest_neighbours = 5,
                 ):
        
        super().__init__(seed = seed)
        
        # defining the variables and setting the values
        self.number_of_households = number_of_households  # Total number of household agents
        self.seed = seed

        # network
        self.network = network # Type of network to be created
        self.probability_of_network_connection = probability_of_network_connection
        self.number_of_edges = number_of_edges
        self.number_of_nearest_neighbours = number_of_nearest_neighbours

        # generating the graph according to the network used and the network parameters specified
        self.G = self.initialize_network()
        # create grid out of network graph
        self.grid = NetworkGrid(self.G)

        # Initialize maps
        self.initialize_maps(flood_map_choice)

        # set schedule for agents
        # self.schedule = RandomActivation(self)  # Schedule for activating agents
        self.schedule = SimultaneousActivation(self)              #changed so that agents make the choice on willingness with the same information. With RandomActivation some agents would make the choice later, giving them an advantage.

        # create households through initiating a household on each node of the network graph
        for i, node in enumerate(self.G.nodes()):
            household = Households(unique_id=i, model=self)
            self.schedule.add(household)
            self.grid.place_agent(agent=household, node_id=node)

        # Data collection setup to collect data
        model_metrics = {
                        "total_adapted_households": self.total_adapted_households,
                        # ... other reporters ...
                        }
        
        agent_metrics = {
                        "FloodDepthEstimated": "flood_depth_estimated",
                        "FloodDamageEstimated" : "flood_damage_estimated",
                        "FloodDepthActual": "flood_depth_actual",
                        "FloodDamageActual" : "flood_damage_actual",
                        "IncomeClass" : "income_class",
                        "IsAdapted": "is_adapted",
                        # "FriendsCount": lambda a: a.count_friends(radius=2),            # REMOVE
                        "Willingness": "willingness",
                        "Awareness": "awareness",                                      # for DEBUGGING
                        "Reduction": "reduction"                                        #for debugging
                        # "location":"location",                                          # Maybe remove

                        }
        #set up the data collector 
        self.datacollector = DataCollector(model_reporters=model_metrics, agent_reporters=agent_metrics)

        # Create the Government agent and add it to the schedule
        # The Government agent is not associated with any node in the network
        self.government = Government(unique_id="gov", model=self)
        # self.schedule.add(self.government)


    def initialize_network(self):
        """
        Initialize and return the social network graph based on the provided network type using pattern matching.
        """
        # i need to add something here such as total_nodes, so I can change all the networks, and use allof them
        if self.network == 'erdos_renyi':
            return nx.erdos_renyi_graph(n=self.number_of_households,
                                        p=self.number_of_nearest_neighbours / self.number_of_households,
                                        seed=self.seed)
        elif self.network == 'barabasi_albert':
            return nx.barabasi_albert_graph(n=self.number_of_households,
                                            m=self.number_of_edges,
                                            seed=self.seed)
        elif self.network == 'watts_strogatz':
            return nx.watts_strogatz_graph(n=self.number_of_households,
                                        k=self.number_of_nearest_neighbours,
                                        p=self.probability_of_network_connection,
                                        seed=self.seed)
        elif self.network == 'no_network':
            G = nx.Graph()
            G.add_nodes_from(range(self.number_of_households))
            return G
        else:
            raise ValueError(f"Unknown network type: '{self.network}'. "
                            f"Currently implemented network types are: "
                            f"'erdos_renyi', 'barabasi_albert', 'watts_strogatz', and 'no_network'")


    def initialize_maps(self, flood_map_choice):
        """
        Initialize and set up the flood map related data based on the provided flood map choice.
        """
        # Define paths to flood maps
        flood_map_paths = {
            'harvey': r'../input_data/floodmaps/Harvey_depth_meters.tif',
            '100yr': r'../input_data/floodmaps/100yr_storm_depth_meters.tif',
            '500yr': r'../input_data/floodmaps/500yr_storm_depth_meters.tif'  # Example path for 500yr flood map
        }

        # Throw a ValueError if the flood map choice is not in the dictionary
        if flood_map_choice not in flood_map_paths.keys():
            raise ValueError(f"Unknown flood map choice: '{flood_map_choice}'. "
                             f"Currently implemented choices are: {list(flood_map_paths.keys())}")

        # Choose the appropriate flood map based on the input choice
        flood_map_path = flood_map_paths[flood_map_choice]

        # Loading and setting up the flood map
        self.flood_map = rs.open(flood_map_path)
        self.band_flood_img, self.bound_left, self.bound_right, self.bound_top, self.bound_bottom = get_flood_map_data(
            self.flood_map)

    def total_adapted_households(self):
        """Return the total number of households that have adapted."""
        #BE CAREFUL THAT YOU MAY HAVE DIFFERENT AGENT TYPES SO YOU NEED TO FIRST CHECK IF THE AGENT IS ACTUALLY A HOUSEHOLD AGENT USING "ISINSTANCE"
        adapted_count = sum([1 for agent in self.schedule.agents if isinstance(agent, Households) and agent.is_adapted])
        return adapted_count
    
    # def plot_model_domain_with_agents(self):
    #     fig, ax = plt.subplots()
    #     # Plot the model domain
    #     map_domain_gdf.plot(ax=ax, color='lightgrey')
    #     # Plot the floodplain
    #     floodplain_gdf.plot(ax=ax, color='lightblue', edgecolor='k', alpha=0.5)
    #
    #     # Collect agent locations and statuses
    #     for agent in self.schedule.agents:
    #         color = 'blue' if agent.is_adapted else 'red'
    #         ax.scatter(agent.location.x, agent.location.y, color=color, s=10, label=color.capitalize() if not ax.collections else "")
    #         ax.annotate(str(agent.unique_id), (agent.location.x, agent.location.y), textcoords="offset points", xytext=(0,1), ha='center', fontsize=9)
    #     # Create legend with unique entries
    #     handles, labels = ax.get_legend_handles_labels()
    #     by_label = dict(zip(labels, handles))
    #     ax.legend(by_label.values(), by_label.keys(), title="Red: not adapted, Blue: adapted")
    #
    #     # Customize plot with titles and labels
    #     plt.title(f'Model Domain with Agents at Step {self.schedule.steps}')
    #     plt.xlabel('Longitude')
    #     plt.ylabel('Latitude')
    #     plt.show()

    ## TESTING CODE SIDE BY SIDE # REMOVE THIS OR ABOVE AT LATER STAGE
    def plot_model_domain_with_agents(self, ax=None):
        if ax is None:
            fig, ax = plt.subplots()
        # Plot the model domain
        map_domain_gdf.plot(ax=ax, color='lightgrey')
        # Plot the floodplain
        floodplain_gdf.plot(ax=ax, color='lightblue', edgecolor='k', alpha=0.5)

        # Collect agent locations and statuses
        for agent in self.schedule.agents:
            color = 'blue' if agent.is_adapted else 'red'
            ax.scatter(agent.location.x, agent.location.y, color=color, s=10,
                       label=color.capitalize() if not ax.collections else "")
            ax.annotate(str(agent.unique_id), (agent.location.x, agent.location.y), textcoords="offset points",
                        xytext=(0, 1), ha='center', fontsize=9)
        # Create legend with unique entries
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), title="Red: not adapted, Blue: adapted")

        # Customize plot with titles and labels
        ax.set_title(f'Model Domain with Agents at Step {self.schedule.steps}')
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')


    def step(self):
        """
        introducing a shock: 
        at time step 5, there will be a global flooding.
        This will result in actual flood depth. Here, we assume it is a random number
        between 0.5 and 1.2 of the estimated flood depth. In your model, you can replace this
        with a more sound procedure (e.g., you can devide the floop map into zones and 
        assume local flooding instead of global flooding). The actual flood depth can be 
        estimated differently
        """

        self.government.step()                                               # This way Government does not have to be added to the scheduler, as that results in model problem which are out of my programming level.

        for agent in self.schedule.agents:                                   #each step, the model checks if the agent is adapapted, if it is, it lowers the flood depth estimated and the flood damge estimated
            if agent.is_adapted and not agent.final_adaption:                #This results in a lower flood depth actual and eventually a lowre flood damge actual
                agent.flood_depth_estimated *= (1 - agent.reduction)         # this means that investing in good floodadaptions lowers the damages.
                agent.flood_damage_estimated *= (1 - agent.reduction)
                agent.final_adaption = True
            else:
                continue

        if self.schedule.steps == 5:
            for agent in self.schedule.agents:

                # Calculate the actual flood depth as a random number between 0.5 and 1.2 times the estimated flood depth
                agent.flood_depth_actual = random.uniform(0.8, 1.2) * agent.flood_depth_estimated                       #maybe make the range smaller #based on harvey, see repor
                # calculate the actual flood damage given the actual flood depth
                agent.flood_damage_actual = calculate_basic_flood_damage(agent.flood_depth_actual)

        # TESTER
        # Calculate and print average willingness of all households
        # total_willingness = 0
        # household_count = 0
        # for agent in self.schedule.agents:
        #     if isinstance(agent, Households):
        #         total_willingness += agent.willingness
        #         household_count += 1
        #
        # if household_count > 0:
        #     average_willingness = total_willingness / household_count
        #     print(f"Average Willingness at Step {self.schedule.steps}: {average_willingness}")
        # else:
        #     print("No households to calculate average willingness.")

        # Collect data and advance the model by one step
        self.datacollector.collect(self)
        self.schedule.step()
