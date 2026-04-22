"""
Machine Learning and Analytics Module for Expense Tracker
Includes: Data preparation, ML prediction, insights generation, and visualization
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from django.db.models import Sum, Q
from .models import Expense
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from matplotlib.dates import DateFormatter
import warnings
warnings.filterwarnings('ignore')

# Configure matplotlib for non-GUI backend
try:
    plt.switch_backend('Agg')
    sns.set_style("whitegrid")
except Exception as e:
    print(f"Warning: Could not configure matplotlib: {e}")


class ExpenseAnalytics:
    """Main analytics class for expense prediction and insights"""
    
    def __init__(self, user):
        """Initialize with user object"""
        self.user = user
        self.df = None
        self.model = None
        self.scaler = StandardScaler()
        
    def prepare_data(self):
        """
        Fetch user expenses and prepare monthly aggregated data
        Returns: pandas DataFrame with monthly expense totals
        """
        try:
            # Fetch all expenses for the user
            expenses = Expense.objects.filter(user=self.user).values('date', 'amount', 'category')
            
            if not expenses.exists():
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(list(expenses))
            df['date'] = pd.to_datetime(df['date'])
            
            # Create year-month column
            df['year_month'] = df['date'].dt.to_period('M')
            
            # Aggregate by month
            monthly_data = df.groupby('year_month').agg({
                'amount': 'sum',
                'category': 'count'  # count transactions
            }).rename(columns={'category': 'count'})
            
            # Fill missing months with zero
            date_range = pd.period_range(
                start=monthly_data.index.min(),
                end=monthly_data.index.max(),
                freq='M'
            )
            monthly_data = monthly_data.reindex(date_range, fill_value=0)
            
            # Reset index and create numeric date for ML
            monthly_data = monthly_data.reset_index()
            monthly_data.columns = ['year_month', 'amount', 'count']
            monthly_data['date'] = monthly_data['year_month'].dt.to_timestamp()
            monthly_data['month_num'] = range(len(monthly_data))
            
            self.df = monthly_data
            return monthly_data
            
        except Exception as e:
            print(f"Error in prepare_data: {e}")
            return None
    
    def prepare_category_data(self):
        """Get monthly spending by category"""
        try:
            expenses = Expense.objects.filter(user=self.user).values('date', 'category', 'amount')
            df = pd.DataFrame(list(expenses))
            
            if df.empty:
                return None
                
            df['date'] = pd.to_datetime(df['date'])
            df['year_month'] = df['date'].dt.to_period('M')
            
            category_monthly = df.groupby(['year_month', 'category'])['amount'].sum().reset_index()
            return category_monthly
            
        except Exception as e:
            print(f"Error in prepare_category_data: {e}")
            return None
    
    def train_model(self):
        """Train ML model for expense prediction"""
        if self.df is None or len(self.df) < 3:
            return False
        
        try:
            X = self.df[['month_num']].values
            y = self.df['amount'].values
            
            # Use RandomForest for small datasets (less prone to overfitting)
            self.model = RandomForestRegressor(
                n_estimators=50,
                max_depth=5,
                random_state=42,
                min_samples_leaf=1
            )
            
            self.model.fit(X, y)
            return True
            
        except Exception as e:
            print(f"Error in train_model: {e}")
            return False
    
    def predict_next_month_weighted_average(self):
        """
        Predict next month's spending with improved accuracy using:
        - Exponential smoothing (recent months weighted much higher)
        - Trend detection and analysis
        - Outlier exclusion
        - Average calculation with confidence
        
        Returns: dict with prediction details
        """
        if self.df is None or len(self.df) < 1:
            print(f"[PREDICTION] No data: df is None={self.df is None}, len={len(self.df) if self.df is not None else 0}")
            return None
        
        try:
            print(f"[PREDICTION] Starting prediction with {len(self.df)} months of data")
            # Get recent months (last 3-6)
            recent_months = min(6, len(self.df))
            df_recent = self.df.tail(recent_months).copy()
            
            print(f"[PREDICTION] Using {recent_months} recent months")
            if len(df_recent) == 0:
                print(f"[PREDICTION] ERROR: No recent data after tail()")
                return None
            
            amounts = df_recent['amount'].values
            # Convert to float to handle Decimal objects from Django ORM
            amounts = np.array([float(amt) for amt in amounts])
            print(f"[PREDICTION] Amounts to predict from: {amounts}")
            
            # ============================================
            # STEP 1: Outlier Detection (IQR Method)
            # ============================================
            if len(amounts) >= 3:
                Q1 = np.percentile(amounts, 25)
                Q3 = np.percentile(amounts, 75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                # Filter out outliers
                filtered_amounts = np.array([
                    amt for amt in amounts 
                    if lower_bound <= amt <= upper_bound
                ])
                
                # Use filtered amounts if at least 2 remain, otherwise use all
                if len(filtered_amounts) >= 2:
                    amounts = filtered_amounts
            
            # ============================================
            # STEP 2: Exponential Smoothing with Trend
            # ============================================
            # Use exponential weights (alpha = 0.7 for responsiveness)
            # Recent months get much higher weight
            alpha = 0.7
            weights = []
            for i in range(len(amounts)):
                # Exponential decay from past to present
                weight = alpha ** (len(amounts) - 1 - i)
                weights.append(weight)
            
            weights = np.array(weights)
            weights = weights / weights.sum()  # Normalize
            
            # Exponential smoothed estimate
            smoothed_estimate = np.sum(amounts * weights)
            
            # ============================================
            # STEP 3: Trend Analysis (Simple Linear Trend)
            # ============================================
            if len(amounts) >= 2:
                # Calculate month-over-month growth rate
                x = np.arange(len(amounts))
                y = amounts
                
                # Fit simple linear trend
                try:
                    coefficients = np.polyfit(x, y, 1)
                    trend_slope = coefficients[0]
                    
                    # Apply trend adjustment for next month
                    # If spending is trending up, increase prediction
                    # If trending down, decrease prediction
                    trend_factor = 1 + (trend_slope / amounts[-1]) if amounts[-1] > 0 else 1
                    
                    # Limit trend adjustment to ±15% to avoid extreme predictions
                    trend_factor = np.clip(trend_factor, 0.85, 1.15)
                    
                    predicted_amount = smoothed_estimate * trend_factor
                except Exception as trend_error:
                    print(f"Trend analysis note: {trend_error}")
                    predicted_amount = smoothed_estimate
            else:
                predicted_amount = smoothed_estimate
            
            # Ensure prediction is positive
            predicted_amount = max(predicted_amount, 0)
            
            # ============================================
            # STEP 4: Calculate Confidence and Basis
            # ============================================
            # Calculate standard deviation for confidence measure
            std_dev = np.std(amounts)
            avg_amount = np.mean(amounts)
            
            # Determine confidence level
            if std_dev < avg_amount * 0.15:
                confidence = "High confidence"
            elif std_dev < avg_amount * 0.30:
                confidence = "Medium confidence"
            else:
                confidence = "Standard estimate"
            
            # Calculate next month date
            last_date = self.df['date'].max()
            next_month_date = last_date + timedelta(days=30)
            
            result = {
                'amount': round(predicted_amount, 2),
                'date': next_month_date.strftime('%B %Y'),
                'basis': f'{confidence} - Based on {len(amounts)} months with trend analysis'
            }
            print(f"[PREDICTION] SUCCESS: Predicted ₹{result['amount']} for {result['date']}")
            return result
            
        except Exception as e:
            print(f"[PREDICTION] ERROR in prediction: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def predict_next_months(self, months=1):
        """
        Predict total expenses for next month
        Returns: list with single prediction or empty list
        """
        # Predict only next month
        if months != 1:
            print("Note: Predictions are now limited to next month only")
        
        prediction = self.predict_next_month_weighted_average()
        
        if prediction is None:
            return []
        
        return [prediction]

    
    def current_month_stats(self):
        """Get current month spending statistics"""
        try:
            today = datetime.now()
            current_year_month = today.strftime('%Y-%m')
            
            current_month_expenses = Expense.objects.filter(
                user=self.user,
                date__year=today.year,
                date__month=today.month
            ).aggregate(total=Sum('amount'))
            
            current_total = current_month_expenses['total'] or 0
            
            return {
                'current_month': today.strftime('%B %Y'),
                'total': round(current_total, 2)
            }
            
        except Exception as e:
            print(f"Error in current_month_stats: {e}")
            return {'current_month': 'N/A', 'total': 0}
    
    def category_breakdown(self):
        """Get current month spending by category"""
        try:
            today = datetime.now()
            
            category_stats = Expense.objects.filter(
                user=self.user,
                date__year=today.year,
                date__month=today.month
            ).values('category').annotate(total=Sum('amount')).order_by('-total')
            
            return list(category_stats)
            
        except Exception as e:
            print(f"Error in category_breakdown: {e}")
            return []
    
    def month_over_month_comparison(self):
        """Compare current month vs previous month"""
        try:
            today = datetime.now()
            current_year, current_month = today.year, today.month
            
            # Current month total
            current = Expense.objects.filter(
                user=self.user,
                date__year=current_year,
                date__month=current_month
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Previous month total
            if current_month == 1:
                prev_year, prev_month = current_year - 1, 12
            else:
                prev_year, prev_month = current_year, current_month - 1
            
            previous = Expense.objects.filter(
                user=self.user,
                date__year=prev_year,
                date__month=prev_month
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Calculate percentage change
            if previous == 0:
                percentage_change = 100 if current > 0 else 0
            else:
                percentage_change = ((current - previous) / previous) * 100
            
            return {
                'current': round(current, 2),
                'previous': round(previous, 2),
                'percentage_change': round(percentage_change, 2),
                'direction': 'up' if percentage_change > 0 else 'down'
            }
            
        except Exception as e:
            print(f"Error in month_over_month_comparison: {e}")
            return {'current': 0, 'previous': 0, 'percentage_change': 0, 'direction': 'neutral'}
    
    def detect_anomalies(self):
        """Detect unusual spending patterns using IQR method"""
        if self.df is None or len(self.df) < 3:
            return []
        
        try:
            amounts = self.df['amount'].values
            Q1 = np.percentile(amounts, 25)
            Q3 = np.percentile(amounts, 75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            anomalies = []
            for idx, row in self.df.iterrows():
                if row['amount'] > upper_bound or row['amount'] < lower_bound:
                    anomalies.append({
                        'date': row['date'].strftime('%B %Y'),
                        'amount': round(row['amount'], 2),
                        'status': 'High' if row['amount'] > upper_bound else 'Low'
                    })
            
            return anomalies
            
        except Exception as e:
            print(f"Error in detect_anomalies: {e}")
            return []
    
    def generate_insights(self):
        """
        Generate actionable spending insights
        Special: Health category is displayed as spending only (no advice/tips)
        """
        insights = []
        
        try:
            # Special: Health category - only show spending, no recommendations
            category_data = self.category_breakdown()
            health_spending = next((cat['total'] for cat in category_data if cat['category'].lower() == 'health'), None)
            
            if health_spending is not None:
                insights.append({
                    'type': 'info',
                    'title': '💊 Health Spending This Month',
                    'message': f"Your health-related expenses this month: ₹{health_spending}",
                    'is_health': True  # Flag to prevent additional suggestions
                })
            
            # Insight 1: Month-over-month comparison
            mom = self.month_over_month_comparison()
            if mom['percentage_change'] > 5:  # Only significant changes
                insights.append({
                    'type': 'warning',
                    'title': 'Spending Increased',
                    'message': f"Your spending increased by {abs(mom['percentage_change']):.1f}% compared to last month. "
                              f"Current: ₹{mom['current']} vs Previous: ₹{mom['previous']}"
                })
            elif mom['percentage_change'] < -5:  # Significant savings
                insights.append({
                    'type': 'success',
                    'title': '✅ Great Savings!',
                    'message': f"You spent {abs(mom['percentage_change']):.1f}% less than last month. Keep up the great work!"
                })
            
            # Insight 2: Top spending category (exclude health)
            non_health_categories = [cat for cat in category_data if cat['category'].lower() != 'health']
            if non_health_categories:
                top_category = non_health_categories[0]
                total_current = sum(cat['total'] for cat in category_data)
                category_percent = (top_category['total'] / total_current * 100) if total_current > 0 else 0
                
                if category_percent > 40:
                    insights.append({
                        'type': 'info',
                        'title': f"📌 {top_category['category']} is Your Top Expense",
                        'message': f"{top_category['category']} accounts for {category_percent:.1f}% of your spending. Consider reviewing this category."
                    })
            
            # Insight 3: Anomaly detection
            anomalies = self.detect_anomalies()
            if anomalies:
                high_anomalies = [a for a in anomalies if a['status'] == 'High']
                if high_anomalies:
                    latest_anomaly = high_anomalies[-1]
                    insights.append({
                        'type': 'alert',
                        'title': '⚠️ Unusual Spike Detected',
                        'message': f"Your spending in {latest_anomaly['date']} was unusually high (₹{latest_anomaly['amount']})."
                    })
            
        except Exception as e:
            print(f"Error in generate_insights: {e}")
        
        return insights

    
    def get_chart_data(self):
        """Return data for frontend charts"""
        if self.df is None:
            return None
        
        try:
            chart_data = {
                'monthly': [
                    {
                        'date': row['date'].strftime('%b %Y'),
                        'amount': float(row['amount'])
                    }
                    for _, row in self.df.iterrows()
                ],
                'last_6_months': [
                    {
                        'date': row['date'].strftime('%b %Y'),
                        'amount': float(row['amount'])
                    }
                    for _, row in self.df.tail(6).iterrows()
                ]
            }
            return chart_data
            
        except Exception as e:
            print(f"Error in get_chart_data: {e}")
            return None


def create_monthly_chart(analytics_obj):
    """Create line chart of monthly expenses"""
    if analytics_obj.df is None or len(analytics_obj.df) == 0:
        return None
    
    try:
        fig, ax = plt.subplots(figsize=(12, 5))
        
        dates = analytics_obj.df['date']
        amounts = analytics_obj.df['amount']
        
        ax.plot(dates, amounts, marker='o', linewidth=2, markersize=6, color='#4a90e2')
        ax.fill_between(dates, amounts, alpha=0.2, color='#4a90e2')
        
        ax.set_title('Monthly Expense Trend', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Amount (₹)', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Format dates
        try:
            ax.xaxis.set_major_formatter(DateFormatter("%b %Y"))
            fig.autofmt_xdate()
        except:
            pass
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.tight_layout()
        try:
            plt.savefig(buffer, format='png', dpi=80, bbox_inches='tight')
        except Exception as save_err:
            print(f"Error saving chart: {save_err}")
            # Try with different format
            plt.savefig(buffer, format='raw', dpi=80, bbox_inches='tight')
        
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close(fig)
        
        return f"data:image/png;base64,{image_base64}"
        
    except Exception as e:
        print(f"Error in create_monthly_chart: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_category_pie_chart(analytics_obj):
    """Create pie chart of spending by category"""
    try:
        today = datetime.now()
        category_data = Expense.objects.filter(
            user=analytics_obj.user,
            date__year=today.year,
            date__month=today.month
        ).values('category').annotate(total=Sum('amount'))
        
        if not category_data.exists():
            return None
        
        categories = [cat['category'] for cat in category_data]
        amounts = [float(cat['total']) for cat in category_data]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        colors = plt.cm.Set3(np.linspace(0, 1, len(categories)))
        
        wedges, texts, autotexts = ax.pie(
            amounts,
            labels=categories,
            autopct='%1.1f%%',
            colors=colors,
            startangle=90
        )
        
        ax.set_title(f'Spending by Category - {today.strftime("%B %Y")}', 
                    fontsize=16, fontweight='bold', pad=20)
        
        # Format text
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.tight_layout()
        try:
            plt.savefig(buffer, format='png', dpi=80, bbox_inches='tight')
        except Exception as save_err:
            print(f"Error saving pie chart to PNG: {save_err}. Trying raw format...")
            try:
                plt.savefig(buffer, format='raw', dpi=80, bbox_inches='tight')
            except Exception as raw_err:
                print(f"Error saving with raw format: {raw_err}")
                raise
        
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close(fig)
        
        return f"data:image/png;base64,{image_base64}"
        
    except Exception as e:
        print(f"Error in create_category_pie_chart: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_last_6_months_chart(analytics_obj):
    """Create bar chart for last 6 months"""
    if analytics_obj.df is None or len(analytics_obj.df) == 0:
        return None
    
    try:
        df_last_6 = analytics_obj.df.tail(6)
        
        fig, ax = plt.subplots(figsize=(12, 5))
        
        dates = [d.strftime('%b %Y') for d in df_last_6['date']]
        amounts = df_last_6['amount'].values
        
        bars = ax.bar(dates, amounts, color='#4a90e2', alpha=0.7, edgecolor='#2c5aa0', linewidth=1.5)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'₹{height:.0f}',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        ax.set_title('Last 6 Months Spending', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Month', fontsize=12)
        ax.set_ylabel('Amount (₹)', fontsize=12)
        ax.grid(True, alpha=0.3, axis='y')
        
        fig.autofmt_xdate()
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.tight_layout()
        try:
            plt.savefig(buffer, format='png', dpi=80, bbox_inches='tight')
        except Exception as save_err:
            print(f"Error saving bar chart to PNG: {save_err}. Trying raw format...")
            try:
                plt.savefig(buffer, format='raw', dpi=80, bbox_inches='tight')
            except Exception as raw_err:
                print(f"Error saving with raw format: {raw_err}")
                raise
        
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close(fig)
        
        return f"data:image/png;base64,{image_base64}"
        
    except Exception as e:
        print(f"Error in create_last_6_months_chart: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_analytics_dashboard(user):
    """
    Main function to prepare all analytics data for dashboard
    Returns: dictionary with all analytics components
    Predictions now focus on next month only using weighted averages
    """
    try:
        print(f"\n[ANALYTICS] Starting analytics dashboard for user: {user.username}")
        analytics = ExpenseAnalytics(user)
        
        # Prepare data
        print(f"[ANALYTICS] Preparing data...")
        monthly_data = analytics.prepare_data()
        
        if monthly_data is None or len(monthly_data) == 0:
            print(f"[ANALYTICS] Insufficient data")
            return {
                'status': 'insufficient_data',
                'message': 'Not enough expense data to generate analytics'
            }
        
        print(f"[ANALYTICS] Data prepared: {len(monthly_data)} months")
        
        # Train model (kept for potential future use)
        if len(monthly_data) < 3:
            has_predictions = False
        else:
            has_predictions = analytics.train_model()
        
        # Generate prediction for next month only (weighted average)
        print(f"[ANALYTICS] Generating prediction...")
        prediction = analytics.predict_next_month_weighted_average()
        predictions = [prediction] if prediction else []
        print(f"[ANALYTICS] Predictions result: {predictions}")
        
        # Generate insights
        insights = analytics.generate_insights()
        
        # Get statistics
        current_stats = analytics.current_month_stats()
        category_breakdown = analytics.category_breakdown()
        mom_comparison = analytics.month_over_month_comparison()
        anomalies = analytics.detect_anomalies()
        chart_data = analytics.get_chart_data()
        
        # Create charts
        monthly_chart = create_monthly_chart(analytics)
        category_chart = create_category_pie_chart(analytics)
        last_6_months_chart = create_last_6_months_chart(analytics)
        
        print(f"[ANALYTICS] Dashboard prepared successfully")
        return {
            'status': 'success',
            'current_month': current_stats,
            'predictions': predictions,
            'insights': insights,
            'category_breakdown': category_breakdown,
            'month_over_month': mom_comparison,
            'anomalies': anomalies,
            'chart_data': chart_data,
            'charts': {
                'monthly_trend': monthly_chart,
                'category_pie': category_chart,
                'last_6_months': last_6_months_chart
            },
            'total_expenses': round(analytics.df['amount'].sum(), 2) if analytics.df is not None else 0,
            'average_monthly': round(analytics.df['amount'].mean(), 2) if analytics.df is not None else 0
        }
        
    except Exception as e:
        print(f"[ANALYTICS] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'error',
            'message': f'Analytics generation failed: {str(e)}'
        }
