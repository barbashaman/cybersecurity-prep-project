*** Settings ***
Documentation       Delivery-manager privacy-safe order visibility journeys.
Resource            resources/common.resource

*** Test Cases ***
Delivery Manager Sees Anonymized Orders Only
    [Tags]    e2e    persona:delivery_manager    feature:orders
    ${customer}=    Get Current User Profile    customer
    ${store_id}=    Set Variable    ${customer}[store_id]
    ${product}=    Find In Stock Product    customer    ${store_id}
    ${product_id}=    Set Variable    ${product}[id]
    ${checkout}=    Checkout Product For Customer    ${store_id}    ${product_id}    1
    ${order_id}=    Set Variable    ${checkout}[order][id]
    ${customer_email}=    Set Variable    ${customer}[email]
    ${order_marker}=    Catenate    SEPARATOR=    \#    ${order_id}

    ${orders}=    Api Get    /api/v1/stores/${store_id}/orders    delivery_manager
    Last Api Status Should Be    200
    Should Not Be Empty    ${orders}
    Last Api Body Should Not Contain    customer_email
    Last Api Body Should Not Contain    shipping_address
    Last Api Body Should Not Contain    ${customer_email}

    Get Shipping Quote    delivery_manager
    Last Api Status Should Be    403

    Api Post    /api/v1/stores/${store_id}/orders/checkout    delivery_manager
    ...    {"lines":[{"product_id":${product_id},"quantity":1}],"shipping_address":"denied"}
    Last Api Status Should Be    403

    Web Login As Persona    delivery_manager
    Web Open Path    /stores/${store_id}/orders
    Last Web Status Should Be    200
    Last Web Body Should Contain    (anonymized)
    Last Web Body Should Contain    ${order_marker}
    Last Web Body Should Not Contain    ${customer_email}
