# Machine Learning & Analytics Module - Documentation

## Overview

This module provides comprehensive machine learning, predictive analytics, spending insights, and data visualization for the AI Expense Manager Django application.

## Features

### 1. **Data Preparation** 📊
- Fetches all expenses for the logged-in user
- Aggregates expenses by month (groups by year & month)
- Fills missing months with zero values
- Prepares data for ML training and analysis
- Generates category-wise monthly breakdown

### 2. **Expense Prediction** 🔮
- **Algorithm**: RandomForestRegressor (robust for small datasets)
- **Prediction Horizon**: Next 3 months
- **Minimum Data**: 3+ months of expense history required
- **Output**: Predicted total expense amounts with dates
- **Why RandomForest**: Better than Linear Regression for non-linear patterns, less prone to overfitting on small datasets

### 3. **Spending Insights** 💡

#### Auto-Generated Insights:
1. **Month-over-Month Comparison**
   - Shows percentage change from previous month
   - Alerts if spending increased significantly
   - Celebrates when spending decreased

2. **Category Analysis**
   - Identifies highest spending category
   - Calculates category percentage of total
   - Suggests limits if one category exceeds 40% of budget

3. **Anomaly Detection**
   - Uses IQR (Interquartile Range) method
   - Detects unusual spending spikes
   - Flags unusually low spending periods
   - Automatically generates alerts for recent anomalies

4. **Average Spending Analysis**
   - Compares current month to historical average
   - Alerts if above average by 20%+
   - Suggests expense reduction strategies

### 4. **Data Visualization** 📈

#### Generated Charts:
1. **Monthly Expense Trend**
   - Line chart with markers
   - Shows spending over time
   - Displays full history

2. **Category Distribution (Pie Chart)**
   - Current month spending by category
   - Percentage breakdown
   - Color-coded by category

3. **Last 6 Months Bar Chart**
   - Month-by-month comparison
   - Values labeled on bars
   - Easy month-to-month comparison

#### Chart Technology:
- **Library**: Matplotlib + Seaborn
- **Format**: Base64 encoded PNG images
- **Integration**: Embedded directly in HTML (no external URLs)
- **Backend**: Agg (non-GUI backend for server environments)

### 5. **Current Month Statistics** 💰
- Total spending this month
- Category-wise breakdown
- Transaction count

## Module Structure

### `analytics.py` - Main Analytics Engine

#### Classes:

**`ExpenseAnalytics`**
- Main class handling all analytics operations
- Initialize with user object: `analytics = ExpenseAnalytics(user)`

#### Key Methods:

```python
# Data & Training
prepare_data()                    # Fetch & aggregate monthly data
prepare_category_data()           # Get monthly spending by category
train_model()                     # Train RandomForest model

# Predictions
predict_next_months(months=3)    # Predict next N months expenses

# Statistics
current_month_stats()             # Get current month total
category_breakdown()              # Category spending breakdown
month_over_month_comparison()    # Compare with previous month

# Insights
detect_anomalies()               # Find unusual spending patterns
generate_insights()              # Create actionable recommendations

# Visualization
get_chart_data()                 # Return data for frontend
```

#### Helper Functions (Module Level):

```python
create_monthly_chart(analytics_obj)      # Monthly trend line chart
create_category_pie_chart(analytics_obj) # Category distribution pie
create_last_6_months_chart(analytics_obj) # Last 6 months bar chart
get_analytics_dashboard(user)            # Main orchestration function
```

## Django Integration

### Views

**`analytics_dashboard(request)`** in `views.py`
- `@login_required` decorator ensures user authentication
- Calls `get_analytics_dashboard()` with logged-in user
- Passes all analytics data to template
- Error handling with user-friendly messages

### URLs

Added in `urls.py`:
```python
path("analytics/", views.analytics_dashboard, name="analytics")
```
- Access at: `http://yourdomain/analytics/`

### Templates

**`analytics_dashboard.html`**
- Responsive design (mobile-friendly)
- Gradient styling with modern UI
- Status indicators (success, warning, alert, info)
- Dynamic content rendering based on data availability
- Embedded base64 images for charts
- Fallback messages for insufficient data

## Data Flow Diagram

```
User Request (/analytics/)
    ↓
analytics_dashboard(request)
    ↓
get_analytics_dashboard(user)
    ├── ExpenseAnalytics(user)
    ├── prepare_data()
    ├── train_model()
    ├── predict_next_months(3)
    ├── current_month_stats()
    ├── category_breakdown()
    ├── month_over_month_comparison()
    ├── detect_anomalies()
    ├── generate_insights()
    └── Create Charts:
        ├── create_monthly_chart()
        ├── create_category_pie_chart()
        └── create_last_6_months_chart()
    ↓
Return Dictionary with all analytics
    ↓
Render analytics_dashboard.html
```

## Model Details

### RandomForestRegressor Configuration
```python
RandomForestRegressor(
    n_estimators=50,      # 50 decision trees
    max_depth=5,          # Prevent overfitting
    random_state=42,      # Reproducibility
    min_samples_leaf=1    # Handle small datasets
)
```

**Why this configuration?**
- **50 trees**: Good balance between accuracy and speed for small datasets
- **max_depth=5**: Prevents overfitting (typical for <100 data points)
- **min_samples_leaf=1**: Handles sparse monthly data
- **random_state=42**: Ensures consistent predictions

