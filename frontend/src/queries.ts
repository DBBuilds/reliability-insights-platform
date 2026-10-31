import { graphql } from "./gql";

export const ORGS = graphql(`
  query Orgs {
    orgs {
      id
      name
      parentId
    }
  }
`);

// Select only fields that are live in PRODUCTION. A query naming a field the
// deployed backend doesn't have fails the whole operation.
// `previous` is the window of the same length just before, for the DORA tiles' change.
export const ORG_METRICS = graphql(`
  query OrgMetrics($orgId: ID!, $start: Date!, $end: Date!, $previousStart: Date!) {
    orgMetrics(orgId: $orgId, start: $start, end: $end) {
      orgId
      syncs {
        stream
        lastSyncedAt
        stale
      }
      insights {
        id
        level
        title
        detail
      }
      delivery {
        deploys
        changeFailureRate
        deployFrequency {
          value
          levels2024
        }
        leadTime {
          value
          levels2024
        }
        recoveryTime {
          value
          levels2024
        }
      }
      weekly {
        weekStart
        partial
        deploys
        changeFailureRate
        leadTime {
          medianMinutes
        }
        incidents
        timeToDetect {
          medianMinutes
        }
        timeToResolve {
          medianMinutes
          p90Minutes
        }
      }
      incidents {
        total
        open
        bySeverity {
          severity
          count
        }
        timeToResolve {
          medianMinutes
          p90Minutes
        }
      }
      recentIncidents(limit: 20) {
        id
        severity
        service
        title
        startedAt
        detectedAt
        resolvedAt
      }
      onCall {
        pages
        offHoursPages
        actionableShare
        noisiestAlerts {
          alertName
          pages
        }
        byHour {
          weekday
          hour
          pages
        }
      }
      slos {
        id
        service
        objective
        windowDays
        budgetRemaining
        burnRate1d
        burnRate3d
        status
        daily {
          day
          budgetRemaining
        }
      }
      support {
        requests
        resolutionRate
        firstResponse {
          medianMinutes
        }
      }
      children {
        orgId
        staleSources
        incidents {
          total
          open
          timeToResolve {
            medianMinutes
          }
        }
        delivery {
          deploys
          changeFailureRate
        }
        onCall {
          pages
          offHoursPages
        }
      }
    }
    previous: orgMetrics(orgId: $orgId, start: $previousStart, end: $start) {
      delivery {
        changeFailureRate
        deployFrequency {
          value
        }
        leadTime {
          value
        }
        recoveryTime {
          value
        }
      }
    }
  }
`);
