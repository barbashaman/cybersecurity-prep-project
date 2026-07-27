*** Settings ***
Documentation       E2E checks for security misconfiguration hardening (OWASP A02).
Resource            resources/common.resource

*** Test Cases ***
Web Responses Emit CSP And HSTS
    [Tags]    e2e    negative    owasp:a02    feature:misconfig
    Web Open Path    /login
    Last Web Status Should Be    200
    Last Web Header Should Match    content-security-policy    default-src 'self'
    Last Web Header Should Match    content-security-policy    object-src 'none'
    Last Web Header Should Match    strict-transport-security    max-age=

Web Session Cookie Is Marked Secure
    [Tags]    e2e    negative    owasp:a02    feature:misconfig
    ${cookie}=    Capture Web Login Set Cookie    customer
    Should Contain    ${cookie.lower()}    secure
    Should Contain    ${cookie.lower()}    httponly

Api Health Remains Public While Auth Stays Protected
    [Tags]    e2e    owasp:a02    feature:misconfig
    # Health is intentionally public for probes; authenticated surfaces stay locked down.
    ${health}=    Api Get    /health
    Last Api Status Should Be    200
    Should Be Equal    ${health}[status]    ok
    Api Get    /api/v1/admin/users
    Last Api Status Should Be    401
