# -*- coding: utf-8 -*-
"""kode

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1abAkBTLyalBVLI2QiXsgqoHlH04aOOVv
"""

# ===============================
# SISTEM PEMANTAUAN KUALITAS UDARA
# Google Colab Implementation
# ===============================

# Install required packages
!pip install openaq pandas numpy scikit-learn matplotlib seaborn plotly requests schedule python-dotenv imbalanced-learn tensorflow

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import requests
import json
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Machine Learning imports
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.utils.class_weight import compute_class_weight
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler
from imblearn.pipeline import Pipeline as ImbPipeline

# TensorFlow for deep learning
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, LSTM
from tensorflow.keras.callbacks import EarlyStopping

# ===============================
# CONFIGURATION
# ===============================

class Config:
    OPENAQ_API_BASE = "https://api.openaq.org/v2"
    LOCATIONS = [
        "Semarang",
        "Jakarta",
        "Surabaya",
        "Bandung",
        "Medan"
    ]
    PARAMETERS = ["pm25", "pm10", "co2", "temperature", "humidity"]
    AQI_BREAKPOINTS = {
        'pm25': [(0, 12), (12.1, 35.4), (35.5, 55.4), (55.5, 150.4), (150.5, 250.4), (250.5, 500.4)],
        'pm10': [(0, 54), (55, 154), (155, 254), (255, 354), (355, 424), (425, 604)]
    }
    AQI_CATEGORIES = ["Good", "Moderate", "Unhealthy for Sensitive", "Unhealthy", "Very Unhealthy", "Hazardous"]
    AQI_COLORS = ["#00E400", "#FFFF00", "#FF7E00", "#FF0000", "#8F3F97", "#7E0023"]

# ===============================
# DATA COLLECTION CLASS
# ===============================

