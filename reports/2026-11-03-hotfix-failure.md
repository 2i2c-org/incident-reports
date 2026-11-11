# Incident report November 3 2026 - Hotfix failure

## Summary

A hotfix was applied to multiple clusters with the `skip-deploy` label applied. The fix was insufficiently validated with a manual deploy against the nasa-ghg-hub cluster the evening before, and subsequently applied in error across the network the morning after by an engineer. A decision was made to apply the skip-deploy label to avoid known CI/CD issues with the CloudBank cluster and, ironically, prevent disturbing workshop events scheduled for that day.

## Impact on community

Support tickets were raised by two communities, one of which was holding a workshop event:

- https://2i2c.freshdesk.com/a/tickets/6335
- https://2i2c.freshdesk.com/a/tickets/6336

## Contributing factors

The `nasa-ghg-hub` image was different from the `basehub` image, so the hotfix for this cluster did not apply to other clusters

The scheduled events prompted a decision to expedite deployment of the hotfix before the events started

However, network-wide CI/CD deployment was considered too risky just before an event, so the skip-deploy and manual approach was taken

Ironically, the deployment strategy taken above ended up causing outages across multiple hubs

## What went well

- PD alerts flagged the outage clearly and caught the attention of engineers within 10 minutes
- Reverting and rolling back the hotfix resolved the issue quickly
- The incident happened early enough in the day that the impact on communities in more western time zones was less

## What could be improved

This occurred when we knew workshop events were scheduled. Should we automatically "freeze" non-workshop-related configuration changes on hubs with events at least 24 hours before an event?

There are varying levels of mistrust in the network-wide CI/CD deployment pipeline, which can lead to inconsistent expectations between desired config and current state. Can we make some fundamental improvements to the CI/CD strategy so that deployments become trustworthy again?

The hotfix was applied to the usage quotas application, running as an internal JupyterHub service. This was a known weakness, and work to separate concerns was in progress.

## Timeline (UTC)

| Timestamp | Marker | Notes |
| --------- | ------ | ----- |
| 09:40 | Detect | Hotfix applied by Engineer 1. |
| 10:38 | Detect | `JupyterHub URL availability` alert fired and noticed by Engineer 2. |
| 10:49 | Diagnosis | Outage identified and PR to revert hotfix applied by Engineer 2. Infra manually stabilised by Engineer 1 with `helm rollback`. |
| 12:20 | Key moment | Incident declared over. |
| 13:06 | Repair | Hotfix removed from infra by Engineer 1. |

## Action items

- [ ] Align team practices on the use of the `skip-deploy` label
- [ ] Explore how we can improve CI/CD deployment strategy
- [ ] Follow through on separation of JupyterHub usage quotas dashboard into an external service in its own pod
- [ ] Propose a policy to "freeze" non-urgent changes to hub config prior to a workshop event
