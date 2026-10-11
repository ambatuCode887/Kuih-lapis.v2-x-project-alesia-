# Credential Stuffing

Credential stuffing is an attack where criminals use leaked usernames and passwords
from one service to access accounts on another service.

## Prevention

Use multi-factor authentication, rate limiting, breached-password detection,
strong password policies, and monitoring for unusual login activity.

## How It Works

Attackers obtain username and password pairs exposed in data breaches, then try
those same pairs on other services. The attack relies on password reuse, not on
guessing every possible password. Login attempts may be automated and spread
across many IP addresses or devices to avoid simple per-address limits.

Credential stuffing is different from brute force: brute force repeatedly
guesses passwords for an account, while credential stuffing tests credentials
already known or stolen from another source.

## Warning Signs

- A sudden increase in failed sign-ins, especially across many accounts.
- Many accounts receiving one or a few login attempts from changing IPs or
  device fingerprints.
- Unusual login successes following repeated failures, or successful sign-ins
  from unfamiliar locations or devices.
- New account changes shortly after an unfamiliar sign-in, such as a changed
  recovery address, payment method, or password.

Treat these signals as indicators for investigation rather than proof by
themselves. Shared networks, travel, and legitimate device changes can also
produce unusual sign-in patterns.

## Defensive Controls

- Require multi-factor authentication, preferably phishing-resistant methods
  such as passkeys or security keys for higher-risk accounts.
- Block known-compromised passwords during sign-up and password changes. Do not
  tell users which breached password matched.
- Apply rate limits and risk-based challenges across accounts, IP ranges,
  devices, and sessions. Avoid relying on IP blocking alone, since attacks can
  be distributed and shared networks can contain legitimate users.
- Detect automation and unusual login patterns, while keeping challenges
  accessible to people using assistive technology.
- Alert on suspicious sign-in spikes and review authentication logs for both
  failed attempts and unexpected successes.
- Use unique passwords for every service, stored in a reputable password
  manager, and secure account recovery methods.

## Response to Suspected Activity

1. Use trusted administrative tools to contain the affected sign-in activity
   and protect accounts showing suspicious successful access.
2. Revoke active sessions and tokens for confirmed or high-risk compromised
   accounts, and require a password reset through the service's trusted flow.
3. Review sign-in and account-change logs for unauthorized recovery changes,
   data access, or transactions; preserve relevant evidence.
4. Notify affected users through a verified channel. Never ask them to send a
   password, one-time code, or recovery secret in a message.
5. Investigate the source and scope, then tune detection and controls without
   unnecessarily locking out legitimate users.

## Advice for Account Holders

If you suspect an account was accessed, open the service using its official app
or a known address, change the password to a new unique one, enable multi-factor
authentication, and sign out other sessions if the service offers that option.
Review recovery details and recent activity. If you reused that password on
other services, change it there too. Do not follow password-reset links in
unexpected messages; navigate to the service directly.
