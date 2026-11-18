ENUMS = {'E_IntersectionState': ['AllRedToNS', 'GreenNS', 'YellowNS', 'AllRedToEW', 'GreenEW', 'YellowEW', 'Faulted']}
G = 'GVL_Intersection.'
St = 'PRG_Intersection.fbIntersection.eState'
SCENARIOS = {
    'green_ns': {St: 1, G + 'bDO_GreenNS': True, G + 'bDO_RedEW': True},
    'yellow_ew': {St: 5, G + 'bDO_YellowEW': True, G + 'bDO_RedNS': True},
    'all_red': {St: 3, G + 'bDO_RedNS': True, G + 'bDO_RedEW': True},
    'faulted': {St: 6, G + 'bDI_Fault': True, G + 'bDO_RedNS': True, G + 'bDO_RedEW': True},
}
