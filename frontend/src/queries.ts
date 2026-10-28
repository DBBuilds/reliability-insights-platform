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
export const ORG_METRICS = graphql(`
  query OrgMetrics($orgId: ID!, $start: Date!, $end: Date!) {
    orgMetrics(orgId: $orgId, start: $start, end: $end) {
      orgId
      start
      end
      staleSources
      incidents {
        total
        open
        timeToDetect {
          sampleSize
          medianMinutes
        }
        timeToResolve {
          sampleSize
          medianMinutes
          p90Minutes
        }
        weekly {
          weekStart
          count
          partial
        }
      }
      delivery {
        deploys
        changeFailureRate
      }
      onCall {
        pages
        offHoursPages
        actionableShare
        noisiestAlerts {
          alertName
          pages
        }
      }
      support {
        requests
        resolutionRate
        firstResponse {
          sampleSize
          medianMinutes
        }
      }
      insights {
        id
        level
        title
        detail
      }
    }
  }
`);
