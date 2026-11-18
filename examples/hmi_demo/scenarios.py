D = 'GVL_HmiDemo.'
SCENARIOS = {
 'idle': {D+'iState': 0, D+'lrLevel': 3.0, D+'lrTemp': 21.5, D+'bLow': True, D+'lrSetpoint': 80},
 'filling': {D+'iState': 1, D+'lrLevel': 48.2, D+'lrTemp': 22.0, D+'bPump': True, D+'lrSetpoint': 80, D+'uiFillCount': 12},
 'fault': {D+'iState': 4, D+'uiFault': 1, D+'lrLevel': 99.0, D+'bHigh': True, D+'lrSetpoint': 80},
}
ENUMS = {}
