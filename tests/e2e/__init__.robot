*** Settings ***
Documentation       E2E suite root: require a healthy seeded API + web stack.
Resource            resources/common.resource
Suite Setup         Stack Must Be Healthy
