// FB_Intersection: four-way intersection, fixed-time. North-south and east-west alternate
// green -> yellow -> all red. A fault input (conflict monitor) forces both directions to
// flash red until the fault is gone and the reset button is pressed.
// Ladder sequence: transitions -> commit -> jumps -> commit -> state decode -> on change -> cyclic.
FUNCTION_BLOCK FB_Intersection
VAR_INPUT
    bFault          : BOOL;     // external fault / conflict monitor, TRUE = fault
    bReset          : BOOL;     // fault reset (rising edge)
END_VAR
VAR_OUTPUT
    eState          : E_IntersectionState;  // current step, for HMI / online view
    bRedNS          : BOOL;     // north-south red
    bYellowNS       : BOOL;     // north-south yellow
    bGreenNS        : BOOL;     // north-south green
    bRedEW          : BOOL;     // east-west red
    bYellowEW       : BOOL;     // east-west yellow
    bGreenEW        : BOOL;     // east-west green
END_VAR
VAR
    _eState         : E_IntersectionState;  // the state; eState is only a copy for the caller
    _eNextState     : E_IntersectionState;  // written by transitions and jumps
    _eLastState     : E_IntersectionState;
    _bStateChanged  : BOOL;             // TRUE on the scan the state changed
    _bStAllRedToNS  : BOOL;             // state decoded after the commits: one BOOL per state
    _bStGreenNS     : BOOL;
    _bStYellowNS    : BOOL;
    _bStAllRedToEW  : BOOL;
    _bStGreenEW     : BOOL;
    _bStYellowEW    : BOOL;
    _bStFaulted     : BOOL;
    _tStepTime      : TIME := ALL_RED_TIME; // time of the current step, starts as AllRedToNS
    _fbStepTimer    : TON;
    _bFlashOn       : BOOL;             // flash phase for the red lamps in Faulted
    _fbFlashOff     : TON;              // times the dark half of the flash
    _fbFlashLit     : TON;              // times the lit half of the flash
END_VAR
VAR CONSTANT
    GREEN_TIME      : TIME := T#10S;
    YELLOW_TIME     : TIME := T#3S;
    ALL_RED_TIME    : TIME := T#2S;
    FLASH_HALF_TIME : TIME := T#500MS;
END_VAR

// ===== 1. Transitions only =====
NETWORK T AllRedToNS -> GreenNS
    [_eState = E_IntersectionState.AllRedToNS] _fbStepTimer.Q -> _eNextState := E_IntersectionState.GreenNS

NETWORK T GreenNS -> YellowNS
    [_eState = E_IntersectionState.GreenNS] _fbStepTimer.Q -> _eNextState := E_IntersectionState.YellowNS

NETWORK T YellowNS -> AllRedToEW
    [_eState = E_IntersectionState.YellowNS] _fbStepTimer.Q -> _eNextState := E_IntersectionState.AllRedToEW

NETWORK T AllRedToEW -> GreenEW
    [_eState = E_IntersectionState.AllRedToEW] _fbStepTimer.Q -> _eNextState := E_IntersectionState.GreenEW

NETWORK T GreenEW -> YellowEW
    [_eState = E_IntersectionState.GreenEW] _fbStepTimer.Q -> _eNextState := E_IntersectionState.YellowEW

NETWORK T YellowEW -> AllRedToNS
    [_eState = E_IntersectionState.YellowEW] _fbStepTimer.Q -> _eNextState := E_IntersectionState.AllRedToNS

NETWORK T Faulted -> AllRedToNS
// Leaves only when the fault is gone and reset is pressed
    [_eState = E_IntersectionState.Faulted] /bFault P:bReset -> _eNextState := E_IntersectionState.AllRedToNS

NETWORK T Invalid state -> AllRedToNS
// The CASE ELSE: an unknown value (e.g. after an online change) restarts from all red
    [_eState > E_IntersectionState.Faulted] -> _eNextState := E_IntersectionState.AllRedToNS

NETWORK Commit transitions
    -> _eState := _eNextState

// ===== 2. Jumps =====
NETWORK J1 Fault
// From any state except Faulted; overrides the transitions above
    [_eState <> E_IntersectionState.Faulted] bFault -> _eNextState := E_IntersectionState.Faulted

NETWORK Commit jumps
    -> _eState := _eNextState

// ===== State decode: one compare per rung, so later rungs use contacts =====
NETWORK Decode AllRedToNS
    [_eState = E_IntersectionState.AllRedToNS] -> _bStAllRedToNS

NETWORK Decode GreenNS
    [_eState = E_IntersectionState.GreenNS] -> _bStGreenNS

NETWORK Decode YellowNS
    [_eState = E_IntersectionState.YellowNS] -> _bStYellowNS

NETWORK Decode AllRedToEW
    [_eState = E_IntersectionState.AllRedToEW] -> _bStAllRedToEW

NETWORK Decode GreenEW
    [_eState = E_IntersectionState.GreenEW] -> _bStGreenEW

NETWORK Decode YellowEW
    [_eState = E_IntersectionState.YellowEW] -> _bStYellowEW

NETWORK Decode Faulted
    [_eState = E_IntersectionState.Faulted] -> _bStFaulted

// ===== 3. On change: entry actions of the new state =====
NETWORK State changed
    [_eState <> _eLastState] -> _bStateChanged

NETWORK Entry all-red
    _bStateChanged (_bStAllRedToNS | _bStAllRedToEW) -> _tStepTime := ALL_RED_TIME

NETWORK Entry green
    _bStateChanged (_bStGreenNS | _bStGreenEW) -> _tStepTime := GREEN_TIME

NETWORK Entry yellow
    _bStateChanged (_bStYellowNS | _bStYellowEW) -> _tStepTime := YELLOW_TIME

NETWORK Remember state
    -> _eLastState := _eState

// ===== 4. Cyclic: sub-FB calls, then outputs last =====
NETWORK Step timer
// Off for the change scan, so it restarts in every new step
    /_bStateChanged _fbStepTimer(PT := _tStepTime)

NETWORK Flash lit phase ends
// Two timers take turns; each one's Q flips the phase
    _bFlashOn _fbFlashLit(PT := FLASH_HALF_TIME) -> R:_bFlashOn

NETWORK Flash dark phase ends
    /_bFlashOn _fbFlashOff(PT := FLASH_HALF_TIME) -> S:_bFlashOn

NETWORK Out bRedNS
    (_bStAllRedToNS | _bStAllRedToEW | _bStGreenEW | _bStYellowEW | _bStFaulted _bFlashOn) -> bRedNS

NETWORK Out bYellowNS
    _bStYellowNS -> bYellowNS

NETWORK Out bGreenNS
    _bStGreenNS -> bGreenNS

NETWORK Out bRedEW
    (_bStAllRedToNS | _bStGreenNS | _bStYellowNS | _bStAllRedToEW | _bStFaulted _bFlashOn) -> bRedEW

NETWORK Out bYellowEW
    _bStYellowEW -> bYellowEW

NETWORK Out bGreenEW
    _bStGreenEW -> bGreenEW

NETWORK Out copies
    -> eState := _eState
END_FUNCTION_BLOCK
