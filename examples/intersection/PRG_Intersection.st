// PRG_Intersection: maps the intersection I/O to FB_Intersection.
PROGRAM PRG_Intersection
VAR
    fbIntersection  : FB_Intersection;  // the intersection
END_VAR

NETWORK Intersection
    -> fbIntersection(bFault := GVL_Intersection.bDI_Fault, bReset := GVL_Intersection.bDI_Reset,
                      bRedNS => GVL_Intersection.bDO_RedNS, bYellowNS => GVL_Intersection.bDO_YellowNS,
                      bGreenNS => GVL_Intersection.bDO_GreenNS, bRedEW => GVL_Intersection.bDO_RedEW,
                      bYellowEW => GVL_Intersection.bDO_YellowEW, bGreenEW => GVL_Intersection.bDO_GreenEW)
END_PROGRAM
