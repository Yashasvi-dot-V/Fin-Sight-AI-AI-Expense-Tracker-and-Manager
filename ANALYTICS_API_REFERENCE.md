# Analytics Module - API Reference & Examples

## Table of Contents
1. [Class: ExpenseAnalytics](#expenseanalytics-class)
2. [Module Functions](#module-functions)
3. [Complete Examples](#complete-examples)
4. [Response Formats](#response-formats)
5. [Error Handling](#error-handling)

---

## ExpenseAnalytics Class

### Initialization
```python
from aiexpense.analytics import ExpenseAnalytics

analytics = ExpenseAnalytics(user)
# user: Django User object
```

---

### Method: prepare_data()

**Purpose**: Fetch and aggregate monthly expenses

```python
df = analytics.prepare_data()
```

**Returns**:
- `pd.DataFrame` with columns: year_month, amount, count, date, month_num
- `None` if no expenses exist

**Example**:
```python
analytics = ExpenseAnalytics(request.user)
df = analytics.prepare_data()

if df is not None:
    print(f"Months of data: {len(df)}")
    print(f"Total spent: ₹{df['amount'].sum()}")
    print(f"Average: ₹{df['amount'].mean():.2f}")
else:
    print("No expense data found")
```

**Output**:
```
    year_month  amount  count        date  month_num
0   2025-11    15000      12 2025-11-30           0
1   2025-12    18000      15 2025-12-31           1
2   2026-01    16500      14 2026-01-31           2
```

---

### Method: prepare_category_data()

**Purpose**: Get monthly spending by category

```python
category_df = analytics.prepare_category_data()
```

**Returns**:
- `pd.DataFrame` with columns: year_month, category, amount
- `None` if no data

**Example**:
```python
category_df = analytics.prepare_category_data()
if category_df is not None:
    print(category_df.groupby('category')['amount'].sum().sort_values(ascending=False))
```

**Output**:
```
category
Food          45000.50
Travel        28000.25
Shopping      18000.75
Entertainment 12000.00
...
```

---

### Method: train_model()

**Purpose**: Train RandomForest prediction model

```python
success = analytics.train_model()
```

**Returns**: `True` if successful, `False` if training failed

**Requirements**: `prepare_data()` must be called first with 3+ months data

**Example**:
```python
analytics.prepare_data()
if analytics.train_model():
    print("✓ Model trained successfully")
    predictions = analytics.predict_next_months(3)
else:
    print("✗ Model training failed (need 3+ months)")
```

---

### Method: predict_next_months(months=3)

**Purpose**: Predict total expenses for next N months

```python
predictions = analytics.predict_next_months(months=3)
```

**Parameters**:
- `months` (int): Number of months to predict (default: 3)

**Returns**: List of dictionaries

**Requires**: Model must be trained via `train_model()`

**Example**:
```python
predictions = analytics.predict_next_months(months=3)

for pred in predictions:
    print(f"{pred['month']} - {pred['date']}: ₹{pred['amount']:,.2f}")
```

**Output**:
```
1 - March 2026: ₹15,234.50
2 - April 2026: ₹14,876.25
3 - May 2026: ₹15,456.00
```

**Response Format**:
```python
[
    {
        'month': 1,
        'date': 'March 2026',
        'amount': 15234.5
    },
    {
        'month': 2,
        'date': 'April 2026',
        'amount': 14876.25
    },
    {
        'month': 3,
        'date': 'May 2026',
        'amount': 15456.0
    }
]
```

---

### Method: current_month_stats()

**Purpose**: Get current month spending statistics

```python
stats = analytics.current_month_stats()
```

**Returns**: Dictionary with current month info

**Example**:
```python
stats = analytics.current_month_stats()
print(f"Month: {stats['current_month']}")
print(f"Total: ₹{stats['total']:,.2f}")
```

**Output**:
```python
{
    'current_month': 'February 2026',
    'total': 14500.75
}
```

---

### Method: category_breakdown()

**Purpose**: Get current month spending by category

```python
categories = analytics.category_breakdown()
```

**Returns**: List of dictionaries with category totals

**Example**:
```python
categories = analytics.category_breakdown()

for cat in categories:
    print(f"{cat['category']}: ₹{cat['total']:,.2f}")
```

**Output**:
```python
[
    {'category': 'Food', 'total': 5234.50},
    {'category': 'Travel', 'total': 3421.00},
    {'category': 'Shopping', 'total': 2156.75},
    {'category': 'Entertainment', 'total': 1823.50},
    {'category': 'Groceries', 'total': 1564.25}
]
```

---

### Method: month_over_month_comparison()

**Purpose**: Compare current month vs previous month

```python
comparison = analytics.month_over_month_comparison()
```

**Returns**: Dictionary with comparison data

**Example**:
```python
mom = analytics.month_over_month_comparison()

if mom['percentage_change'] > 0:
    print(f"⬆️ Spending UP {mom['percentage_change']}%")
else:
    print(f"⬇️ Spending DOWN {abs(mom['percentage_change'])}%")

print(f"Current: ₹{mom['current']:,.2f}")
print(f"Previous: ₹{mom['previous']:,.2f}")
```

**Output**:
```python
{
    'current': 14500.75,
    'previous': 12000.50,
    'percentage_change': 20.84,
    'direction': 'up'
}
```

**Fields**:
- `current` (float): Current month total
- `previous` (float): Previous month total
- `percentage_change` (float): Percentage change (negative if decreased)
- `direction` (str): 'up' or 'down'

---

### Method: detect_anomalies()

**Purpose**: Detect unusual spending patterns (IQR method)

```python
anomalies = analytics.detect_anomalies()
```

**Returns**: List of anomaly dictionaries

**Example**:
```python
anomalies = analytics.detect_anomalies()

for anomaly in anomalies:
    status_emoji = "🔴" if anomaly['status'] == 'High' else "🟢"
    print(f"{status_emoji} {anomaly['date']}: ₹{anomaly['amount']:,.2f}")
```

**Output**:
```python
[
    {'date': 'December 2025', 'amount': 28500.0, 'status': 'High'},
    {'date': 'September 2025', 'amount': 5000.0, 'status': 'Low'}
]
```

---

### Method: generate_insights()

**Purpose**: Generate actionable spending recommendations

```python
insights = analytics.generate_insights()
```

**Returns**: List of insight dictionaries

**Example**:
```python
insights = analytics.generate_insights()

for insight in insights:
    print(f"[{insight['type'].upper()}] {insight['title']}")
    print(f"  {insight['message']}\n")
```

**Output**:
```
[SUCCESS] Great Savings!
  You spent 15% less compared to last month. Keep it up!

[WARNING] Food Dominating Budget
  Food accounts for 35% of your spending. Consider setting a limit.

[ALERT] Unusual Spending Detected
  Your spending in December 2025 was unusually high (₹28,500). Review your transactions.
```

**Insight Types**:
- `success`: Positive behavior
- `warning`: Caution needed
- `alert`: Negative behavior
- `info`: Informational

---

### Method: get_chart_data()

**Purpose**: Get raw data for frontend charts

```python
chart_data = analytics.get_chart_data()
```

**Returns**: Dictionary with chart datasets

**Example**:
```python
chart_data = analytics.get_chart_data()

# Monthly data for line chart
for month in chart_data['monthly']:
    print(f"{month['date']}: ₹{month['amount']}")

# Last 6 months for bar chart
for month in chart_data['last_6_months']:
    print(f"{month['date']}: ₹{month['amount']}")
```

**Output**:
```python
{
    'monthly': [
        {'date': 'Nov 2025', 'amount': 15000.5},
        {'date': 'Dec 2025', 'amount': 18000.25},
        {'date': 'Jan 2026', 'amount': 16500.75}
    ],
    'last_6_months': [
        {'date': 'Sep 2025', 'amount': 14000.0},
        {'date': 'Oct 2025', 'amount': 15500.0},
        # ... 4 more months
    ]
}
```

---

## Module Functions

### create_monthly_chart(analytics_obj)

**Purpose**: Generate monthly expense trend line chart

```python
from aiexpense.analytics import create_monthly_chart

chart_base64 = create_monthly_chart(analytics)
```

**Parameters**:
- `analytics_obj`: ExpenseAnalytics instance

**Returns**: Base64 encoded PNG image string (or None)

**Example**:
```python
analytics = ExpenseAnalytics(user)
analytics.prepare_data()

chart = create_monthly_chart(analytics)
if chart:
    html = f'<img src="{chart}" alt="Monthly Trend">'
    print(html)
```

---

### create_category_pie_chart(analytics_obj)

**Purpose**: Generate category distribution pie chart (current month)

```python
from aiexpense.analytics import create_category_pie_chart

chart_base64 = create_category_pie_chart(analytics)
```

**Returns**: Base64 encoded PNG image string (or None)

**Example**:
```python
chart = create_category_pie_chart(analytics)
if chart:
    template_html = f'<img src="{chart}" alt="Category Pie">'
```

---

### create_last_6_months_chart(analytics_obj)

**Purpose**: Generate last 6 months bar chart

```python
from aiexpense.analytics import create_last_6_months_chart

chart_base64 = create_last_6_months_chart(analytics)
```

**Returns**: Base64 encoded PNG image string (or None)

---

### get_analytics_dashboard(user)

**Purpose**: Main function - orchestrates all analytics

```python
from aiexpense.analytics import get_analytics_dashboard

analytics_data = get_analytics_dashboard(request.user)
```

**Parameters**:
- `user`: Django User object

**Returns**: Dictionary with complete analytics

**Example**:
```python
result = get_analytics_dashboard(user)

if result['status'] == 'success':
    print(f"✓ Analytics ready")
    print(f"  Predictions: {len(result['predictions'])}")
    print(f"  Insights: {len(result['insights'])}")
    print(f"  Charts: {len(result['charts'])}")
elif result['status'] == 'insufficient_data':
    print(f"⚠️ {result['message']}")
else:
    print(f"❌ {result['message']}")
```

**Response Format**:
```python
{
    'status': 'success',
    'current_month': {...},
    'predictions': [...],
    'insights': [...],
    'category_breakdown': [...],
    'month_over_month': {...},
    'anomalies': [...],
    'charts': {
        'monthly_trend': 'data:image/png;base64,...',
        'category_pie': 'data:image/png;base64,...',
        'last_6_months': 'data:image/png;base64,...'
    },
    'total_expenses': 150000.0,
    'average_monthly': 12500.0
}
```

---

## Complete Examples

### Example 1: Basic Usage

```python
from django.shortcuts import render
from aiexpense.analytics import get_analytics_dashboard

def my_analytics_view(request):
    analytics = get_analytics_dashboard(request.user)
    return render(request, 'my_template.html', {'analytics': analytics})
```

### Example 2: Manual Step-by-Step

```python
from aiexpense.analytics import ExpenseAnalytics

user = request.user
analytics = ExpenseAnalytics(user)

# Step 1: Prepare data
df = analytics.prepare_data()
if df is None:
    print("No data available")
    return

# Step 2: Get current month stats
stats = analytics.current_month_stats()
print(f"Current month: ₹{stats['total']}")

# Step 3: Compare with previous month
comparison = analytics.month_over_month_comparison()
print(f"Change: {comparison['percentage_change']}%")

# Step 4: Get category breakdown
categories = analytics.category_breakdown()
for cat in categories:
    print(f"  {cat['category']}: ₹{cat['total']}")

# Step 5: Train & predict
if len(df) >= 3:
    if analytics.train_model():
        predictions = analytics.predict_next_months(3)
        for pred in predictions:
            print(f"  {pred['date']}: ₹{pred['amount']}")

# Step 6: Generate insights
insights = analytics.generate_insights()
for insight in insights:
    print(f"[{insight['type']}] {insight['title']}")

# Step 7: Detect anomalies
anomalies = analytics.detect_anomalies()
for anomaly in anomalies:
    print(f"  {anomaly['date']}: ₹{anomaly['amount']} ({anomaly['status']})")
```

### Example 3: Creating Custom Dashboard

```python
from aiexpense.analytics import ExpenseAnalytics, create_monthly_chart

def custom_dashboard(request):
    user = request.user
    analytics = ExpenseAnalytics(user)
    
    # Prepare all data
    analytics.prepare_data()
    analytics.train_model()
    
    # Collect data
    context = {
        'current_total': analytics.current_month_stats()['total'],
        'categories': analytics.category_breakdown()[:3],  # Top 3
        'predictions': analytics.predict_next_months(6),   # 6 months
        'insights': analytics.generate_insights()[:5],     # Top 5
        'chart': create_monthly_chart(analytics),
        'anomalies': analytics.detect_anomalies()
    }
    
    return render(request, 'custom_dashboard.html', context)
```

### Example 4: API Response

```python
from django.http import JsonResponse
from aiexpense.analytics import get_analytics_dashboard

def analytics_api(request):
    analytics = get_analytics_dashboard(request.user)
    
    # Convert to API response (exclude images)
    response = {
        'status': analytics['status'],
        'current_total': analytics['current_month']['total'],
        'predictions': analytics['predictions'],
        'insights': analytics['insights'],
        'category_breakdown': analytics['category_breakdown'],
        'month_over_month': analytics['month_over_month'],
        'anomalies': analytics['anomalies']
    }
    
    return JsonResponse(response)
```

---

## Response Formats

### Current Month Stats
```python
{
    'current_month': 'February 2026',
    'total': 14500.75
}
```

### Predictions
```python
[
    {'month': 1, 'date': 'March 2026', 'amount': 15234.5},
    {'month': 2, 'date': 'April 2026', 'amount': 14876.25},
    {'month': 3, 'date': 'May 2026', 'amount': 15456.0}
]
```

### Insights
```python
[
    {
        'type': 'success',
        'title': 'Great Savings!',
        'message': 'You spent 15% less compared to last month. Keep it up!'
    },
    {
        'type': 'warning',
        'title': 'Food Dominating Budget',
        'message': 'Food accounts for 35% of your spending. Consider setting a limit.'
    }
]
```

### Category Breakdown
```python
[
    {'category': 'Food', 'total': 5234.50},
    {'category': 'Travel', 'total': 3421.00},
    {'category': 'Shopping', 'total': 2156.75}
]
```

### Month-over-Month
```python
{
    'current': 14500.75,
    'previous': 12000.50,
    'percentage_change': 20.84,
    'direction': 'up'
}
```

### Anomalies
```python
[
    {'date': 'December 2025', 'amount': 28500.0, 'status': 'High'},
    {'date': 'September 2025', 'amount': 5000.0, 'status': 'Low'}
]
```

---

## Error Handling

### Status Codes

```python
result = get_analytics_dashboard(user)

if result['status'] == 'success':
    # All data available
    
elif result['status'] == 'insufficient_data':
    # Not enough expenses
    message = result['message']
    # "Not enough expense data to generate analytics"
    
elif result['status'] == 'error':
    # Something failed
    message = result['message']
    # "Analytics generation failed: ..."
```

### Try-Except Pattern

```python
from aiexpense.analytics import ExpenseAnalytics

try:
    analytics = ExpenseAnalytics(user)
    df = analytics.prepare_data()
    
    if df is None or len(df) < 3:
        print("Need more data")
        return
    
    analytics.train_model()
    predictions = analytics.predict_next_months(3)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
```

---

## Tips & Tricks

### Get Maximum Prediction Value
```python
predictions = analytics.predict_next_months(3)
max_prediction = max(p['amount'] for p in predictions)
print(f"Highest predicted: ₹{max_prediction}")
```

### Filter High Anomalies Only
```python
anomalies = analytics.detect_anomalies()
high_anomalies = [a for a in anomalies if a['status'] == 'High']
print(f"High anomalies: {len(high_anomalies)}")
```

### Get Total Predicted Spending
```python
predictions = analytics.predict_next_months(3)
total_predicted = sum(p['amount'] for p in predictions)
average_predicted = total_predicted / len(predictions)
print(f"Average prediction: ₹{average_predicted:,.2f}")
```

### Format Percentage
```python
comparison = analytics.month_over_month_comparison()
change = comparison['percentage_change']
symbol = "📈" if change > 0 else "📉"
print(f"{symbol} {abs(change):.1f}%")
```

---

**Happy Analytics! 📊**