### Anomaly Detection (IQR Method)
```
Q1 = 25th percentile
Q3 = 75th percentile
IQR = Q3 - Q1
Lower Bound = Q1 - 1.5 × IQR
Upper Bound = Q3 + 1.5 × IQR

If amount > Upper Bound → High anomaly
If amount < Lower Bound → Low anomaly
```

## Minimum Data Requirements

| Feature | Minimum Data |
|---------|-------------|
| Current Statistics | 1 expense |
| Category Breakdown | 1 expense |
| Monthly Trend Chart | 2+ months |
| 6-Month Chart | 6+ months |
| Predictions | 3+ months |
| Insights | 2+ months |
| Anomaly Detection | 3+ data points |

## Error Handling

1. **Insufficient Data**: Shows user-friendly message suggesting more expenses
2. **Model Training Failure**: Falls back to basic statistics
3. **Chart Generation Failure**: Returns None (template skips display)
4. **Database Errors**: Logs error and returns error status
5. **Empty Datasets**: Gracefully handles with default values

## Performance Considerations

- **Query Optimization**: Uses `.values()` for aggregation (not full object loading)
- **Aggregation**: Database-level with `.aggregate()` and `.annotate()`
- **Chart Generation**: Base64 encoding (single HTTP request, no external URLs)
- **Memory**: Matplotlib uses `Agg` backend (no display server needed)
- **Caching**: Not implemented but can be added with Django cache framework

## Usage Example

```python
from .analytics import get_analytics_dashboard

# In your view
analytics_data = get_analytics_dashboard(request.user)

# Check status
if analytics_data['status'] == 'success':
    predictions = analytics_data['predictions']
    insights = analytics_data['insights']
    charts = analytics_data['charts']
else:
    print(analytics_data['message'])
```

## Context Variables in Template

```javascript
analytics = {
    status: 'success',                    // 'success', 'error', 'insufficient_data'
    current_month: {
        current_month: 'January 2026',
        total: 15000.50
    },
    predictions: [
        {month: 1, date: 'March 2026', amount: 14500.23},
        {month: 2, date: 'April 2026', amount: 15200.45},
        {month: 3, date: 'May 2026', amount: 14800.67}
    ],
    insights: [
        {type: 'success|warning|alert|info', title: '...', message: '...'},
        ...
    ],
    category_breakdown: [
        {category: 'Food', total: 3000},
        {category: 'Travel', total: 2500}
    ],
    month_over_month: {
        current: 15000,
        previous: 12000,
        percentage_change: 25.0,
        direction: 'up'
    },
    anomalies: [
        {date: 'December 2025', amount: 25000, status: 'High'},
        ...
    ],
    charts: {
        monthly_trend: 'data:image/png;base64,...',
        category_pie: 'data:image/png;base64,...',
        last_6_months: 'data:image/png;base64,...'
    },
    total_expenses: 150000.00,
    average_monthly: 12500.00
}
```

## Customization

### Adjusting Prediction Months
```python
# In views.py
predictions = analytics.predict_next_months(6)  # Predict 6 months instead
```

### Changing Anomaly Sensitivity
```python
# In analytics.py, modify multiplier
upper_bound = Q3 + 2.0 * IQR  # More sensitive
lower_bound = Q1 - 2.0 * IQR  # More sensitive
```

### Switching to Linear Regression
```python
from sklearn.linear_model import LinearRegression

self.model = LinearRegression()
self.model.fit(X, y)
```

### Adding Category Thresholds
```python
if category_percent > 50:  # Change from 40% to 50%
    insights.append({...})
```

## Dependencies

Required packages:
```
pandas>=1.3.0
scikit-learn>=1.0.0
matplotlib>=3.4.0
seaborn>=0.11.0
numpy>=1.20.0
django>=3.2
```

Install with:
```bash
pip install pandas scikit-learn matplotlib seaborn numpy
```

## Testing the Module

```python
# Test in Django shell
python manage.py shell

from django.contrib.auth.models import User
from aiexpense.analytics import get_analytics_dashboard

user = User.objects.first()
analytics = get_analytics_dashboard(user)
print(analytics['status'])
print(analytics['predictions'])
print(analytics['insights'])
```

## Future Enhancements

1. **Time Series Models**: ARIMA, Prophet for seasonal patterns
2. **Budget Recommendations**: Auto-suggest budgets by category
3. **Goal Tracking**: User-defined spending goals
4. **Forecasting**: Yearly expense projections
5. **Caching**: Redis cache for analytics results (24-hour TTL)
6. **Alerts**: Email/SMS notifications for anomalies
7. **Export**: PDF/Excel report generation
8. **Comparison**: Compare with user's spending goals
9. **Trends**: ML-powered trend analysis
10. **Recommendations**: Personalized saving tips based on patterns

## Troubleshooting

**Charts not showing?**
- Check matplotlib backend is set to 'Agg'
- Verify PIL/Pillow is installed
- Check browser allows base64 images

**Predictions not generating?**
- Need at least 3 months of expense data
- Check that expenses are in the database
- Verify dates are correct format

**Insights not appearing?**
- Ensure category data is populated
- Check for database query errors in logs
- Verify user has expenses in current month

**Module too slow?**
- Reduce chart DPI (currently 100)
- Cache analytics results
- Optimize database queries with select_related()

## Support & Contributing

For issues or questions:
1. Check the logs in Django console
2. Verify database contains expected data
3. Run analytics tests in Django shell
4. Review error messages in analytics_dashboard.html
