import os
import pandas as pd
import gurobipy as gp

from gurobipy import GRB
from dotenv import load_dotenv
from enum import Enum

from p6.utils import log
logger = log.setupCustomLogger(__name__)

load_dotenv('variables.env')

#environment variables
options = {
    "WLSACCESSID": os.getenv("WLSACCESSID"),
    "WLSSECRET": os.getenv("WLSSECRET"),
    "LICENSEID": int(os.getenv("LICENSEID")),
}

class LinearOptimizationModel(Enum):
    """
    Enum class for the linear optimization models.
    """
    averageUtilization = 'averageUtilization'
    maxUtilization = 'maxUtilization'
    squaredUtilization = 'squaredUtilization'


def runLinearOptimizationModel(model, links, flows, traffic):
    """
    Runs the linear optimization model to calculate the link utilization and the average link utilization.

    ### Parameters:
    ----------
    #### model: string
    The optimization model to run, can be 'averageUtilization', 'maxUtilization', or 'squaredUtilization'.
    
    #### links: dict
    The links in the network, indexed by linkName.
    
    #### paths: dict
    The paths for each source-destination pair, with the paths split into a list of paths.
    
    #### traffic: dict
    The traffic for each source-destination pair.
    
    ### Returns:
    ----------
    The total link utilization, the average link utilization, and the link utilization for each link.
    """
    logger.info('Started running linear optimization model...')

    with gp.Env(params=options) as env, gp.Model(env=env) as m:
        # Create optimization model based on the input model
        m = gp.Model("network_optimization", env=env)

        m.setParam('logFile', 'gurobi.log')

        # Decision variables for path ratios for each source-destination pair
        path_ratios = m.addVars([(sd, pathNum) for sd in flows for pathNum in range(len(flows[sd]))], vtype=GRB.CONTINUOUS, name="PathRatios")
        match model:
            case LinearOptimizationModel.averageUtilization:
                utilization = m.addVars(links, vtype=GRB.CONTINUOUS, name="Utilization")
                m.setObjective(gp.quicksum((utilization[link]/links[link]['capacity'] for link in links)), GRB.MINIMIZE)
            case LinearOptimizationModel.maxUtilization:
                max_utilization = m.addVar(vtype=GRB.CONTINUOUS, name="MaxUtilization")
                m.setObjective(max_utilization, GRB.MINIMIZE)
            case LinearOptimizationModel.squaredUtilization:
                utilization = m.addVars(links, vtype=GRB.CONTINUOUS, name="Utilization")
                m.setObjective(gp.quicksum((utilization[link]**2 for link in links)), GRB.MINIMIZE)
            case _:
                raise ValueError(f'Invalid model: {model}')

        # Constraints for each link's utilization
        for link in links:
            linkTuple = tuple((link[:5], link[5:]))
            link_flow = gp.quicksum(
                path_ratios[sd, pathNum] * traffic[sd]
                if linkTuple in zip(flows[sd][pathNum][:-1], flows[sd][pathNum][1:])
                else 0
                for sd in flows for pathNum in range(len(flows[sd]))
            )

            m.addConstr(link_flow <= links[link]['capacity'], name=f"cap_{link}")

            match model:
                case LinearOptimizationModel.averageUtilization: 
                    m.addConstr(link_flow == links[link]['capacity'] * utilization[link], name=f"util_{link}")
                case LinearOptimizationModel.maxUtilization:
                    m.addConstr(link_flow / links[link]['capacity'] <= max_utilization, name=f"util_{link}")
                case LinearOptimizationModel.squaredUtilization:
                    m.addConstr(link_flow == utilization[link] * links[link]['capacity'], name=f"util_{link}")
                case _:
                    raise ValueError(f'Invalid model: {model}')
                
        for sd in traffic:
            m.addConstr(path_ratios.sum(sd, '*') == 1, name=f"traffic_split_{sd}")

        m.write(f"{model}.lp")

        logger.info('Started optimization...')

        m.optimize()

        logger.info('Finished optimization')

        # Output the results
        if m.status == GRB.OPTIMAL:
            #find largest util and print
            match model:
                case LinearOptimizationModel.averageUtilization:
                    totalLinkUtil = m.getObjective().getValue() / len(links) * 100
                case LinearOptimizationModel.maxUtilization:
                    totalLinkUtil = max_utilization.x * 100
                case LinearOptimizationModel.squaredUtilization:
                    totalLinkUtil = m.getObjective().getValue() / len(links) * 100
                case _:
                    raise ValueError(f'Invalid model: {model}')
            for sd in flows:
                logger.info(f"Optimal path ratios for {sd}:")
                for pathNum in range(len(flows[sd])):
                    logger.info(f"   Path {pathNum}: {path_ratios[sd, pathNum].x * 100} %")

            logger.info("")

            # Calculate average link utilization
            totalLinkUtil = 0
            for link in links:
                linkTuple = tuple((link[:5], link[5:]))
                link_flow = sum(
                    path_ratios[sd, pathNum].x * traffic[sd]
                    if linkTuple in zip(flows[sd][pathNum][:-1], flows[sd][pathNum][1:])
                    else 0
                    for sd in flows for pathNum in range(len(flows[sd]))
                )
                if (link_flow / links[link]['capacity'] * 100) >= 10:
                    logger.info(f'Link {link} has utilization: {link_flow / links[link]["capacity"] * 100}%')
                totalLinkUtil += link_flow / links[link]['capacity'] * 100
            totalLinkUtil = totalLinkUtil / len(links)
            logger.info(f"Average link utilization: {totalLinkUtil}% for model {model}")
        elif m.status == GRB.INFEASIBLE:
            logger.error('Model is infeasible')
            m.computeIIS()
            logger.error('The following constraints cannot be satisfied:')
            for c in m.getConstrs():
                if c.IISConstr:
                    logger.error(c.constrName)
        else:
            logger.error('Optimization ended with status %d' % m.status)