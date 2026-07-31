# Patch: two corrections to dashboardMetrics.json

## 1. Backlog series is missing June

The HR template's New Metrics block (row 32) reports June backlog at **17.15**. The series
currently ends at May. Append it, and note that Dec 2025 sits at the head of the window:

```diff
   "backlog": {
     "unit": "USD millions",
     "source": "Synechron HR Template Jun 26, New Metrics row 27",
     "series": [
-      { "month": "Dec", "value": 18.19 },
       { "month": "Jan", "value": 17.9 },
       { "month": "Feb", "value": 18.06 },
       { "month": "Mar", "value": 20.39 },
       { "month": "Apr", "value": 18.57 },
-      { "month": "May", "value": 19.36 }
+      { "month": "May", "value": 19.36 },
+      { "month": "Jun", "value": 17.15 }
     ]
   },
```

June is a 11.4% decline against May — worth surfacing rather than showing May as current.

## 2. `kpis.backlog` should follow the series

`kpis.backlog` is 19.36 (May). Once June is in, it should read **17.15**, otherwise the KPI
strip and the Synechron pack disagree on the same month.

## Nothing to change, but worth a comment

`attrition.ttmAttritionPct` is 17.3 and correct; any UI showing 11.4% is reading stale
sample data, not this file.
