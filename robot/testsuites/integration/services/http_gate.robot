*** Settings ***
Variables   ../../../variables/common.py


Library     ../${RESOURCES}/neofs.py
Library     ../${RESOURCES}/payment_neogo.py
Library     ../${RESOURCES}/gates.py


*** Test cases ***

NeoFS HTTP Gateway 
    [Documentation]     Creates container and does PUT, GET via HTTP Gate
    [Timeout]           5 min

    ${WALLET} =         Init wallet
                        Generate wallet         ${WALLET}
    ${ADDR} =           Dump Address            ${WALLET}
    ${PRIV_KEY} =       Dump PrivKey            ${WALLET}              ${ADDR}
    ${TX} =             Transfer Mainnet Gas    wallets/wallet.json    NTrezR3C4X8aMLVg7vozt5wguyNfFhwuFx    ${ADDR}    6

                        Wait Until Keyword Succeeds         1 min      15 sec        
                        ...  Transaction accepted in block  ${TX}
                        Get Transaction                     ${TX}
                        Expected Mainnet Balance            ${ADDR}    6

    ${SCRIPT_HASH} =    Get ScriptHash                       ${PRIV_KEY}  

    ${TX_DEPOSIT} =     NeoFS Deposit                       ${WALLET}    ${ADDR}    ${SCRIPT_HASH}    5     
                        Wait Until Keyword Succeeds         1 min        15 sec
                        ...  Transaction accepted in block  ${TX_DEPOSIT}
                        Get Transaction                     ${TX_DEPOSIT}

    ${CID} =            Create container                    ${PRIV_KEY}    public    REP 1 IN X CBF 1 SELECT 1 FROM * AS X
                        Wait Until Keyword Succeeds         2 min          30 sec
                        ...  Container Existing             ${PRIV_KEY}    ${CID}

    ${FILE} =           Generate file of bytes              1024
    ${FILE_L} =         Generate file of bytes              70e+6
    ${FILE_HASH} =      Get file hash                       ${FILE}
    ${FILE_L_HASH} =    Get file hash                       ${FILE_L}

    ${S_OID} =          Put object                 ${PRIV_KEY}    ${FILE}      ${CID}    ${EMPTY}    ${EMPTY}       
    ${L_OID} =          Put object                 ${PRIV_KEY}    ${FILE_L}    ${CID}    ${EMPTY}    ${EMPTY}     
  
    # By request from Service team - try to GET object from the node without object

    @{GET_NODE_LIST} =  Get nodes without object            ${PRIV_KEY}    ${CID}    ${S_OID}
    ${NODE} =           Evaluate                            random.choice($GET_NODE_LIST)    random

                        Get object               ${PRIV_KEY}    ${CID}    ${S_OID}    ${EMPTY}    s_file_read    ${NODE}
    ${FILEPATH} =       Get via HTTP Gate                   ${CID}         ${S_OID}

                        Verify file hash                    s_file_read    ${FILE_HASH} 
                        Verify file hash                    ${FILEPATH}    ${FILE_HASH} 

    @{GET_NODE_LIST} =  Get nodes without object            ${PRIV_KEY}    ${CID}    ${L_OID}
    ${NODE} =           Evaluate                            random.choice($GET_NODE_LIST)    random

                        Get object               ${PRIV_KEY}    ${CID}    ${L_OID}    ${EMPTY}    l_file_read    ${NODE}
    ${FILEPATH} =       Get via HTTP Gate                   ${CID}         ${L_OID}

                        Verify file hash                    l_file_read    ${FILE_L_HASH} 
                        Verify file hash                    ${FILEPATH}    ${FILE_L_HASH} 

    [Teardown]          Cleanup                             ${FILEPATH}    ${FILE}    



*** Keywords ***

Cleanup
    [Arguments]             ${FILEPATH}        ${FILE}
                            Cleanup Files      ${FILEPATH}    ${FILE}    s_file_read    l_file_read
                            Get Docker Logs    http_gate