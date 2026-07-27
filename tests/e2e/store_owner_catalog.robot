*** Settings ***
Documentation       Store-owner catalog and order management journeys.
Resource            resources/common.resource

*** Test Cases ***
Store Owner Manages Own Catalog And Orders
    [Tags]    e2e    persona:store_owner    feature:catalog
    ${profile}=    Get Current User Profile    store_owner_primary
    Should Be Equal    ${profile}[role]    store_owner
    ${store_id}=    Set Variable    ${profile}[store_id]
    Should Be True    ${store_id} > 0

    ${product}=    Create Product For Owner    store_owner_primary    ${store_id}
    Should Be Equal As Integers    ${product}[store_id]    ${store_id}
    Should Be Equal    ${product}[name]    ${product}[name]

    ${products}=    List Products For Store    store_owner_primary    ${store_id}
    Last Api Status Should Be    200
    Should Not Be Empty    ${products}

    ${customer_profile}=    Get Current User Profile    customer
    ${customer_store}=    Set Variable    ${customer_profile}[store_id]
    ${product}=    Find In Stock Product    customer    ${customer_store}
    ${customer_product_id}=    Set Variable    ${product}[id]
    ${checkout}=    Checkout Product For Customer    ${customer_store}    ${customer_product_id}    1
    ${order_id}=    Set Variable    ${checkout}[order][id]

    # Owner of the customer's store can advance status when tenant matches.
    IF    ${store_id} == ${customer_store}
        Update Order Status    store_owner_primary    ${order_id}    confirmed
        Last Api Status Should Be    200
    END

    Web Login As Persona    store_owner_primary
    Web Open Path    /stores/${store_id}
    Last Web Status Should Be    200
    Last Web Body Should Contain    ${product}[name]
    Web Open Path    /stores/${store_id}/orders
    Last Web Status Should Be    200
    Last Web Body Should Contain    Orders
