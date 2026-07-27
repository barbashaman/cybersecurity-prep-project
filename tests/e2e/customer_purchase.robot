*** Settings ***
Documentation       Customer purchase lifecycle across API checkout and web catalog.
Resource            resources/common.resource

*** Test Cases ***
Customer Completes Purchase Lifecycle
    [Tags]    e2e    persona:customer    feature:checkout
    ${profile}=    Get Current User Profile    customer
    Should Be Equal    ${profile}[role]    customer
    ${store_id}=    Set Variable    ${profile}[store_id]
    Should Be True    ${store_id} > 0

    ${products}=    List Products For Store    customer    ${store_id}
    Last Api Status Should Be    200
    Should Not Be Empty    ${products}
    ${product}=    Find In Stock Product    customer    ${store_id}
    ${product_id}=    Set Variable    ${product}[id]

    Get Shipping Quote    customer
    Last Api Status Should Be    200

    ${checkout}=    Checkout Product For Customer    ${store_id}    ${product_id}    1
    Should Be Equal As Integers    ${checkout}[order][store_id]    ${store_id}
    ${order_id}=    Set Variable    ${checkout}[order][id]
    ${order_marker}=    Catenate    SEPARATOR=    \#    ${order_id}

    ${orders}=    Api Get    /api/v1/stores/${store_id}/orders    customer
    Last Api Status Should Be    200
    Should Not Be Empty    ${orders}

    Web Login As Persona    customer
    Last Web Status Should Be    200
    Last Web Body Should Contain    Stores
    Web Open Path    /stores/${store_id}
    Last Web Status Should Be    200
    Last Web Body Should Contain    Product catalog
    Web Open Path    /stores/${store_id}/orders
    Last Web Status Should Be    200
    Last Web Body Should Contain    ${order_marker}
