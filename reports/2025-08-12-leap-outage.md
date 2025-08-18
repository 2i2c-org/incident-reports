# Incident report August 12 2025 - LEAP hub outage

## Summary
On August 12 2025, a 2i2c engineer unintentionally deleted the `prod` namespace for the LEAP deployment whilst working on separate (new) hub. As a consequence of this action, all pods running in the `prod` namespace were terminated, and the hub rendered entirely inaccessible for ~1hr. 

The root cause for this incident is a bug in our NFS deployment process. Working around this bug led to this incident. 

## Resolution
A single remaining user-pod was deleted in the `prod` namespace, finalising the `kubectl namespace delete` operation. Subsequently re-deploying the `prod` hub was successful. No data were lost.

## What went well
The engineer that triggered the incident was quick to identify the situation ahead of the hub's monitoring alerts declaring an issue. A second engineer was pulled in early to support communication with the LEAP community whilst the first engineer identified the remedial action to take.

2i2c already designed against loss of k8s resources by provisioning persistent storage separately using Terraform. The survival of user data demonstrates the pay-off of this design against failure.

## What didn't go so well?
Although the primary engineer was able to identify the necessary remedial action, they did not feel confident to re-deploy the `prod` hub without speaking to the tech lead to confirm that there were no additional risks to consider, such as persistent data loss. Establishing communication with the tech lead (in a different timezone) took some time.

Redeploying the hub took additional minutes as a consequence of a circular dependency between the deployment of jupyterhub-home-nfs and consuming the NFS server IP in the PVCs. This is sometimes blocked by the `nfs-share-creator` job, which [2i2c intends to replace](https://github.com/2i2c-org/infrastructure/issues/5560).

The primary engineer did not have any contextual clues that they'd switched onto the LEAP hub, leading to the incident.

## Timeline (times in BST)

### 5:00 PM
Incident declared
> Hey all. I was deploying the new temple cluster, and ran into some NFS issues.
I deleted the prod namespace, when it hung. I listed the pods and found a load of users from a different cluster. I think my kubeconfig has somehow been mutated / corrupted and some other cluster is currently being torn down.
Creating this incident whilst I figure out what's happened.

### 5:02 PM
Engineer updates the incident channel with clarification of the affected hub
> OK, the cluster is LEAP, I'm confident -- no pods on prod :cry:

A second engineer joins a Huddle with the primary engineer.

### 5:15 PM
Second engineer updates LEAP community of an active outage.

### 5:32 PM
Uptime check on LEAP cluster fails
> An uptime check on two-eye-two-see Uptime Check URL labels {project_id=two-eye-two-see, host=leap.2i2c.cloud} is failing. | Violation started: Aug 12, 2025 at 4:32PM UTC (less than 1 sec ago) | Policy: leap.2i2c.cloud on leap | Condition: Simple Health Check Endpoint | View incident: https://console.cloud.google.com/monitoring/alerting/alerts/0.nvvomvjf6yo2?channelType=pagerduty&project=two-eye-two-see

Second engineer hands off to People Operations Lead to handle the communications responsibilities of the incident commander role.

### 5:33 PM
Primary engineer acknowledges that they would like to re-deploy `prod`, but are acting cautiously to avoid unnecessary data loss.

### 5:37 PM
First reports of users encountering 404 errors whilst accessing the hub arrive from Sarika de Bruyn.

### 5:43 PM
Tech lead confirms approach is to re-deploy `prod`, and encourages primary engineer to proceed.

### 5:48 PM
`nfs-share-creator` job is blocking deployment, the primary engineer kills the job.

### 5:51 PM
Primary engineer re-deploys `prod` with updated NFS server IP address.

### 5:55 PM 
Primary engineer deletes `prod` ingress to prevent users spawning mid-deployment.

### 6:08 PM
Primary engineer declares `prod` hub online, shares this update with the LEAP community, and continues testing.

### 6:11 PM
Incident resolved.

## Follow-up timeline (times in BST)

### 8:16 PM
Sarika de Bruyn reports that some userse are having trouble with logging in, or are experiencing kernel disconnections.

### 8:20 PM
Primary engineer acknowledges report.

### 8:37 PM
Primary engineer requests more information from Sarika.

### 9:03 PM
Sarika shares full-text of user reports.

### 9:16 PM
Primary engineer observes heavy Dask workloads being started (peaking at 200 dask *nodes* being provisioned), sees the workload ultimately stabilise, and reports back to Sarika.

## Action Items
- [ ] Write an incident report
- [ ] Write a small document for incident response [20m] e.g. "I deleted prod, what next?"
- [ ] Upgrade jupyterhub-home-nfs, and remove nfs-share-creator job (see https://github.com/2i2c-org/jupyterhub-home-nfs/pull/34).
- [x] Update `deployer` system to add opt-in hardening against nested kubeconfig contexts — https://github.com/2i2c-org/infrastructure/pull/6555
- [x] Update primary engineer's shell configuration to better identify distinct kubeconfig contexts.
