import sys
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_dependencies():
    required_packages = {
        'pandas': 'pandas',
        'plotly.express': 'plotly',
        'folium': 'folium',
        'numpy': 'numpy'
    }
    
    for import_name, package_name in required_packages.items():
        try:
            __import__(import_name)
            logger.info(f"Successfully imported {import_name}")
        except ImportError:
            logger.error(f"Failed to import {import_name}")
            print(f"\nPlease install {package_name} using:")
            print(f"pip install {package_name}")
            sys.exit(1)

def load_and_clean_data(filepath):
    try:
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            print("\nError: building_permits.csv not found!")
            print("Please download the dataset from:")
            print("https://data.seattle.gov/Permitting/Building-Permits/76t5-zqzr")
            sys.exit(1)
        
        logger.info(f"Attempting to load data from {filepath}")
        df = pd.read_csv(filepath)
        
        # Convert AppliedDate to datetime
        logger.info("Converting AppliedDate to datetime")
        df['AppliedDate'] = pd.to_datetime(df['AppliedDate'])
        
        # Convert EstProjectCost to numeric, handling any non-numeric values
        df['EstProjectCost'] = pd.to_numeric(df['EstProjectCost'], errors='coerce')
        
        # Filter out rows with missing coordinates
        initial_rows = len(df)
        df = df.dropna(subset=['Latitude', 'Longitude'])
        dropped_rows = initial_rows - len(df)
        logger.info(f"Dropped {dropped_rows} rows with missing coordinates")
        
        # Filter to recent permits
        two_years_ago = datetime.now() - pd.DateOffset(years=2)
        df = df[df['AppliedDate'] > two_years_ago]
        logger.info(f"Filtered to {len(df)} permits from the last 2 years")
        
        return df
        
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        raise

def create_time_series(df):
    try:
        logger.info("Creating time series visualization")
        # Group by month and count permits
        monthly_permits = df.resample('ME', on='AppliedDate').size().reset_index()
        monthly_permits.columns = ['Date', 'Number of Permits']
        
        # Create interactive time series with Plotly
        fig = px.line(monthly_permits, 
                     x='Date', 
                     y='Number of Permits',
                     title='Building Permits Over Time in Seattle')
        
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Number of Permits Issued",
            hovermode='x'
        )
        
        # Save as HTML file
        fig.write_html("visualizations/permits_time.html")
        logger.info("Time series visualization saved")
        
    except Exception as e:
        logger.error(f"Error creating time series: {str(e)}")
        raise

def create_permit_type_analysis(df):
    try:
        logger.info("Creating permit type analysis")
        
        # Create permit type distribution
        permit_counts = df['PermitTypeMapped'].value_counts()
        
        fig = px.pie(values=permit_counts.values, 
                    names=permit_counts.index,
                    title='Distribution of Permit Types')
        
        fig.write_html("visualizations/permit_types.html")
        
        # Create cost analysis by permit type
        cost_by_type = df.groupby('PermitTypeMapped')['EstProjectCost'].agg(['mean', 'median', 'count'])
        cost_by_type = cost_by_type.sort_values('mean', ascending=False)
        
        fig2 = px.bar(cost_by_type.reset_index(), 
                     x='PermitTypeMapped',
                     y='mean',
                     title='Average Project Cost by Permit Type',
                     labels={'mean': 'Average Cost ($)', 'PermitTypeMapped': 'Permit Type'})
        
        fig2.write_html("visualizations/cost_analysis.html")
        logger.info("Permit type analysis saved")
        
    except Exception as e:
        logger.error(f"Error creating permit type analysis: {str(e)}")
        raise

def create_map(df):
    try:
        logger.info("Creating map visualization")
        # Create base map centered on Seattle
        seattle_map = folium.Map(
            location=[47.6062, -122.3321],
            zoom_start=12,
            tiles='CartoDB positron'
        )
        
        # Create heatmap data
        heat_data = df[['Latitude', 'Longitude']].values.tolist()
        
        # Add heatmap layer
        HeatMap(heat_data,
               radius=15,
               blur=10,
               max_zoom=13).add_to(seattle_map)
        
        # Add markers for high-value permits
        large_permits = df[df['EstProjectCost'] > df['EstProjectCost'].quantile(0.95)]
        logger.info(f"Adding {len(large_permits)} markers for large permits")
        
        for idx, row in large_permits.iterrows():
            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=5,
                color='red',
                fill=True,
                popup=f"Cost: ${row['EstProjectCost']:,.2f}<br>Type: {row['PermitTypeMapped']}<br>Address: {row['OriginalAddress1']}"
            ).add_to(seattle_map)
        
        # Create output directory if it doesn't exist
        os.makedirs('visualizations', exist_ok=True)
        
        # Save map
        seattle_map.save('visualizations/permits_map.html')
        logger.info("Map visualization saved")
        
    except Exception as e:
        logger.error(f"Error creating map: {str(e)}")
        raise

def generate_summary_stats(df):
    """Generate summary statistics for the README"""
    try:
        logger.info("Generating summary statistics")
        
        stats = {
            'total_permits': len(df),
            'total_value': df['EstProjectCost'].sum(),
            'avg_value': df['EstProjectCost'].mean(),
            'median_value': df['EstProjectCost'].median(),
            'most_common_type': df['PermitTypeMapped'].mode().iloc[0],
            'date_range': f"{df['AppliedDate'].min().strftime('%Y-%m-%d')} to {df['AppliedDate'].max().strftime('%Y-%m-%d')}"
        }
        
        # Write stats to file
        with open('statistics.md', 'w') as f:
            f.write("# Seattle Building Permits - Summary Statistics\n\n")
            f.write(f"## Date Range: {stats['date_range']}\n\n")
            f.write(f"- Total Permits: {stats['total_permits']:,}\n")
            f.write(f"- Total Project Value: ${stats['total_value']:,.2f}\n")
            f.write(f"- Average Project Value: ${stats['avg_value']:,.2f}\n")
            f.write(f"- Median Project Value: ${stats['median_value']:,.2f}\n")
            f.write(f"- Most Common Permit Type: {stats['most_common_type']}\n")
        
        logger.info("Summary statistics saved to statistics.md")
        return stats
    
    except Exception as e:
        logger.error(f"Error generating summary stats: {str(e)}")
        raise

def main():
    check_dependencies()
    
    import pandas as pd
    import plotly.express as px
    import folium
    from folium.plugins import HeatMap
    import numpy as np
    from datetime import datetime
    
    try:
        # Create visualizations directory
        os.makedirs('visualizations', exist_ok=True)
        
        # Load and process data
        df = load_and_clean_data('building_permits.csv')
        
        # Create visualizations
        create_time_series(df)
        create_permit_type_analysis(df)
        create_map(df)
        
        # Generate summary statistics
        stats = generate_summary_stats(df)
        
        print("\nSuccessfully created visualizations in 'visualizations' directory:")
        print("1. permits_time.html - Interactive time series visualization")
        print("2. permits_map.html - Interactive map with permit locations")
        print("3. permit_types.html - Distribution of permit types")
        print("4. cost_analysis.html - Cost analysis by permit type")
        print("\nSummary statistics saved to statistics.md")
        
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()