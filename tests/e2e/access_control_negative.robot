*** Settings ***
Documentation       Negative E2E coverage for broken access control (OWASP A01).
Resource            resources/common.resource

*** Test Cases ***
Cross Tenant Catalog Access Is Denied
    [Tags]    e2e    negative    owasp:a01    feature:catalog
    ${owner}=    Get Current User Profile    store_owner_secondary
    ${owner_store}=    Set Variable    ${owner}[store_id]
    ${stores}=    List Stores For Persona    admin
    FOR    ${store}    IN    @{stores}
        IF    ${store}[id] != ${owner_store}
            ${foreign_id}=    Set Variable    ${store}[id]
            BREAK
        END
    END
    List Products For Store    store_owner_secondary    ${foreign_id}
    Last Api Status Should Be    403

    Web Login As Persona    store_owner_secondary
    Web Open Path    /stores/${foreign_id}
    Last Web Status Should Be    403

Customer Cannot Access Admin Directory
    [Tags]    e2e    negative    owasp:a01    feature:admin
    Api Get    /api/v1/admin/users    customer
    Last Api Status Should Be    403

Store Owner Cannot Place Checkout Order
    [Tags]    e2e    negative    owasp:a01    feature:checkout
    ${owner}=    Get Current User Profile    store_owner_primary
    ${store_id}=    Set Variable    ${owner}[store_id]
    ${products}=    List Products For Store    store_owner_primary    ${store_id}
    Last Api Status Should Be    200
    ${product_id}=    Set Variable    ${products}[0][id]
    Api Post    /api/v1/stores/${store_id}/orders/checkout    store_owner_primary
    ...    {"lines":[{"product_id":${product_id},"quantity":1}],"shipping_address":"owner-denied"}
    Last Api Status Should Be    403

Unauthenticated Api Access Is Rejected
    [Tags]    e2e    negative    owasp:a01    feature:auth
    Api Get    /api/v1/auth/me
    Last Api Status Should Be    401
