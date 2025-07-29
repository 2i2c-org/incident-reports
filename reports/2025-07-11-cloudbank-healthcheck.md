# Incident report July 11 2025 - CloudBank health check fail plus GroupExporter pod restarts
 
 
## Summary
 
After a PR from the community, the 2i2c team saw an alert for Cloudbank showing a failed health check and groups-exporter pods restarting.

## Resolution

Rolling back the PR did not resolve the issue, nor did restarts; disabling Jupyterhub configurator did.


## What went well
Most of the hubs weren't in active use across 50ish community colleges. While the incident took a few hours to resolve, there was no perceivable outage/downtime for users.
Collaboration with community technical contact & bumpy but ultimately prompt resolution of the issue.

## What Didn't Go So Well?
We had one engineer working, both to triage and resolve the issue that started in her late afternoon. Other engineers were out or at a conference in PDT time zone - they were able to offer remote guidance, but the staffing gap delayed our progress.



## Timeline (times in BST)

### July 11, 2025, 12:42 PM
Incident declared
> Description: An uptime check on two-eye-two-see Uptime Check URL labels {project_id=two-eye-two-see, host=santiago.cloudbank.2i2c.cloud} is failing. | Violation started: July 11, 2025 at 4:42PM UTC (less than 1 sec ago) | Policy: santiago.cloudbank.2i2c.cloud on cloudbank | Condition: Simple Health Check Endpoint | View incident: https://console.cloud.google.com/monitoring/alerting/alerts/0.nunch3tjib61?channelType=pagerduty&project=two-eye-two-see (View Message)

### 12:49 PM
PR that triggered the alerts reverted: <https://github.com/2i2c-org/infrastructure/pull/6349>
CloudBank health check fail plus GroupExporter pod restarts.

### 1:06 PM
- Hub admin updates the `jupyterhub.singleuser.image` config in the `common.values.yaml` for CloudBank.
- Engineer notices a bunch of gha-failures, logs into a cloudbank hub to check everything is okay and succeeds.
- Engineer notices PagerDuty alerts for health-check failures come in.
- Engineer tries to log into other hubs and met with `Service unavailable`.
- Engineer decides to revert the PR and communicates this to hub admin.
- PR revert did not solve the root cause of the problem.
- Hubs remain inaccessible with `Service unavailable`.

### 1:27 PM
Tech Lead enters the chat, at a conference without a laptop, suspects the hub pods are dead.

### 1:29 PM
Engineer attempts hub pod restarts.

### 1:35 PM
Tech Lead's hypothesis is that all the hub pods restarting maxes out something on the core nodes.

### 1:36 PM
To test, engineer deletes one of the hub pods now to see if it comes back.

### 1:38 PM
It does.

### 1:38 PM
Engineer does the same for the other hubs in the cluster, with time gaps in between.

### 1:42 PM
Tech Lead notes we still need to actually fix the underlying cause.

### 2:35 PM
Engineer notes "am a fair way through restarting hub pods and they are not having the intended effect".
Tries logging into various Cloudbank hubs but still met with `Service unavailable.`

Engineer hands off to Tech Lead with a note:
> P.S I think the hub pod is fine, it could be the proxy pod.

### 3:34 PM
Tech Lead runs `k get pod -A | grep -v Running | choose 0 | sort | uniq | x`.

### 4:06 PM
Tech Lead believes that https://github.com/2i2c-org/infrastructure/pull/6352 fixed it, and re-deploys the original PR.

### 4:22 PM
Incident resolved and communicated to hub admin.

### July 14, 2025, 11:20 AM
Engineer finishes resolving the overall incident in PagerDuty by restarting all the groups-exporter pods (see private pagerduty channel) and opens <https://github.com/2i2c-org/infrastructure/issues/6358> for the <https://team-compass.2i2c.org/projects/managed-hubs/incidents/#create-an-incident-report>.


## Action Items

- [ ] Write an incident report
- [ ] https://github.com/2i2c-org/infrastructure/issues/6477


