# Incident report May 12 2025 - Earthscope resource provisioning issue
 
 
## Summary
 
On May 12 2025 we received a Freshdesk support ticket about user's servers taking >15min to start and their kernels being killed. This was happening during a workshop and was also impacting other instructors trying to use the hub for different purposes.
 
Upon investigation we found out that profile option used during the workshop didn't have any memory limit set and the memory overcommitment was big. The node had 32GB of memory and the guarantee was 8GB and no limit was set. This was causing users' kernels to die.

## Resolution

Explicit memory limits were set to prevent users from evicting each other from a shared node when their memory usage spiked.

## Timeline

_All times in EEST_

## May 12

### 20:15

Ticket https://2i2c.freshdesk.com/a/tickets/3310 is opened about user's servers taking >15min to start and their kernels being killed

### 20:49

Ticket is brought to attention to the team via the [#support-freshdesk](https://2i2c.slack.com/archives/C028WU9PFBN/p1747072166510619) Slack channel

### 20:57
First engineer acknowledges the issue


### 20:59

Another report of the issue in [#business-development](https://2i2c.slack.com/archives/G015W2KSBCP/p1747072790080979) Slack channel received initially via text saying that the communiy was having major issues with their hub with a short course with ~30 users.

### 21:05

Engineer does a helm rollout and a hub redeploy which seems to have improved the situation

### 21:59
Community responds via Freshdesk that they are able to launch servers again but that things still hang. Course instructor will use a local python env for the rest of the day so the activity on the hub will decrease.

Community asks for some engineering capacity that can watch the infrastructure during the workshop that will happen in the following day.

### 22:00
Engineer reports the issue still persists:

```
tornado.web.HTTPError: HTTP 404: Not Found (Kernel does not exist
```

### 22:00
Engineer [shares logs](https://2i2c.slack.com/archives/C028WU9PFBN/p1747080050890899?thread_ts=1747072166.510619&cid=C028WU9PFBN) saved about the issue for the second engineer to look at.

### 23:00

Second engineer starts looking through the logs but not seing anything obviously wrong.

### 00:40

Second engineer conclusion is that there was nothing wrong with the hub, but a resource exhaustion issue.

However, https://grafana.earthscope.2i2c.cloud/d/a730e3a3d487abed/cluster-information?orgId=1&from=1747064147915&to=1747085747916&viewPanel=8 showed that the core node where the hub was running had a high CPU usage.

### 00:47

Second engineer asks about the resource needs for the workshop next day offering to pre-warm the cluster to make server start time faster

## May 13

### 14:30

The issue is identified as being the use of a "legacy profile option", one that was guarateeing a 8GB memory on a 32GB node but was setting no limit. When users consistently use more than the guaranteed amount, then other users' kernels get killed.

### 15:51

First engineer makes the "medium" profile available to the users so more users can share a machine.

### 16:00

Community is informed via freshdesk about the new profile option

### 17:00
The two engineers agree that they should not alter users' profile options so early before the workshop (to change available node shares and limits), so they decide to go with the "Medium" profile, increase the guarantee so that the memory overcommitment isn't that big and "pre-warm" the hub so that the users' won't wait that much for the nodes to come up

### 17:15
Second engineer makes 15 nodes available for a workshop of 30 users.

### 17:58

Community is informed about the changes made to the hub and guided how to use them.

### 19:28

Community confirms the workshop is running smoothly and asks for the medium profile to be made unavilable again after the workshop

### 19:31

Minimum nodegroup count is set to zero again to allow cluster scale down

### 20:21

Community confirms an uneventful workshop and asks for 20 nodes to be made available for the workshop on Sunday and an on-call engineer

## May 14

### 11:39AM

Earthscope home dir capacity is bumped reacting to pagerduty alert

### 17:15

Engineers discuss updating the community's profile options for the small nodes and setting up mem guarantee to equal mem limit. 
They deploy https://github.com/2i2c-org/infrastructure/pull/6047/files before the workshop

### 17:54

Community is informed about the changes

## 15 May

### 19:26

Community confirms the workshop on 14th worked great and asks for pre-warm and on call on Sunday https://2i2c.freshdesk.com/a/tickets/3319

A separate email thread to sync with the community is started, with an action to share findings from this incident with them. 

## 16 May

### 11:00 AM
Engineers agree to not update the current configuration further given everything worked as expected and not to pre-warm the cluster on a Sunday because of this.

## Action Items

- [ ] write an incident report
- [ ] hold an internal retrospective about the incident to learn from it https://github.com/2i2c-org/meta/issues/2194
  - https://github.com/2i2c-org/meta/issues/2217
  - https://github.com/2i2c-org/infrastructure/issues/6105
  - https://github.com/2i2c-org/infrastructure/issues/6106 
