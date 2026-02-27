mtype = { DCCP_REQUEST, 
          DCCP_RESPONSE, 
          DCCP_DATA, 
          DCCP_ACK, 
          DCCP_DATAACK, 
          DCCP_CLOSEREQ, 
          DCCP_CLOSE, 
          DCCP_RESET,
          DCCP_SYNC,
          DCCP_SYNCACK };

chan AtoN = [1] of { mtype };
chan NtoA = [1] of { mtype };  /* 改为缓冲通道 */
chan BtoN = [1] of { mtype };
chan NtoB = [1] of { mtype };  /* 改为缓冲通道 */

int state[2];
int before_state[2];

#define ClosedState    0
#define ListenState    1
#define RequestState   2
#define RespondState   3
#define PartOpenState  4
#define OpenState      5
#define CloseReqState  6
#define ClosingState   7
#define TimeWaitState  8

#define StableState    9
#define ChangingState  10
#define UnstableState  11
#define EndState       -1

#define leftClosed       (state[0] == ClosedState)
#define rightEstablished (state[1] == OpenState)

#define leftListen   (state[0] == ListenState)
#define leftTimeWait (state[0] == TimeWaitState)
#define leftRespond  (state[0] == RespondState)
#define leftLTR      (leftListen || leftTimeWait || leftRespond)
#define leftTR       (              leftTimeWait || leftRespond)

/* 网络进程 - 转发消息*/
proctype Network() {
    mtype msg;
    do
    :: AtoN ?  msg -> 
       if
       :: NtoB !  msg;  /* 正常转发 */
       fi
    :: BtoN ? msg -> 
       if
       :: NtoA ! msg;  /* 正常转发 */
       fi
    od
}

proctype DCCP(chan snd, rcv; int i) {
    bool I_am_active;
CLOSED:
    I_am_active = false;
    before_state[i] = state[i];
    state[i] = ClosedState;
    if
    ::  goto LISTEN; /* passive open */
    ::  snd ! DCCP_REQUEST;  /* active  open */ 
       goto REQUEST; 
    fi
LISTEN:
    before_state[i] = state[i];
    state[i] = ListenState;
    if
    :: rcv ? DCCP_REQUEST -> /* rcv request  */
       snd ! DCCP_RESPONSE; /* snd response */ 
       goto RESPOND;
    :: timeout -> goto CLOSED;
    fi
/* ...  其余 DCCP 进程代码保持不变 ...  */
REQUEST:
    I_am_active = true;
    before_state[i] = state[i];
    state[i] = RequestState;
    if
    :: rcv ? DCCP_RESPONSE -> 
       snd ! DCCP_ACK;
       goto PARTOPEN;
    ::  rcv ? DCCP_RESET -> goto CLOSED;
    :: rcv ?  DCCP_SYNC -> snd ! DCCP_RESET; goto CLOSED;
    :: timeout -> goto CLOSED;
    fi
RESPOND:
    I_am_active = false;
    before_state[i] = state[i];
    state[i] = RespondState;
    do
    :: rcv ? DCCP_ACK     -> goto OPEN;
    :: rcv ? DCCP_DATAACK -> goto OPEN; 
    :: timeout -> 
        if
        :: snd ! DCCP_RESET;
        :: skip;
        fi
        goto CLOSED;
    ::  snd ! DCCP_DATA;
    od
PARTOPEN: 
    before_state[i] = state[i];
    state[i] = PartOpenState;
    do
    ::  rcv ? DCCP_DATA;    snd ! DCCP_ACK; goto OPEN;
    :: rcv ?  DCCP_DATAACK; snd ! DCCP_ACK; goto OPEN;
    ::  snd ! DCCP_DATAACK;
    ::  timeout -> goto CLOSED;
    ::  rcv ? DCCP_CLOSEREQ -> snd ! DCCP_CLOSE; goto CLOSING;
    :: rcv ?  DCCP_CLOSE    -> snd !  DCCP_RESET; goto CLOSED;
    :: rcv ? DCCP_ACK      -> goto OPEN;
    od
OPEN:
    before_state[i] = state[i];
    state[i] = OpenState;
    do
    :: snd !  DCCP_DATA;
    :: snd ! DCCP_DATAACK;
    :: rcv ?  DCCP_ACK;
    ::  rcv ? DCCP_DATA;
    :: rcv ?  DCCP_DATAACK;
    ::  I_am_active == true -> 
       snd ! DCCP_CLOSEREQ;
       goto CLOSEREQ;
    ::  rcv ? DCCP_CLOSE ->
       snd !  DCCP_RESET;
       goto CLOSED;
    :: I_am_active == true ->
       snd ! DCCP_CLOSE;
       goto CLOSING;
    :: rcv ? DCCP_CLOSEREQ ->
       snd !  DCCP_CLOSE;
       goto CLOSING;
    :: goto CLOSED;
    od
CLOSEREQ:
    before_state[i] = state[i];
    state[i] = CloseReqState;
    rcv ? DCCP_CLOSE;
    snd ! DCCP_RESET;
    goto CLOSED;
CLOSING: 
    before_state[i] = state[i];
    state[i] = ClosingState;
    if
    ::  rcv ? DCCP_RESET ->
       goto TIMEWAIT;
    :: timeout -> goto CLOSED;
    fi
TIMEWAIT:
    before_state[i] = state[i];
    state[i] = TimeWaitState;
    skip;
    goto CLOSED;
}

init {
    state[0] = ClosedState;
    state[1] = ClosedState;
    before_state[0] = ClosedState;
    before_state[1] = ClosedState;
    run Network();              /* 启动网络进程 */
    run DCCP(AtoN, NtoA, 0);
    run DCCP(BtoN, NtoB, 1);
}
