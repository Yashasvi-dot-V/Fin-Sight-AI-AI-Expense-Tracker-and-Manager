# Analytics Module - Architecture & Visual Guide

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      USER BROWSER                               │
│  Dashboard.html ──→  [📊 Analytics Button]  ──────────────┐     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DJANGO ROUTING                               │
│                  /analytics/ URL Pattern                         │
│              (matches analytics_dashboard view)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DJANGO VIEW LAYER                           │
│                    views.py                                      │
│                                                                  │
│  @login_required                                               │
│  def analytics_dashboard(request):                             │
│    ├─ Verify user authenticated                               │
│    ├─ Call get_analytics_dashboard(request.user)              │
│    └─ Render analytics_dashboard.html                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ANALYTICS ENGINE LAYER                        │
│                    analytics.py                                  │
│                                                                  │
│  get_analytics_dashboard(user)                                 │
│    ├─→ Initialize ExpenseAnalytics(user)                       │
│    │                                                            │
│    ├─→ Data Preparation Stage:                                │
│    │   ├─ prepare_data()                                      │
│    │   │  └─ Fetch user expenses from DB                      │
│    │   │  └─ Aggregate by month                               │
│    │   │  └─ Return pandas DataFrame                          │
│    │   │                                                       │
│    │   └─ prepare_category_data()                             │
│    │      └─ Get monthly by category                          │
│    │                                                            │
│    ├─→ Statistics Stage:                                       │
│    │   ├─ current_month_stats()                               │
│    │   ├─ category_breakdown()                                │
│    │   ├─ month_over_month_comparison()                       │
│    │   └─ get_chart_data()                                    │
│    │                                                            │
│    ├─→ ML Model Stage:                                         │
│    │   ├─ train_model()                                       │
│    │   │  └─ Train RandomForestRegressor                      │
│    │   │  └─ 50 trees, max_depth=5                           │
│    │   │                                                       │
│    │   └─ predict_next_months(3)                              │
│    │      └─ Predict next 3 months                            │
│    │                                                            │
│    ├─→ Anomaly Detection Stage:                               │
│    │   └─ detect_anomalies()                                  │
│    │      └─ IQR (Interquartile Range) method                 │
│    │      └─ Find High/Low outliers                           │
│    │                                                            │
│    ├─→ Insights Generation Stage:                             │
│    │   └─ generate_insights()                                 │
│    │      ├─ Month-over-month analysis                        │
│    │      ├─ Category analysis                                │
│    │      ├─ Anomaly alerts                                   │
│    │      └─ Average spending analysis                        │
│    │                                                            │
│    └─→ Visualization Stage:                                    │
│        ├─ create_monthly_chart()                              │
│        │  └─ Line chart (matplotlib)                          │
│        │  └─ Encode as base64                                 │
│        │                                                       │
│        ├─ create_category_pie_chart()                         │
│        │  └─ Pie chart (matplotlib)                           │
│        │  └─ Encode as base64                                 │
│        │                                                       │
│        └─ create_last_6_months_chart()                        │
│           └─ Bar chart (matplotlib)                           │
│           └─ Encode as base64                                 │
│                                                                 │
│  Return: {                                                      │
│    'status': 'success',                                         │
│    'current_month': {...},                                      │
│    'predictions': [...],                                        │
│    'insights': [...],                                           │
│    'category_breakdown': [...],                                 │
│    'charts': {                                                  │
│      'monthly_trend': 'data:image/png;base64,...',             │
│      'category_pie': 'data:image/png;base64,...',              │
│      'last_6_months': 'data:image/png;base64,...'              │
│    }                                                            │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   TEMPLATE RENDERING                            │
│                analytics_dashboard.html                         │
│                                                                  │
│  ├─ Check Status                                                │
│  ├─ Display Stats (Current Month, Total, Avg)                   │
│  ├─ Display Predictions (3 months)                              │
│  ├─ Display Insights (with color coding)                        │
│  ├─ Display Category Breakdown                                  │
│  ├─ Display Anomalies (if any)                                  │
│  └─ Display Charts (3 embedded base64 images)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   RENDERED HTML RESPONSE                        │
│              Sent back to user's browser                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌──────────────────────┐
│   Database (Django)  │
│   Expense Model      │
│  - id, user, title   │
│  - amount, category  │
│  - date              │
└──────────────────────┘
         │
         │ .objects.filter(user=request.user)
         │
         ▼
┌──────────────────────────────────────────┐
│  ExpenseAnalytics.prepare_data()         │
│  - Fetch expenses                        │
│  - Group by year-month                   │
│  - Aggregate amounts                     │
│  - Fill missing months with 0            │
│  - Create DataFrame                      │
└──────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  Monthly DataFrame                       │
│  ┌────────────────────────────────────┐  │
│  │ year_month │ amount │ count │ ...  │  │
│  ├────────────────────────────────────┤  │
│  │ 2025-11    │ 15000  │ 12    │     │  │
│  │ 2025-12    │ 18000  │ 15    │     │  │
│  │ 2026-01    │ 16500  │ 14    │     │  │
│  └────────────────────────────────────┘  │
│                                          │
│  Ready for: ML, Stats, Charts            │
└──────────────────────────────────────────┘
         │
    ┌────┴─────┬────────────────┬──────────────┐
    │           │                │              │
    ▼           ▼                ▼              ▼
 ┌─────┐  ┌──────────┐  ┌────────────────┐  ┌─────────┐
 │Stats│  │ML Model  │  │Chart Creator   │  │Insights │
 ├─────┤  ├──────────┤  ├────────────────┤  ├─────────┤
 │Month│  │RandomFst │  │Matplotlib      │  │Algo:    │
 │Over │  │50 trees  │  │Seaborn         │  │-MOM     │
 │Month│  │max_depth │  │Base64 Encode   │  │-Anomaly │
 │ MOM │  │          │  │                │  │-Category│
 │Avg  │  │Train:    │  │Line Chart      │  │-Avg     │
 │Cate-│  │X=months  │  │Pie Chart       │  │         │
 │gory │  │y=amounts │  │Bar Chart       │  │         │
 └─────┘  ├──────────┤  └────────────────┘  └─────────┘
           │Predict  │
           │next 3mo │
           └──────────┘
    │           │                │              │
    └────┬──────┴────────────────┴──────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│  Complete Analytics Dictionary       │
│  {                                   │
│    'status': 'success',              │
│    'current_month': {...},           │
│    'predictions': [...],             │
│    'insights': [...],                │
│    'category_breakdown': [...],      │
│    'month_over_month': {...},        │
│    'anomalies': [...],               │
│    'charts': {                       │
│      'monthly_trend': '...',         │
│      'category_pie': '...',          │
│      'last_6_months': '...'          │
│    }                                 │
│  }                                   │
└──────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│  Template (analytics_dashboard.html) │
│  - Render all data                   │
│  - Display charts as images          │
│  - Format insights nicely            │
│  - Show statistics                   │
└──────────────────────────────────────┘
```

---

## Class Hierarchy

```
                    ┌─ ExpenseAnalytics
                    │  ├─ __init__(user)
                    │  │
                    │  ├─ Data Preparation Methods
                    │  │  ├─ prepare_data()
                    │  │  └─ prepare_category_data()
                    │  │
                    │  ├─ Model Training Methods
                    │  │  ├─ train_model()
                    │  │  └─ predict_next_months()
                    │  │
                    │  ├─ Statistics Methods
                    │  │  ├─ current_month_stats()
                    │  │  ├─ category_breakdown()
                    │  │  ├─ month_over_month_comparison()
                    │  │  └─ get_chart_data()
                    │  │
                    │  └─ Analysis Methods
                    │     ├─ detect_anomalies()
                    │     └─ generate_insights()
                    │
                    └─ Helper Functions (Module Level)
                       ├─ create_monthly_chart()
                       ├─ create_category_pie_chart()
                       ├─ create_last_6_months_chart()
                       └─ get_analytics_dashboard()
                          (Orchestrator function)
```

---

## Algorithm Flow Diagrams

### 1. Prediction Model Training

```
Training Data (History)
┌──────────────────────┐
│  Month | Spending     │
├──────────────────────┤
│   1   │ 15,000       │
│   2   │ 18,000       │
│   3   │ 16,500       │
│   4   │ 17,200       │
│   5   │ 19,000       │
│   6   │ 18,500       │
└──────────────────────┘
         │
         │ Feature Engineering
         │ X = [1, 2, 3, 4, 5, 6]  (month_num)
         │ y = [15k, 18k, 16.5k, ...]  (amounts)
         │
         ▼
┌──────────────────────────────────────┐
│  RandomForestRegressor               │
│  ├─ n_estimators = 50                │
│  │  (50 decision trees)              │
│  │                                   │
│  ├─ max_depth = 5                    │
│  │  (prevent overfitting)            │
│  │                                   │
│  ├─ random_state = 42                │
│  │  (reproducible results)           │
│  │                                   │
│  └─ Training: .fit(X, y)             │
└──────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│  Trained Model Ready for Prediction  │
│                                      │
│  Input: Month 7 (X = [[7]])         │
│  Output: Predicted Spending          │
│          (average of 50 trees)       │
└──────────────────────────────────────┘
```

### 2. Anomaly Detection (IQR Method)

```
Monthly Spending Data
┌──────────────────────────────────────┐
│  Amounts: [15k, 18k, 16.5k, 28k,     │
│           17k, 16.8k, 5k, 19k, ...]  │
└──────────────────────────────────────┘
         │
         │ Step 1: Calculate Percentiles
         │
         ▼
┌──────────────────────────────────────┐
│  Q1 (25th percentile) = 16,500       │
│  Q3 (75th percentile) = 18,500       │
│  IQR = Q3 - Q1 = 2,000               │
└──────────────────────────────────────┘
         │
         │ Step 2: Set Bounds
         │ Lower = Q1 - 1.5 × IQR = 13,500
         │ Upper = Q3 + 1.5 × IQR = 21,500
         │
         ▼
┌──────────────────────────────────────┐
│  Check Each Value                    │
│                                      │
│  15,000  ✓ Normal (13.5k < 15k < 21.5k)
│  18,000  ✓ Normal                    │
│  16,500  ✓ Normal                    │
│  28,000  ✗ HIGH (28k > 21.5k)        │
│  17,000  ✓ Normal                    │
│  16,800  ✓ Normal                    │
│   5,000  ✗ LOW  (5k < 13.5k)         │
│  19,000  ✓ Normal                    │
└──────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│  Result:                             │
│  - High Anomaly: 28,000 (Dec)        │
│  - Low Anomaly:  5,000 (Sep)         │
└──────────────────────────────────────┘
```

### 3. Insight Generation Pipeline

```
Input: User Expense Data
         │
    ┌────┴────┬────────────┬────────────┬──────────────┐
    │          │            │            │              │
    ▼          ▼            ▼            ▼              ▼
 ┌─────┐  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
 │Check│  │Detect    │ │Category  │ │Compare   │ │Find      │
 │MOM  │  │Anomalies │ │Analysis  │ │to Avg    │ │Recent    │
 ├─────┤  ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤
 │    │  │If High:  │ │If >40%:  │ │If 20%+:  │ │If Recent │
 │curr↑  │Alert     │ │Warning   │ │Alert     │ │Alert     │
 │prev↓  │          │ │          │ │          │ │          │
 │      │ │If Low:  │ │          │ │          │ │          │
 │      │ │Info     │ │          │ │          │ │          │
 └─────┘  └──────────┘ └──────────┘ └──────────┘ └──────────┘
    │          │            │            │              │
    └────┬─────┴────────────┴────────────┴──────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  Consolidated Insights:                  │
│                                          │
│  [{type: 'success', title, message},     │
│   {type: 'warning', title, message},     │
│   {type: 'alert', title, message},       │
│   {type: 'info', title, message}]        │
└──────────────────────────────────────────┘
```

---

## Component Dependencies

```
analytics.py
│
├─ IMPORTS:
│  ├─ pandas (DataFrame manipulation)
│  ├─ numpy (numerical operations)
│  ├─ datetime (date handling)
│  ├─ Django ORM (database queries)
│  ├─ scikit-learn:
│  │  ├─ RandomForestRegressor
│  │  └─ StandardScaler
│  ├─ matplotlib (charting)
│  └─ seaborn (styling)
│
├─ USES Django Models:
│  └─ Expense
│     ├─ user (ForeignKey)
│     ├─ title
│     ├─ amount (FloatField)
│     ├─ category
│     └─ date (DateField)
│
└─ OUTPUTS:
   ├─ Raw Data (pandas DataFrames)
   ├─ Statistics (dictionaries)
   ├─ Predictions (lists)
   ├─ Insights (lists)
   ├─ Anomalies (lists)
   └─ Charts (base64 PNG strings)

views.py
│
├─ IMPORTS:
│  └─ analytics module
│
├─ USES:
│  └─ get_analytics_dashboard() function
│
└─ RETURNS:
   └─ Rendered HTML template

urls.py
│
├─ DEFINES:
│  └─ /analytics/ URL pattern
│
└─ ROUTES TO:
   └─ analytics_dashboard view

analytics_dashboard.html
│
├─ DISPLAYS:
│  ├─ Statistics
│  ├─ Predictions
│  ├─ Insights
│  ├─ Anomalies
│  └─ Charts (base64 embedded)
│
└─ USES CSS:
   └─ Inline styles (gradients, flexbox, grid)
```

---

## Performance Characteristics

```
Operation              │ Time    │ Data Size
───────────────────────┼─────────┼──────────
Load Expenses from DB  │ 50-100ms│ 1000 rows
Group/Aggregate        │ 10-20ms │ 50 months
Train ML Model         │ 30-100ms│ 50 months
Make Predictions       │ 5-10ms  │ 3 months
Calculate Statistics   │ 10-20ms │ 50 months
Detect Anomalies       │ 5-10ms  │ 50 values
Generate Insights      │ 20-50ms │ Complex IO
Create Month Chart     │ 200-300ms│ 50 points
Create Pie Chart       │ 150-200ms│ 10 categories
Create Bar Chart       │ 150-200ms│ 6 points
───────────────────────┼─────────┼──────────
TOTAL (all 3 charts)   │ 800-1500ms│ Combined
───────────────────────┴─────────┴──────────

Optimization Tips:
1. Cache results (5 min TTL)
2. Reduce chart DPI (100→75)
3. Add database indexes
4. Lazy load charts (JS)
5. Compress images
```

---

## Decision Tree for Status Codes

```
                    Start
                      │
                      ▼
        ┌─ Have User? ─┐
        │              │
       No             Yes
       │               │
       ▼               ▼
    Error      ┌─ Query Expenses ─┐
               │                  │
               No               Yes (1+)
               │                  │
               ▼                  ▼
         insufficient_      ┌─ Have 3+ months? ─┐
         data              │                    │
                          No                   Yes
                          │                     │
                          ▼                     ▼
                    success          ┌─ Train Model ─┐
                  (with insights)    │                │
                  (no predictions)   Fail            Success
                                      │               │
                                      ▼               ▼
                                    error        success
                                  (recovery)    (all features)
```

---

## User Interaction Flow

```
┌──────────────┐
│ User Visits  │
│  Dashboard   │
└──────────────┘
       │
       ▼
    ┌──────────────────────────┐
    │ See "📊 Analytics" Button │
    └──────────────────────────┘
       │
       ▼ [Click]
    ┌──────────────────────────┐
    │ HTTP GET /analytics/     │
    │ (with session/auth)      │
    └──────────────────────────┘
       │
       ▼
    ┌──────────────────────────┐
    │ Django checks:           │
    │ @login_required          │
    │ ✓ User authenticated?    │
    └──────────────────────────┘
       │
       ▼
    ┌──────────────────────────┐
    │ Run analytics_dashboard()│
    │ Call get_analytics_      │
    │   dashboard(user)        │
    │ (~1-2 seconds)           │
    └──────────────────────────┘
       │
       ▼
    ┌──────────────────────────┐
    │ Render HTML with all     │
    │ data embedded            │
    │ (charts as base64)       │
    └──────────────────────────┘
       │
       ▼
    ┌──────────────────────────┐
    │ User sees:               │
    │ - Current month stats    │
    │ - Predictions            │
    │ - Insights               │
    │ - Charts                 │
    │ - Anomalies              │
    └──────────────────────────┘
       │
       ▼
    User Reviews Data
    & Takes Actions
```

---

## Technology Stack Diagram

```
┌─────────────────────────────────────────────────────┐
│  FRONTEND (Client Side)                             │
│  ├─ HTML5                                           │
│  ├─ CSS3 (Flexbox, Grid, Gradients)               │
│  └─ Browser (Chrome, Firefox, Safari, Edge)        │
└─────────────────────────────────────────────────────┘
     ▲                                      │
     │ HTTP Request                         │ HTTP Response
     │                                      │
     │                         ┌────────────▼────────────┐
     │                         │ DJANGO WEB FRAMEWORK    │
     │                         │ ├─ routing (urls.py)    │
     │                         │ ├─ views (views.py)     │
     │                         │ ├─ templates (.html)    │
     │                         │ └─ authentication       │
     │                         └────────────┬────────────┘
     │                                      │
     │                         ┌────────────▼────────────┐
     │                         │ ANALYTICS LAYER         │
     │                         │ (analytics.py)          │
     │                         ├─ Data Preparation      │
     │                         ├─ ML Model Training     │
     │                         ├─ Predictions           │
     │                         ├─ Insights Generation   │
     │                         ├─ Anomaly Detection     │
     │                         └─ Chart Creation        │
     │                                      │
     │                         ┌────────────▼────────────┐
     │                         │ LIBRARIES               │
     │                         ├─ pandas (Data frames)   │
     │                         ├─ scikit-learn (ML)      │
     │                         ├─ matplotlib (Charts)    │
     │                         ├─ seaborn (Styling)      │
     │                         ├─ numpy (Math)           │
     │                         └─ Django ORM            │
     │                                      │
     │                         ┌────────────▼────────────┐
     │                         │ DATABASE                │
     │                         │ (SQLite/PostgreSQL)     │
     │                         │ ├─ Expense Model        │
     │                         │ ├─ User Model           │
     │                         │ └─ Transactions         │
     │                         └─────────────────────────┘
     │
     └─ [Back to Frontend with Full Analytics]
```

---

This comprehensive visual guide helps understand:
1. **System Architecture**: How all components work together
2. **Data Flow**: From database to final render
3. **Class Design**: Object-oriented structure
4. **Algorithms**: How predictions and anomalies work
5. **Dependencies**: What libraries are used
6. **Performance**: Expected timing for operations
7. **Decision Making**: Status code logic
8. **User Journey**: Complete interaction flow
9. **Tech Stack**: Technology layers

Refer back to these diagrams when implementing or debugging the analytics module!
