VAR_GLOBAL
    iState : INT;          // 0 Idle, 1 Filling, 2 Full, 3 Draining, 4 Faulted
    uiFault : UINT;        // 0 none, 1 overfill, 2 pump dry run
    bStart, bStop, bDrain, bReset, bPumpManual : BOOL;
    bPump, bValve, bHigh, bLow : BOOL;
    lrLevel, lrTemp, lrSetpoint : LREAL;
    uiFillCount : UINT;
END_VAR
