###### Endpoint list
###### Request examples
###### Response examples
###### Authentication methods
###### Error codes

---

--- 
# AUTH

---
### POST `{{BASE_URL}}/auth/signup/`
- Used for signing up.
- Request:
  ```
  - email
  - password
  - username
  ```
- Response:
  ```
  - refresh token
  - access token
  ```
  
---
### POST `{{BASE_URL}}/auth/login/`
- Used for login.
- Request:
  ```
  - email
  - password
  ```
- Response:
  ```
  - refresh token
  - access token
  ```

---
### GET/PUT/PATCH `{{BASE_URL}}/profile/<user_id>/`
- Details about the user.
- Additionally, let user update their own profile.
- Request:
  ```
  - 
  ```
- Response:
  ```
  - 
  ```

---

---
# LANDING PAGE (Ignore as will be managed via vercel instead of render)

---
### GET `{{BASE_URL}}/` - '.app'
- React based landing page about conclave.
- Responses with React page.
- Deployed on vercel, and not on render to overcome at least coldstart problem on frontend.
- Basically ignore this here.

---

---
# TENANT OPERATIONS FROM HOMEPAGE (i.e., with no subdomain)

---
### GET `{{BASE_URL}}/tenant/`
- Returns list of all available tenants.
- Response:
  ```
  - 
  ```
  
---
### POST `{{BASE_URL}}/tenant/`
- Let user create a new tenant.
- Request:
  ```
  -
  ```
- Response:
  ```
  - 
  ```
  
---

---
# TENANT SPECIFIC OPERATIONS (i.e., with subdomain)

---
### GET `*.{{BASE_URL}}/`
- Details for specified tenant.
- Response:
  ```
  - 
  ```
  
---
### PUT/PATCH `*.{{BASE_URL}}/settings/`
- See/Update specified tenant.
- Only if it is user who created tenant.
- Request:
  ```
  - 
  ```
- Response:
  ```
  - 
  ```

---

---
# INVITES/REQUESTS SYSTEM

---
### POST `*.{{BASE_URL}}/invite/`
- Invite user to specific tenant.
- Only if it is user who created tenant.
- Request:
  ```
  - 
  ```
- Response:
  ```
  - 
  ```
  
---
### GET `*.{{BASE_URL}}/invitations/`
- List of invited users to that specific tenant.
- Only if it is user who created tenant.
- Request:
  ```
  - 
  ```
- Response:
  ```
  - 
  ```
  
---
### POST `*.{{BASE_URL}}/invitations/{id}/`
- Accept/Reject invitation.
- Tenant owner only.
- Request:
  ```
  - 
  ```
- Response:
  ```
  - 
  ```
  
---
### POST `*.{{BASE_URL}}/request/`
- Send request to join specific tenant.
- Request:
  ```
  - 
  ```
- Response:
  ```
  - 
  ```
  
---
### GET `*.{{BASE_URL}}/requested/`
- List of tenants to whom join request is sent.
- Response:
  ```
  - 
  ```
  
---
### GET `*.{{BASE_URL}}/requests/`
- List of users who have sent request to join tenants.
- Tenant owner only.
- Response:
  ```
  - 
  ```
  
---
### POST `*.{{BASE_URL}}/requests/{id}/`
- Accept/Reject request.
- Tenant owner only.
- Request:
  ```
  - 
  ```
- Response:
  ```
  - 
  ```
  
---