# Cognito Authentication Setup

## Overview

This project uses AWS Cognito for authentication and authorization.

The authentication system supports:

* User sign-up
* User login
* Email verification
* Hosted UI authentication
* OAuth 2.0 authorization code flow

## AWS Cognito Configuration

### User Pool

* Region: ap-southeast-2
* Authentication method: Email
* Self-registration: Enabled

### Required Attributes

* email
* given_name
* family_name

### OAuth Configuration

* Grant type: Authorization code grant
* Callback URL: http://localhost:3000

### OpenID Scopes

* openid
* email
* profile

## Hosted UI

A Cognito Hosted UI login page was configured and tested successfully.

## Planned API Protection

The following APIs will be protected using Cognito Authorizer in API Gateway:

* Upload API
* Query API
* Delete API
* Manual Tag API

## Contribution

Configured and tested:

* Cognito User Pool
* Hosted UI
* OAuth login flow

## API Gateway Authorization Setup

An HTTP API was created in AWS API Gateway.

### API Configuration
- API name: AussieEcoLens-API
- Region: ap-southeast-2
- Stage: $default
- Auto-deploy: Enabled

### Routes Created
- POST /upload
- POST /query
- POST /tags
- DELETE /file

### JWT Authorizer
A JWT authorizer named `CognitoAuthorizer` was created and connected to the Cognito User Pool.

Protected routes:
- POST /upload
- POST /query
- POST /tags
- DELETE /file

### Current Status
The API Gateway authentication layer has been configured.  
The next step is to connect the routes to Lambda integrations so the API can invoke backend functions.
* Email verification workflow
