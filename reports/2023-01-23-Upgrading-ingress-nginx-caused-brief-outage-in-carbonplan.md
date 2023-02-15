# 2023-01-23 Upgrading ingress-nginx caused brief outage in carbonplan

(This incident was originally tracked in https://github.com/2i2c-org/infrastructure/issues/2080)

### Summary

The CI/CD pipeline when merging a PR (#2067) upgrading the support chart's dependencies on `ingress-nginx`, `prometheus`, and `grafana` [failed like this](https://github.com/2i2c-org/infrastructure/actions/runs/3989923635). Among the failures I observed most of them related to a mundane failure to auth with GKE that by chance showed up now, but at least one was related to AWS - the carbonplan cluster.

In the carbonplan cluster, the staging and prod wasn't accessible so I reverted the version bump in #2079 which restored carbonplan but overall failed to deploy fully to other hubs as there was need for a patch commit still that was reverted.

#### GKE Auth issue

```
Unable to connect to the server: getting credentials: exec: executable gke-gcloud-auth-plugin not found

It looks like you are trying to use a client-go credential plugin that is not installed.

To learn more about this feature, consult the documentation available at:
      https://kubernetes.io/docs/reference/access-authn-authz/authentication/#client-go-credential-plugins

Install gke-gcloud-auth-plugin for use with kubectl by following https://cloud.google.com/blog/products/containers-kubernetes/kubectl-auth-changes-in-gke
```

#### Carbonplan issue

I'm very confident it relates to carbonplan being the one eksctl based AWS cluster that has k8s 1.19, while others have k8s 1.21 or higher. I assume the ingress-nginx chart has dropped support for so ancient versions, just like z2jh has already.

### Impact on users

I think only users of carbonplan was disrupted, and it seems nobody used it.

### Important information

- Hub URL: carbonplan.2i2c.cloud
- Support ticket ref: I saw this myself
