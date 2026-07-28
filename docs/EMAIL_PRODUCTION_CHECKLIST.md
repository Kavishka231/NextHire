# Production email verification

Do not deploy with the SMTP password previously exposed in chat. Revoke it in
Brevo, create a replacement credential, and store the replacement only in the
hosting platform's encrypted secret manager. Never place it in `.env.example`,
GitHub variables, workflow files, images, logs, tickets, or documentation.

## Provider and DNS

1. Use a domain owned by the organization. A Gmail address cannot be
   authenticated as a sending domain.
2. In Brevo, add and authenticate the sending domain.
3. Publish the exact Brevo code and DKIM records shown for that account.
4. Publish one DMARC TXT record. Begin with reporting (`p=none`) and a monitored
   aggregate-report mailbox, then move to `quarantine` or `reject` after valid
   mail consistently aligns.
5. Review the existing SPF record before changing it. A domain must not have
   multiple SPF records; merge provider includes when required.
6. Wait for DNS propagation and require Brevo to show the domain and sender as
   authenticated before enabling production email.

Production secrets:

```env
MAIL_SERVER=smtp-relay.brevo.com
MAIL_PORT=587
MAIL_USERNAME=<replacement Brevo SMTP login>
MAIL_PASSWORD=<replacement secret from the secret manager>
MAIL_FROM=noreply@your-domain.example
MAIL_FROM_NAME=NextHire
```

## Release verification

Use dedicated test candidate, company, administrator, and recipient accounts.
Do not use real customer addresses for release testing.

Verify each flow:

1. Request a password reset and confirm the email arrives, the public HTTPS link
   uses the deployed domain, the token expires, and it cannot be reused.
2. Create an application that qualifies for a reminder, run the reminder task,
   and confirm one correctly rendered message arrives.
3. Send an individual admin email and confirm the Celery task succeeds.
4. Send a broadcast only to a small test audience and confirm the reported
   recipient, success, and failure counts.
5. Check API, worker, and scheduler logs. They must not contain addresses,
   passwords, SMTP credentials, reset tokens, refresh tokens, or message bodies.

## Delivery monitoring

- Review Brevo transactional reports and logs for delivered, hard bounce, soft
  bounce, blocked, and complaint events.
- Configure a Brevo transactional webhook or provider alerting for bounce,
  blocked, and complaint events before opening registration.
- Alert on a material delivery-rate drop or an unusual bounce/complaint rise.
- Keep hard-bounced and complained addresses suppressed. Do not repeatedly
  retry permanent failures.
- Define transactional-log retention according to the privacy policy and limit
  access to authorized operators.

Record the credential rotation date, authenticated domain, DNS verification
date, test message IDs, observed results, and approving operator in the release
record. Do not record the credential value.
