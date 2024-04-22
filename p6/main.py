import gurobipy as gp

from gurobipy import GRB

from p6.utils import data as dataUtils
from p6.utils import network as nwUtils
from p6.utils import log
logger = log.setupCustomLogger(__name__)

import pandas as pd

DATA_DAY = 2

# --- FUNCTIONS ---
def calcLinkUtil(links):
    util = {}

    for linkKey in links:
        util[linkKey] = links[linkKey]['totalTraffic'] / links[linkKey]['capacity'] * 100

    return util

def main():
    logger.info('Started')

    flows = dataUtils.readFlows(DATA_DAY)
    links = dataUtils.readLinks()
    traffic = dataUtils.readTraffic(DATA_DAY)

    for timestamp in flows:
        # Reset totalTraffic for all links in this timestamp
        for linkKey in links:
            links[linkKey]['totalTraffic'] = 0

        for i, flow in enumerate(flows[timestamp]):
            routers = nwUtils.getRoutersHashFromFlow(flows[timestamp][flow])
            flowLinks = nwUtils.getFlowLinks(routers, links)

            # Update links with traffic
            for linkKey in flowLinks:
                if(linkKey in links):
                    links[linkKey]['totalTraffic'] += traffic[timestamp][flow] * flowLinks[linkKey].trafficRatio
                else:
                    links[linkKey] = {
                        'linkStart': flowLinks[linkKey].linkStart,
                        'linkEnd': flowLinks[linkKey].linkEnd,
                        'capacity': flowLinks[linkKey].capacity,
                        'totalTraffic': traffic[timestamp][flow] * flowLinks[linkKey].trafficRatio
                        }

            # Log number of processed flows
            if(i % 10000 == 0):
                logger.info(f'Processed {timestamp} {i+1} flows of {len(flows[timestamp])}...')
            if(i == len(flows[timestamp]) - 1):
                logger.info(f'Processed {timestamp} {i+1} flows of {len(flows[timestamp])}...')
            
    
        linkUtil = calcLinkUtil(links)
        
        # for linkKey in links:
        #     procentage = links[linkKey]['totalTraffic'] / links[linkKey]['capacity'] * 100
        #     if(procentage >= 70):
        #         print(f'{timestamp} Link: {links[linkKey]}')
        #         print(f'{timestamp} - {procentage}%')
        

   

    # logger.debug(f"Flows: {len(flows)}")

    # for flow in flows:
    #     print(f"Flow: {flow}")
    #     for path in flows[flow]:
    #         print(f"-: {path}")
    #     print("\n")

    # # --- LINKS ---
    # linksCapacity = {}
    # linksCapacity['AB'] = 600
    # linksCapacity['AC'] = 2000
    # linksCapacity['BD'] = 500
    # linksCapacity['BE'] = 600
    # linksCapacity['CF'] = 1500
    # linksCapacity['DG'] = 400
    # linksCapacity['EG'] = 600
    # linksCapacity['FG'] = 1500

    # # --- PATHS ---
    # flows = {}
    # flows['AG'] = {}
    # flows['AG'][0] = ['A', 'B', 'D', 'G']
    # flows['AG'][1] = ['A', 'B', 'E', 'G']
    # flows['AG'][2] = ['A', 'C', 'F', 'G']

    # # --- TRAFFIC ---
    # traffic = {}
    # traffic['AG'] = 100

    # # --- RATIOS ---

    # logger.info('Populating routers hash from flows')
    # routersHash = nwUtils.getRoutersHashFromFlows(flows)
    
    # logger.info('Calculating ratios')
    # links = {}
    # nwUtils.recCalcRatios(links, routersHash['G'], linksCapacity)
