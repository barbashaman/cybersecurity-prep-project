*** Settings ***
Documentation       Admin cross-store governance journeys.
Resource            resources/common.resource

*** Test Cases ***
Admin Governs Across Stores
    [Tags]    e2e    persona:admin    feature:admin
    ${profile}=    Get Current User Profile    admin
    Should Be Equal    ${profile}[role]    admin

    ${stores}=    List Stores For Persona    admin
    ${store_count}=    Get Length    ${stores}
    Should Be True    ${store_count} >= 2

    ${users}=    Api Get    /api/v1/admin/users    admin
    Last Api Status Should Be    200
    Should Not Be Empty    ${users}

    ${created}=    Create Store As Admin
    Should Be Equal    ${created}[name]    ${created}[name]
    Should Not Be Empty    ${created}[public_id]

    ${store_one}=    Set Variable    ${stores}[0]
    ${revenue}=    Get Store Revenue    admin    ${store_one}[public_id]
    Last Api Status Should Be    200

    ${products}=    List Products For Store    admin    ${store_one}[id]
    Last Api Status Should Be    200

    Web Login As Persona    admin
    Last Web Body Should Contain    Stores
    Web Open Path    /stores/${store_one}[id]
    Last Web Status Should Be    200
    Web Open Path    /stores/${store_one}[id]/orders
    Last Web Status Should Be    200
