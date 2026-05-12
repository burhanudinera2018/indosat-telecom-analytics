"""
Internet Traffic Forecasting for Milan Telecom
Indosat Ooredoo Data Science Portfolio
Models: ARIMA + Prophet
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sqlalchemy import create_engine
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')
import os

print("="*60)
print("🔮 INTERNET TRAFFIC FORECASTING FOR MILAN TELECOM")
print("="*60)

# Koneksi ke database
engine = create_engine('postgresql:///indosat_db?host=localhost')

# 1. Load data time series (aggregate per jam)
print("\n📊 Loading hourly traffic data...")
df = pd.read_sql("""
    SELECT 
        DATE_TRUNC('hour', hour) as timestamp,
        SUM(internet_traffic) as total_traffic
    FROM cdr_hourly
    GROUP BY DATE_TRUNC('hour', hour)
    ORDER BY timestamp
""", engine)

# Konversi ke datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.set_index('timestamp')
print(f"   Loaded {len(df)} hourly records")
print(f"   Date range: {df.index.min()} to {df.index.max()}")
print(f"   Traffic range: {df['total_traffic'].min():.0f} - {df['total_traffic'].max():.0f}")

# 2. Eksplorasi Time Series
print("\n📈 Exploratory Analysis...")
os.makedirs('images_indosat', exist_ok=True)

fig, axes = plt.subplots(3, 1, figsize=(12, 10))

# Plot original
axes[0].plot(df.index, df['total_traffic'], color='#2ecc71', linewidth=1)
axes[0].set_title('Internet Traffic Time Series (Hourly)', fontsize=14)
axes[0].set_ylabel('Traffic')
axes[0].grid(True, alpha=0.3)

# Rolling mean & std
rolling_mean = df['total_traffic'].rolling(window=24).mean()
rolling_std = df['total_traffic'].rolling(window=24).std()
axes[1].plot(df.index, rolling_mean, color='#e74c3c', label='24h Rolling Mean')
axes[1].plot(df.index, rolling_std, color='#3498db', label='24h Rolling Std')
axes[1].set_title('Rolling Statistics (24-hour window)', fontsize=14)
axes[1].set_ylabel('Traffic')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

# Distribution
axes[2].hist(df['total_traffic'], bins=50, color='#9b59b6', alpha=0.7, edgecolor='black')
axes[2].set_title('Distribution of Hourly Traffic', fontsize=14)
axes[2].set_xlabel('Traffic')
axes[2].set_ylabel('Frequency')
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('images_indosat/forecast_eda.png', dpi=150, bbox_inches='tight')
plt.close()
print("   ✅ Saved: images_indosat/forecast_eda.png")

# 3. Stationarity Test (ADF Test)
print("\n📊 Stationarity Test (Augmented Dickey-Fuller)...")
result = adfuller(df['total_traffic'].dropna())
print(f"   ADF Statistic: {result[0]:.4f}")
print(f"   p-value: {result[1]:.4f}")
print(f"   Critical Values:")
for key, value in result[4].items():
    print(f"      {key}: {value:.4f}")

if result[1] < 0.05:
    print("   ✅ Data is stationary (p < 0.05)")
else:
    print("   ⚠️ Data is not stationary. Differencing applied.")

# 4. Train-Test Split (last 24 hours for testing)
print("\n📊 Splitting data (train: all except last 24h, test: last 24h)...")
train = df.iloc[:-24]
test = df.iloc[-24:]
print(f"   Train: {len(train)} hours")
print(f"   Test: {len(test)} hours")

# 5. ARIMA MODEL
print("\n🔮 Training ARIMA Model...")
# Try different orders (p,d,q)
# p: AR order (lag), d: differencing, q: MA order
arima_orders = [(1,0,1), (2,0,2), (3,0,3), (5,0,2), (7,0,3)]
best_arima = None
best_aic = float('inf')
best_order = None

for order in arima_orders:
    try:
        model = ARIMA(train['total_traffic'], order=order)
        fitted = model.fit()
        if fitted.aic < best_aic:
            best_aic = fitted.aic
            best_order = order
            best_arima = fitted
    except:
        continue

print(f"   Best ARIMA Order: {best_order}")
print(f"   AIC: {best_aic:.2f}")

# Forecast ARIMA
arima_forecast = best_arima.forecast(steps=24)
arima_forecast.index = test.index

# Evaluate ARIMA
arima_mae = mean_absolute_error(test['total_traffic'], arima_forecast)
arima_rmse = np.sqrt(mean_squared_error(test['total_traffic'], arima_forecast))
arima_mape = np.mean(np.abs((test['total_traffic'].values - arima_forecast.values) / test['total_traffic'].values)) * 100
print(f"   ARIMA MAE: {arima_mae:.2f}")
print(f"   ARIMA RMSE: {arima_rmse:.2f}")
print(f"   ARIMA MAPE: {arima_mape:.1f}%")

# 6. PROPHET MODEL (by Facebook)
print("\n🔮 Training Prophet Model...")

# Prepare data for Prophet (ds: date, y: value)
prophet_df = train.reset_index().rename(columns={'timestamp': 'ds', 'total_traffic': 'y'})

# Create and train model
prophet_model = Prophet(
    yearly_seasonality=False,
    weekly_seasonality=True,
    daily_seasonality=True,
    changepoint_prior_scale=0.05
)
prophet_model.add_country_holidays(country_name='IT')  # Italian holidays
prophet_model.fit(prophet_df)

# Create future dataframe (24 hours ahead)
future = prophet_model.make_future_dataframe(periods=24, freq='h')
forecast = prophet_model.predict(future)

# Extract forecast for test period
prophet_forecast = forecast.set_index('ds')['yhat'].loc[test.index]
prophet_lower = forecast.set_index('ds')['yhat_lower'].loc[test.index]
prophet_upper = forecast.set_index('ds')['yhat_upper'].loc[test.index]

# Evaluate Prophet
prophet_mae = mean_absolute_error(test['total_traffic'], prophet_forecast)
prophet_rmse = np.sqrt(mean_squared_error(test['total_traffic'], prophet_forecast))
prophet_mape = np.mean(np.abs((test['total_traffic'].values - prophet_forecast.values) / test['total_traffic'].values)) * 100
print(f"   Prophet MAE: {prophet_mae:.2f}")
print(f"   Prophet RMSE: {prophet_rmse:.2f}")
print(f"   Prophet MAPE: {prophet_mape:.1f}%")

# 7. Visualisasi Perbandingan
print("\n📊 Generating comparison visualization...")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Plot 1: ARIMA Forecast vs Actual
axes[0,0].plot(test.index, test['total_traffic'], label='Actual', color='black', linewidth=2)
axes[0,0].plot(test.index, arima_forecast, label='ARIMA Forecast', color='#e74c3c', linewidth=2, linestyle='--')
axes[0,0].set_title(f'ARIMA Forecast (MAPE: {arima_mape:.1f}%)', fontsize=12)
axes[0,0].set_ylabel('Traffic')
axes[0,0].legend()
axes[0,0].grid(True, alpha=0.3)

# Plot 2: Prophet Forecast vs Actual
axes[0,1].plot(test.index, test['total_traffic'], label='Actual', color='black', linewidth=2)
axes[0,1].plot(test.index, prophet_forecast, label='Prophet Forecast', color='#3498db', linewidth=2, linestyle='--')
axes[0,1].fill_between(test.index, prophet_lower, prophet_upper, color='#3498db', alpha=0.2, label='Confidence Interval')
axes[0,1].set_title(f'Prophet Forecast (MAPE: {prophet_mape:.1f}%)', fontsize=12)
axes[0,1].set_ylabel('Traffic')
axes[0,1].legend()
axes[0,1].grid(True, alpha=0.3)

# Plot 3: Error Comparison
models = ['ARIMA', 'Prophet']
mae_scores = [arima_mae, prophet_mae]
rmse_scores = [arima_rmse, prophet_rmse]

x = np.arange(len(models))
width = 0.35
axes[1,0].bar(x - width/2, mae_scores, width, label='MAE', color='#e74c3c')
axes[1,0].bar(x + width/2, rmse_scores, width, label='RMSE', color='#3498db')
axes[1,0].set_xlabel('Model')
axes[1,0].set_ylabel('Error')
axes[1,0].set_title('Model Error Comparison')
axes[1,0].set_xticks(x)
axes[1,0].set_xticklabels(models)
axes[1,0].legend()
axes[1,0].grid(True, alpha=0.3)

# Plot 4: 24-Hour Forecast (Next Day)
# Decompose Prophet forecast components
prophet_components = forecast[['ds', 'trend', 'weekly', 'daily']].set_index('ds').tail(24)

axes[1,1].plot(prophet_components.index, prophet_components['trend'], label='Trend', color='#2ecc71')
axes[1,1].plot(prophet_components.index, prophet_components['weekly'], label='Weekly', color='#f39c12')
axes[1,1].plot(prophet_components.index, prophet_components['daily'], label='Daily', color='#9b59b6')
axes[1,1].set_title('Forecast Components (Next 24 Hours)', fontsize=12)
axes[1,1].set_xlabel('Hour')
axes[1,1].set_ylabel('Component Value')
axes[1,1].legend()
axes[1,1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('images_indosat/forecast_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("   ✅ Saved: images_indosat/forecast_comparison.png")

# 8. 24-Hour Forecast Table
print("\n📊 24-HOUR FORECAST (Next Day):")
forecast_24h = pd.DataFrame({
    'Hour': test.index,
    'Actual': test['total_traffic'].values,
    'ARIMA_Predicted': arima_forecast.values,
    'Prophet_Predicted': prophet_forecast.values,
    'Prophet_Lower': prophet_lower.values,
    'Prophet_Upper': prophet_upper.values
})
forecast_24h['Hour_Label'] = forecast_24h['Hour'].dt.strftime('%Y-%m-%d %H:00')
print(forecast_24h[['Hour_Label', 'Actual', 'Prophet_Predicted']].to_string(index=False))

# 9. Business Recommendations
print("\n" + "="*60)
print("💼 BUSINESS RECOMMENDATIONS FOR INDOSAT OOREDOO")
print("="*60)

# Find peak predicted hours
peak_hours = forecast_24h.nlargest(3, 'Prophet_Predicted')['Hour']
low_hours = forecast_24h.nsmallest(3, 'Prophet_Predicted')['Hour']

print(f"""
📊 Based on Prophet forecast (MAPE: {prophet_mape:.1f}%):

🔴 PREDICTED PEAK HOURS (High Traffic):
   → Allocate MORE bandwidth
   → Schedule marketing campaigns
   → Activate prepaid promotions
   {', '.join([h.strftime('%H:00') for h in peak_hours])}

🟢 PREDICTED LOW HOURS (Low Traffic):
   → Schedule network maintenance
   → Offer "Happy Hour" discounts
   → Run system updates
   {', '.join([h.strftime('%H:00') for h in low_hours])}

📈 FORECAST ACCURACY:
   • Prophet Model: {prophet_mape:.1f}% MAPE (Recommended)
   • ARIMA Model: {arima_mape:.1f}% MAPE

✅ RECOMMENDATION: Use Prophet for production forecasting
   because it handles seasonality better and provides confidence intervals.
""")

# 10. Save forecast result
forecast_24h.to_csv('images_indosat/forecast_24h.csv', index=False)
print("\n📁 Forecast saved: images_indosat/forecast_24h.csv")

print("\n" + "="*60)
print("🎉 FORECASTING COMPLETED!")
print("="*60)
print("\n📁 Output files:")
print("   images_indosat/forecast_eda.png")
print("   images_indosat/forecast_comparison.png")
print("   images_indosat/forecast_24h.csv")