class OpenAQDataCollector:
    def __init__(self):
        self.base_url = Config.OPENAQ_API_BASE
        self.session = requests.Session()

    def get_latest_measurements(self, location="Semarang", limit=1000):
        """Fetch latest air quality measurements"""
        url = f"{self.base_url}/measurements"
        params = {
            'city': location,
            'limit': limit,
            'order_by': 'datetime',
            'sort': 'desc'
        }

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            return None

    def get_historical_data(self, location="Semarang", days=30):
        """Fetch historical data for specified days"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        url = f"{self.base_url}/measurements"
        params = {
            'city': location,
            'date_from': start_date.strftime('%Y-%m-%d'),
            'date_to': end_date.strftime('%Y-%m-%d'),
            'limit': 10000,
            'order_by': 'datetime',
            'sort': 'desc'
        }

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching historical data: {e}")
            return None

# ===============================
# DATA PROCESSING CLASS
# ===============================

class DataProcessor:
    def __init__(self):
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()

    def calculate_aqi(self, concentration, parameter):
        """Calculate AQI based on concentration and parameter type"""
        if parameter not in Config.AQI_BREAKPOINTS:
            return None

        breakpoints = Config.AQI_BREAKPOINTS[parameter]
        aqi_values = [50, 100, 150, 200, 300, 500]

        for i, (low, high) in enumerate(breakpoints):
            if low <= concentration <= high:
                aqi_low = 0 if i == 0 else aqi_values[i-1] + 1
                aqi_high = aqi_values[i]

                aqi = ((aqi_high - aqi_low) / (high - low)) * (concentration - low) + aqi_low
                return round(aqi)

        return 500  # Hazardous level

    def get_aqi_category(self, aqi):
        """Get AQI category based on AQI value"""
        if aqi <= 50:
            return 0, "Good"
        elif aqi <= 100:
            return 1, "Moderate"
        elif aqi <= 150:
            return 2, "Unhealthy for Sensitive"
        elif aqi <= 200:
            return 3, "Unhealthy"
        elif aqi <= 300:
            return 4, "Very Unhealthy"
        else:
            return 5, "Hazardous"

    def process_openaq_data(self, raw_data):
        """Process raw OpenAQ data into structured format"""
        if not raw_data or 'results' not in raw_data:
            return pd.DataFrame()

        processed_data = []

        for measurement in raw_data['results']:
            try:
                data_point = {
                    'datetime': pd.to_datetime(measurement['date']['utc']),
                    'location': measurement['location'],
                    'city': measurement['city'],
                    'country': measurement['country'],
                    'parameter': measurement['parameter'],
                    'value': measurement['value'],
                    'unit': measurement['unit']
                }
                processed_data.append(data_point)
            except KeyError as e:
                print(f"Missing key in measurement: {e}")
                continue

        df = pd.DataFrame(processed_data)

        if df.empty:
            return df

        # Pivot data to have parameters as columns
        df_pivot = df.pivot_table(
            index=['datetime', 'location', 'city', 'country'],
            columns='parameter',
            values='value',
            aggfunc='mean'
        ).reset_index()

        # Calculate AQI for PM2.5 and PM10
        if 'pm25' in df_pivot.columns:
            df_pivot['pm25_aqi'] = df_pivot['pm25'].apply(
                lambda x: self.calculate_aqi(x, 'pm25') if pd.notna(x) else None
            )

        if 'pm10' in df_pivot.columns:
            df_pivot['pm10_aqi'] = df_pivot['pm10'].apply(
                lambda x: self.calculate_aqi(x, 'pm10') if pd.notna(x) else None
            )

        # Calculate overall AQI (maximum of PM2.5 and PM10 AQI)
        aqi_columns = [col for col in df_pivot.columns if col.endswith('_aqi')]
        if aqi_columns:
            df_pivot['overall_aqi'] = df_pivot[aqi_columns].max(axis=1)
            df_pivot['aqi_category_num'], df_pivot['aqi_category'] = zip(
                *df_pivot['overall_aqi'].apply(self.get_aqi_category)
            )

        return df_pivot

    def create_features(self, df):
        """Create additional features for ML model"""
        if df.empty:
            return df

        # Time-based features
        df['hour'] = df['datetime'].dt.hour
        df['day_of_week'] = df['datetime'].dt.dayofweek
        df['month'] = df['datetime'].dt.month
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)

        # Lag features
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for col in ['pm25', 'pm10', 'co2']:
            if col in df.columns:
                df[f'{col}_lag1'] = df[col].shift(1)
                df[f'{col}_lag24'] = df[col].shift(24)  # 24 hours ago

        # Rolling statistics
        for col in ['pm25', 'pm10']:
            if col in df.columns:
                df[f'{col}_rolling_mean_24h'] = df[col].rolling(window=24, min_periods=1).mean()
                df[f'{col}_rolling_std_24h'] = df[col].rolling(window=24, min_periods=1).std()

        return df

# ===============================
# DATA AUGMENTATION CLASS
# ===============================

class DataAugmentation:
    def __init__(self):
        self.smote = SMOTE(random_state=42)
        self.undersampler = RandomUnderSampler(random_state=42)

    def augment_time_series(self, df, noise_factor=0.1):
        """Add noise to time series data for augmentation"""
        augmented_data = []

        for category in df['aqi_category_num'].unique():
            category_data = df[df['aqi_category_num'] == category].copy()

            # Add noise to numerical features
            numeric_columns = category_data.select_dtypes(include=[np.number]).columns
            numeric_columns = [col for col in numeric_columns if col not in ['aqi_category_num']]

            for _ in range(3):  # Create 3 augmented versions
                augmented = category_data.copy()
                for col in numeric_columns:
                    if col in augmented.columns and augmented[col].notna().any():
                        noise = np.random.normal(0, noise_factor * augmented[col].std(), len(augmented))
                        augmented[col] = augmented[col] + noise

                augmented_data.append(augmented)

        return pd.concat([df] + augmented_data, ignore_index=True)

    def balance_classes(self, X, y):
        """Balance classes using SMOTE and undersampling"""
        # First apply SMOTE to oversample minority classes
        X_resampled, y_resampled = self.smote.fit_resample(X, y)

        # Then apply undersampling to reduce majority class
        X_balanced, y_balanced = self.undersampler.fit_resample(X_resampled, y_resampled)

        return X_balanced, y_balanced

# ===============================
# MACHINE LEARNING MODELS
# ===============================

class AirQualityMLModel:
    def __init__(self):
        self.models = {
            'random_forest': RandomForestClassifier(n_estimators=100, random_state=42),
            'gradient_boosting': GradientBoostingClassifier(n_estimators=100, random_state=42),
            'neural_network': None  # Will be initialized in prepare_features
        }
        self.scaler = StandardScaler()
        self.best_model = None
        self.feature_importance = None
        self.input_shape = None

    def _build_neural_network(self, input_shape):
        """Build neural network model with dynamic input shape"""
        model = Sequential([
            Dense(128, activation='relu', input_shape=(input_shape,)),
            Dropout(0.3),
            Dense(64, activation='relu'),
            Dropout(0.3),
            Dense(32, activation='relu'),
            Dense(6, activation='softmax')  # 6 AQI categories
        ])

        model.compile(
            optimizer='adam',
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )

        return model

    def prepare_features(self, df):
        """Prepare features for ML model"""
        # Select relevant features
        feature_columns = [
            'pm25', 'pm10', 'co2', 'temperature', 'humidity',
            'hour', 'day_of_week', 'month', 'is_weekend'
        ]

        # Add available lag features
        for col in df.columns:
            if any(lag in col for lag in ['_lag1', '_lag24', '_rolling_mean', '_rolling_std']):
                feature_columns.append(col)

        # Filter existing columns
        feature_columns = [col for col in feature_columns if col in df.columns]

        X = df[feature_columns].copy()
        y = df['aqi_category_num'].copy() if 'aqi_category_num' in df.columns else None

        # Handle missing values
        X = X.fillna(X.mean())

        # Initialize neural network with correct input shape
        self.input_shape = len(feature_columns)
        self.models['neural_network'] = self._build_neural_network(self.input_shape)

        return X, y, feature_columns

    def train_models(self, X_train, y_train, X_test, y_test, use_class_weights=True):
        """Train multiple ML models with class weights"""
        # First ensure neural network is initialized
        if self.models['neural_network'] is None:
            self.input_shape = X_train.shape[1]
            self.models['neural_network'] = self._build_neural_network(self.input_shape)

        results = {}

        # Calculate class weights
        if use_class_weights:
            class_weights = compute_class_weight(
                'balanced',
                classes=np.unique(y_train),
                y=y_train
            )
            weight_dict = dict(zip(np.unique(y_train), class_weights))
        else:
            weight_dict = None

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train Random Forest
        if weight_dict:
            self.models['random_forest'].set_params(class_weight=weight_dict)

        self.models['random_forest'].fit(X_train, y_train)
        rf_pred = self.models['random_forest'].predict(X_test)
        results['random_forest'] = {
            'accuracy': accuracy_score(y_test, rf_pred),
            'predictions': rf_pred,
            'model': self.models['random_forest']
        }

        # Train Gradient Boosting
        self.models['gradient_boosting'].fit(X_train, y_train)
        gb_pred = self.models['gradient_boosting'].predict(X_test)
        results['gradient_boosting'] = {
            'accuracy': accuracy_score(y_test, gb_pred),
            'predictions': gb_pred,
            'model': self.models['gradient_boosting']
        }

        # Train Neural Network
        early_stopping = EarlyStopping(patience=10, restore_best_weights=True)

        if weight_dict:
            sample_weights = np.array([weight_dict[y] for y in y_train])
            history = self.models['neural_network'].fit(
                X_train_scaled, y_train,
                validation_data=(X_test_scaled, y_test),
                epochs=100,
                batch_size=32,
                sample_weight=sample_weights,
                callbacks=[early_stopping],
                verbose=0
            )
        else:
            history = self.models['neural_network'].fit(
                X_train_scaled, y_train,
                validation_data=(X_test_scaled, y_test),
                epochs=100,
                batch_size=32,
                callbacks=[early_stopping],
                verbose=0
            )

        nn_pred = np.argmax(self.models['neural_network'].predict(X_test_scaled), axis=1)
        results['neural_network'] = {
            'accuracy': accuracy_score(y_test, nn_pred),
            'predictions': nn_pred,
            'model': self.models['neural_network'],
            'history': history
        }

        # Select best model
        best_model_name = max(results.keys(), key=lambda k: results[k]['accuracy'])
        self.best_model = results[best_model_name]['model']

        # Feature importance (for tree-based models)
        if best_model_name in ['random_forest', 'gradient_boosting']:
            self.feature_importance = self.best_model.feature_importances_

        return results, best_model_name

    def predict_aqi_category(self, features):
        """Predict AQI category for new data"""
        if self.best_model is None:
            raise ValueError("Model not trained yet!")

        # Scale features if neural network
        if hasattr(self.best_model, 'predict_proba'):
            prediction = self.best_model.predict(features)
        else:
            features_scaled = self.scaler.transform(features)
            prediction = np.argmax(self.best_model.predict(features_scaled), axis=1)

        return prediction


# ===============================
# VISUALIZATION CLASS
# ===============================

class AirQualityVisualizer:
    def __init__(self):
        self.colors = Config.AQI_COLORS
        self.categories = Config.AQI_CATEGORIES

    def plot_aqi_trend(self, df):
        """Plot AQI trend over time"""
        fig = go.Figure()

        if 'overall_aqi' in df.columns:
            fig.add_trace(go.Scatter(
                x=df['datetime'],
                y=df['overall_aqi'],
                mode='lines+markers',
                name='Overall AQI',
                line=dict(color='blue', width=2),
                marker=dict(size=4)
            ))

        # Add AQI category background colors
        for i, (category, color) in enumerate(zip(self.categories, self.colors)):
            y_min = [0, 51, 101, 151, 201, 301][i]
            y_max = [50, 100, 150, 200, 300, 500][i]

            fig.add_shape(
                type="rect",
                x0=df['datetime'].min(),
                y0=y_min,
                x1=df['datetime'].max(),
                y1=y_max,
                fillcolor=color,
                opacity=0.1,
                layer="below",
                line_width=0
            )

        fig.update_layout(
            title="Air Quality Index Trend",
            xaxis_title="Date",
            yaxis_title="AQI",
            hovermode='x unified',
            template='plotly_white'
        )

        return fig

    def plot_parameter_comparison(self, df):
        """Plot comparison of air quality parameters"""
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('PM2.5', 'PM10', 'CO2', 'Temperature & Humidity'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": True}]]
        )

        # PM2.5
        if 'pm25' in df.columns:
            fig.add_trace(
                go.Scatter(x=df['datetime'], y=df['pm25'], name='PM2.5', line=dict(color='red')),
                row=1, col=1
            )

        # PM10
        if 'pm10' in df.columns:
            fig.add_trace(
                go.Scatter(x=df['datetime'], y=df['pm10'], name='PM10', line=dict(color='orange')),
                row=1, col=2
            )

        # CO2
        if 'co2' in df.columns:
            fig.add_trace(
                go.Scatter(x=df['datetime'], y=df['co2'], name='CO2', line=dict(color='green')),
                row=2, col=1
            )

        # Temperature & Humidity
        if 'temperature' in df.columns:
            fig.add_trace(
                go.Scatter(x=df['datetime'], y=df['temperature'], name='Temperature', line=dict(color='blue')),
                row=2, col=2
            )

        if 'humidity' in df.columns:
            fig.add_trace(
                go.Scatter(x=df['datetime'], y=df['humidity'], name='Humidity', line=dict(color='purple')),
                row=2, col=2, secondary_y=True
            )

        fig.update_layout(
            title="Air Quality Parameters Comparison",
            height=600,
            template='plotly_white'
        )

        return fig

    def plot_model_performance(self, results):
        """Plot model performance comparison"""
        models = list(results.keys())
        accuracies = [results[model]['accuracy'] for model in models]

        fig = go.Figure(data=[
            go.Bar(
                x=models,
                y=accuracies,
                marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1']
            )
        ])

        fig.update_layout(
            title="Model Performance Comparison",
            xaxis_title="Model",
            yaxis_title="Accuracy",
            template='plotly_white'
        )

        return fig

# ===============================
# CONFIGURATION
# ===============================

class Config:
    OPENAQ_API_BASE = "https://api.openaq.org/v2"

    def __init__(self):
        self.LOCATIONS = self._get_auto_locations()
        self.current_date = datetime.now()

    def _get_auto_locations(self):
        """Get locations automatically with fallback"""
        try:
            # Try to get current city from IP (works in local environment)
            response = requests.get('https://ipinfo.io/json', timeout=3)
            current_city = response.json().get('city', 'Jakarta')

            # Combine with major Indonesian cities
            return [current_city] + ["Jakarta", "Surabaya", "Bandung", "Medan"]
        except:
            # Fallback to major Indonesian cities
            return ["Jakarta", "Surabaya", "Bandung", "Medan", "Semarang"]

    PARAMETERS = ["pm25", "pm10", "co2", "temperature", "humidity"]
    AQI_BREAKPOINTS = {
        'pm25': [(0, 12), (12.1, 35.4), (35.5, 55.4), (55.5, 150.4), (150.5, 250.4), (250.5, 500.4)],
        'pm10': [(0, 54), (55, 154), (155, 254), (255, 354), (355, 424), (425, 604)]
    }
    AQI_CATEGORIES = ["Good", "Moderate", "Unhealthy for Sensitive", "Unhealthy", "Very Unhealthy", "Hazardous"]
    AQI_COLORS = ["#00E400", "#FFFF00", "#FF7E00", "#FF0000", "#8F3F97", "#7E0023"]

# ===============================
# DATA COLLECTION CLASS (Updated)
# ===============================

class OpenAQDataCollector:
    def __init__(self):
        self.base_url = Config().OPENAQ_API_BASE
        self.session = requests.Session()
        self.config = Config()

    def get_historical_data(self, location=None, days=30):
        """Fetch historical data with automatic date range"""
        if location is None:
            location = self.config.LOCATIONS[0]  # Use first location

        end_date = self.config.current_date
        start_date = end_date - timedelta(days=days)

        print(f"📅 Fetching data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"📍 Location: {location}")

        url = f"{self.base_url}/measurements"
        params = {
            'city': location,
            'date_from': start_date.strftime('%Y-%m-%d'),
            'date_to': end_date.strftime('%Y-%m-%d'),
            'limit': 10000,
            'order_by': 'datetime',
            'sort': 'desc'
        }

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching historical data: {e}")
            return None

# ===============================
# MAIN EXECUTION (Updated)
# ===============================

def main():
    print("🌍 Starting Air Quality Monitoring System...")

    # Initialize configuration
    config = Config()
    print(f"🔄 Auto-detected locations: {config.LOCATIONS}")
    print(f"📅 Current date: {config.current_date.strftime('%Y-%m-%d')}")

    # Initialize components
    collector = OpenAQDataCollector()
    processor = DataProcessor()
    augmentation = DataAugmentation()
    ml_model = AirQualityMLModel()
    visualizer = AirQualityVisualizer()

    # Collect data (automatically uses first location)
    print("\n📊 Collecting data from OpenAQ...")
    raw_data = collector.get_historical_data(days=30)  # No location specified

    if raw_data is None:
        print("❌ Failed to collect data. Using sample data...")
        # Generate sample data with current date
        end_date = config.current_date
        start_date = end_date - timedelta(days=30)
        dates = pd.date_range(start=start_date, end=end_date, freq='H')

        sample_data = {
            'datetime': dates,
            'location': 'Sample Location',
            'city': config.LOCATIONS[0],  # Use first detected location
            'country': 'Indonesia',
            'pm25': np.random.lognormal(3, 0.5, len(dates)),
            'pm10': np.random.lognormal(3.5, 0.5, len(dates)),
            'co2': np.random.normal(400, 50, len(dates)),
            'temperature': np.random.normal(28, 5, len(dates)),
            'humidity': np.random.normal(65, 10, len(dates))
        }
        df = pd.DataFrame(sample_data)

        # Calculate AQI
        df['pm25_aqi'] = df['pm25'].apply(lambda x: processor.calculate_aqi(x, 'pm25'))
        df['pm10_aqi'] = df['pm10'].apply(lambda x: processor.calculate_aqi(x, 'pm10'))
        df['overall_aqi'] = df[['pm25_aqi', 'pm10_aqi']].max(axis=1)
        df['aqi_category_num'], df['aqi_category'] = zip(*df['overall_aqi'].apply(processor.get_aqi_category))
    else:
        # Process real data
        print("🔄 Processing data...")
        df = processor.process_openaq_data(raw_data)

    # Rest of the main function remains the same...
    if df.empty:
        print("❌ No data available for processing.")
        return

    # Create features
    print("🔧 Creating features...")
    df = processor.create_features(df)

    # Data augmentation
    print("🎯 Applying data augmentation...")
    df_augmented = augmentation.augment_time_series(df)

    # Prepare ML features
    print("🤖 Preparing ML model...")
    X, y, feature_columns = ml_model.prepare_features(df_augmented)

    if y is None or X.empty:
        print("❌ Insufficient data for ML training.")
        return

    # Apply class balancing
    X_balanced, y_balanced = augmentation.balance_classes(X, y)

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X_balanced, y_balanced, test_size=0.2, random_state=42, stratify=y_balanced
    )

    # Train models
    print("🎓 Training ML models...")
    results, best_model_name = ml_model.train_models(X_train, y_train, X_test, y_test)

    # Display results
    print("\n📈 Model Performance:")
    for model_name, result in results.items():
        print(f"{model_name}: {result['accuracy']:.4f}")

    print(f"\n🏆 Best Model: {best_model_name}")

    # Create visualizations
    print("📊 Creating visualizations...")

    # AQI trend plot
    aqi_fig = visualizer.plot_aqi_trend(df)
    aqi_fig.show()

    # Parameters comparison
    param_fig = visualizer.plot_parameter_comparison(df)
    param_fig.show()

    # Model performance
    perf_fig = visualizer.plot_model_performance(results)
    perf_fig.show()

    # Save processed data
    df.to_csv('processed_air_quality_data.csv', index=False)
    print("💾 Data saved to 'processed_air_quality_data.csv'")

    # Save model
    import joblib
    joblib.dump(ml_model.best_model, 'best_air_quality_model.pkl')
    joblib.dump(ml_model.scaler, 'feature_scaler.pkl')
    print("💾 Model saved to 'best_air_quality_model.pkl'")

    print("✅ Air Quality Monitoring System setup complete!")

    return df, ml_model, results

# Run the main function
if __name__ == "__main__":
    df, model, results = main()
from google.colab import files
from nbformat import read
from nbconvert import PythonExporter

# Upload notebook (.ipynb) ke Colab
uploaded = files.upload()
ipynb_file = list(uploaded.keys())[0]

# Konversi ke .py
with open(ipynb_file, 'r', encoding='utf-8') as f:
    nb = read(f, as_version=4)

exporter = PythonExporter()
py_code, _ = exporter.from_notebook_node(nb)

# Download file .py
with open('converted.py', 'w', encoding='utf-8') as f:
    f.write(py_code)

files.download('converted.py')  # Auto-download