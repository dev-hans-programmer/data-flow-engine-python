"""
Sample pipeline configurations to demonstrate system capabilities
"""
import asyncio
import json
from app.postgres_db import postgres_db
from app.models import Pipeline, PipelineStatus, LoadStep, TransformStep, SaveStep

async def create_sample_pipelines():
    """Create sample pipelines to demonstrate the system"""
    
    # Sample Pipeline 1: Data Cleaning and Analysis
    data_cleaning_pipeline = Pipeline(
        id="sample-data-cleaning",
        name="Sample Data Cleaning Pipeline",
        description="Demonstrates loading CSV data, cleaning, and transforming it",
        status=PipelineStatus.ACTIVE,
        steps=[
            LoadStep(
                id="load-csv",
                name="Load CSV Data",
                source_path="uploads/test_data.csv",
                format="csv"
            ),
            TransformStep(
                id="clean-data",
                name="Clean Data",
                operations=[{
                    "type": "drop_na",
                    "columns": ["name", "age"]
                }]
            ),
            TransformStep(
                id="add-category",
                name="Add Category Column",
                operations=[{
                    "type": "add_column",
                    "column_name": "category",
                    "value": "processed"
                }]
            ),
            SaveStep(
                id="save-cleaned",
                name="Save Cleaned Data",
                output_path="outputs/cleaned_data.csv",
                format="csv"
            )
        ],
        triggers=[],
        schedule=None,
        tags=["sample", "data-cleaning", "csv"],
        created_by="system"
    )
    
    # Sample Pipeline 2: JSON Processing
    json_processing_pipeline = Pipeline(
        id="sample-json-processing",
        name="JSON Data Processing Pipeline",
        description="Processes JSON data and converts to CSV format",
        status=PipelineStatus.ACTIVE,
        steps=[
            LoadStep(
                id="load-json",
                name="Load JSON Data",
                source_path="uploads/sample_data.json",
                format="json"
            ),
            TransformStep(
                id="flatten-json",
                name="Flatten JSON Structure",
                operations=[{
                    "type": "flatten",
                    "separator": "_"
                }]
            ),
            SaveStep(
                id="save-as-csv",
                name="Save as CSV",
                output_path="outputs/json_to_csv.csv",
                format="csv"
            )
        ],
        triggers=[],
        schedule=None,
        tags=["sample", "json", "conversion"],
        created_by="system"
    )
    
    # Create the pipelines in the database
    try:
        await postgres_db.init_database()
        
        # Check if pipelines already exist
        existing_pipeline1 = await postgres_db.get_pipeline("sample-data-cleaning")
        if not existing_pipeline1:
            await postgres_db.create_pipeline(data_cleaning_pipeline)
            print("✓ Created sample data cleaning pipeline")
        
        existing_pipeline2 = await postgres_db.get_pipeline("sample-json-processing")
        if not existing_pipeline2:
            await postgres_db.create_pipeline(json_processing_pipeline)
            print("✓ Created sample JSON processing pipeline")
            
        print("Sample pipelines setup complete!")
        
    except Exception as e:
        print(f"Error creating sample pipelines: {e}")

if __name__ == "__main__":
    asyncio.run(create_sample_pipelines())