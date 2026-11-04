// E_IntersectionState: steps of the four-way intersection (north-south / east-west), in ring order.
// AllRedToNS is 0 so power-up starts with an all-red clearance. Keep Faulted last:
// FB_Intersection treats any value above it as invalid.
{attribute 'qualified_only'}
TYPE E_IntersectionState :
(
    AllRedToNS := 0,    // all red, north-south gets green next
    GreenNS,            // NS green, EW red
    YellowNS,           // NS yellow, EW red
    AllRedToEW,         // all red, east-west gets green next
    GreenEW,            // EW green, NS red
    YellowEW,           // EW yellow, NS red
    Faulted             // conflict monitor tripped: both directions flash red until reset
) UINT;
END_TYPE
