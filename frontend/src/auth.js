import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserAttribute
} from 'amazon-cognito-identity-js'

const poolData = {
  UserPoolId: 'ap-southeast-2_cqBZusKHK',
  ClientId: '7ecsm8r3mtqomf6jvm3tp1t9ql'
}

const userPool = new CognitoUserPool(poolData)

// Sign up
export function signUp(email, password, firstName, lastName) {
  return new Promise((resolve, reject) => {
    const attributes = [
      new CognitoUserAttribute({ Name: 'email', Value: email }),
      new CognitoUserAttribute({ Name: 'given_name', Value: firstName }),
      new CognitoUserAttribute({ Name: 'family_name', Value: lastName })
    ]
    userPool.signUp(email, password, attributes, null, (err, result) => {
      if (err) reject(err)
      else resolve(result)
    })
  })
}

// Confirm sign up
export function confirmSignUp(email, code) {
  return new Promise((resolve, reject) => {
    const user = new CognitoUser({ Username: email, Pool: userPool })
    user.confirmRegistration(code, true, (err, result) => {
      if (err) reject(err)
      else resolve(result)
    })
  })
}

// Sign in
export function signIn(email, password) {
  return new Promise((resolve, reject) => {
    const user = new CognitoUser({ Username: email, Pool: userPool })
    const authDetails = new AuthenticationDetails({ Username: email, Password: password })
    user.authenticateUser(authDetails, {
      onSuccess: (result) => resolve(result),
      onFailure: (err) => reject(err)
    })
  })
}

// Sign out
export function signOut() {
  const user = userPool.getCurrentUser()
  if (user) user.signOut()
}

// Get current token
export function getToken() {
  return new Promise((resolve, reject) => {
    const user = userPool.getCurrentUser()
    if (!user) return reject('No user')
    user.getSession((err, session) => {
      if (err) reject(err)
      else resolve(session.getIdToken().getJwtToken())
    })
  })
}