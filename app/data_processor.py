"""
Data processing utilities for pipeline operations
"""

import pandas as pd
import numpy as np
import json
from typing import Dict, Any, List, Union
from pathlib import Path
import io

from app.models import DataFormat
from app.utils.logger import get_logger
from app.utils.exceptions import DataProcessingError

logger = get_logger(__name__)


class DataProcessor:
    """Handles data loading, transformation, and saving operations"""
    
    async def load_data(self, file_path: str, format: DataFormat, options: Dict[str, Any] = None) -> pd.DataFrame:
        """Load data from file based on format"""
        if options is None:
            options = {}
        
        try:
            logger.info(f"Loading data from {file_path} (format: {format})")
            
            if format == DataFormat.CSV:
                df = pd.read_csv(file_path, **options)
            elif format == DataFormat.JSON:
                df = pd.read_json(file_path, **options)
            elif format == DataFormat.PARQUET:
                df = pd.read_parquet(file_path, **options)
            elif format == DataFormat.XLSX:
                df = pd.read_excel(file_path, **options)
            else:
                raise DataProcessingError(f"Unsupported format: {format}")
            
            logger.info(f"Loaded data: {len(df)} rows, {len(df.columns)} columns")
            return df
            
        except Exception as e:
            logger.error(f"Error loading data from {file_path}: {e}")
            raise DataProcessingError(f"Failed to load data: {e}")
    
    async def save_data(self, df: pd.DataFrame, file_path: str, format: DataFormat, options: Dict[str, Any] = None):
        """Save data to file based on format"""
        if options is None:
            options = {}
        
        try:
            logger.info(f"Saving data to {file_path} (format: {format})")
            
            if format == DataFormat.CSV:
                df.to_csv(file_path, index=False, **options)
            elif format == DataFormat.JSON:
                df.to_json(file_path, orient='records', **options)
            elif format == DataFormat.PARQUET:
                df.to_parquet(file_path, index=False, **options)
            elif format == DataFormat.XLSX:
                df.to_excel(file_path, index=False, **options)
            else:
                raise DataProcessingError(f"Unsupported format: {format}")
            
            logger.info(f"Saved data: {len(df)} rows to {file_path}")
            
        except Exception as e:
            logger.error(f"Error saving data to {file_path}: {e}")
            raise DataProcessingError(f"Failed to save data: {e}")
    
    async def apply_transformation(self, df: pd.DataFrame, operation: Dict[str, Any]) -> pd.DataFrame:
        """Apply a transformation operation to the dataframe"""
        try:
            operation_type = operation.get("type")
            
            if operation_type == "rename_columns":
                column_mapping = operation.get("mapping", {})
                df = df.rename(columns=column_mapping)
                
            elif operation_type == "add_column":
                column_name = operation.get("name")
                expression = operation.get("expression")
                df[column_name] = df.eval(expression)
                
            elif operation_type == "drop_columns":
                columns = operation.get("columns", [])
                df = df.drop(columns=columns, errors='ignore')
                
            elif operation_type == "convert_types":
                type_mapping = operation.get("mapping", {})
                for column, dtype in type_mapping.items():
                    if column in df.columns:
                        df[column] = df[column].astype(dtype)
                        
            elif operation_type == "fill_na":
                method = operation.get("method", "forward")
                value = operation.get("value")
                columns = operation.get("columns")
                
                if columns:
                    df[columns] = df[columns].fillna(value if value is not None else method)
                else:
                    df = df.fillna(value if value is not None else method)
                    
            elif operation_type == "sort":
                columns = operation.get("columns", [])
                ascending = operation.get("ascending", True)
                df = df.sort_values(by=columns, ascending=ascending)
                
            elif operation_type == "reset_index":
                df = df.reset_index(drop=True)
                
            else:
                raise DataProcessingError(f"Unknown transformation operation: {operation_type}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error applying transformation {operation}: {e}")
            raise DataProcessingError(f"Transformation failed: {e}")
    
    async def apply_filter(self, df: pd.DataFrame, condition: Dict[str, Any]) -> pd.DataFrame:
        """Apply a filter condition to the dataframe"""
        try:
            condition_type = condition.get("type")
            column = condition.get("column")
            
            if condition_type == "equals":
                value = condition.get("value")
                df = df[df[column] == value]
                
            elif condition_type == "not_equals":
                value = condition.get("value")
                df = df[df[column] != value]
                
            elif condition_type == "greater_than":
                value = condition.get("value")
                df = df[df[column] > value]
                
            elif condition_type == "less_than":
                value = condition.get("value")
                df = df[df[column] < value]
                
            elif condition_type == "greater_equal":
                value = condition.get("value")
                df = df[df[column] >= value]
                
            elif condition_type == "less_equal":
                value = condition.get("value")
                df = df[df[column] <= value]
                
            elif condition_type == "in":
                values = condition.get("values", [])
                df = df[df[column].isin(values)]
                
            elif condition_type == "not_in":
                values = condition.get("values", [])
                df = df[~df[column].isin(values)]
                
            elif condition_type == "contains":
                value = condition.get("value")
                df = df[df[column].str.contains(value, na=False)]
                
            elif condition_type == "not_null":
                df = df[df[column].notna()]
                
            elif condition_type == "is_null":
                df = df[df[column].isna()]
                
            elif condition_type == "expression":
                expression = condition.get("expression")
                df = df.query(expression)
                
            else:
                raise DataProcessingError(f"Unknown filter condition: {condition_type}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error applying filter {condition}: {e}")
            raise DataProcessingError(f"Filter failed: {e}")
    
    async def aggregate_data(self, df: pd.DataFrame, group_by: List[str], aggregations: Dict[str, str]) -> pd.DataFrame:
        """Aggregate data by group columns"""
        try:
            if not group_by:
                # Global aggregation
                result = {}
                for column, agg_func in aggregations.items():
                    if column in df.columns:
                        if agg_func == "count":
                            result[f"{column}_{agg_func}"] = df[column].count()
                        elif agg_func == "sum":
                            result[f"{column}_{agg_func}"] = df[column].sum()
                        elif agg_func == "mean":
                            result[f"{column}_{agg_func}"] = df[column].mean()
                        elif agg_func == "min":
                            result[f"{column}_{agg_func}"] = df[column].min()
                        elif agg_func == "max":
                            result[f"{column}_{agg_func}"] = df[column].max()
                        elif agg_func == "std":
                            result[f"{column}_{agg_func}"] = df[column].std()
                
                return pd.DataFrame([result])
            else:
                # Group by aggregation
                grouped = df.groupby(group_by)
                
                agg_dict = {}
                for column, agg_func in aggregations.items():
                    if column in df.columns:
                        agg_dict[column] = agg_func
                
                result = grouped.agg(agg_dict).reset_index()
                
                # Flatten column names if necessary
                if isinstance(result.columns, pd.MultiIndex):
                    result.columns = ['_'.join(col).strip() if col[1] else col[0] for col in result.columns.values]
                
                return result
                
        except Exception as e:
            logger.error(f"Error aggregating data: {e}")
            raise DataProcessingError(f"Aggregation failed: {e}")
    
    async def join_data(self, left_df: pd.DataFrame, right_df: pd.DataFrame, 
                       left_on: Union[str, List[str]], right_on: Union[str, List[str]], 
                       join_type: str = "inner") -> pd.DataFrame:
        """Join two dataframes"""
        try:
            if join_type == "inner":
                how = "inner"
            elif join_type == "left":
                how = "left"
            elif join_type == "right":
                how = "right"
            elif join_type == "outer":
                how = "outer"
            else:
                raise DataProcessingError(f"Unknown join type: {join_type}")
            
            result = pd.merge(left_df, right_df, left_on=left_on, right_on=right_on, how=how)
            return result
            
        except Exception as e:
            logger.error(f"Error joining data: {e}")
            raise DataProcessingError(f"Join failed: {e}")
    
    async def get_data_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get summary statistics for a dataframe"""
        try:
            summary = {
                "shape": df.shape,
                "columns": list(df.columns),
                "dtypes": df.dtypes.to_dict(),
                "null_counts": df.isnull().sum().to_dict(),
                "memory_usage": df.memory_usage(deep=True).sum(),
                "numeric_summary": {},
                "categorical_summary": {}
            }
            
            # Numeric columns summary
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            if len(numeric_columns) > 0:
                summary["numeric_summary"] = df[numeric_columns].describe().to_dict()
            
            # Categorical columns summary
            categorical_columns = df.select_dtypes(include=['object', 'category']).columns
            for col in categorical_columns:
                summary["categorical_summary"][col] = {
                    "unique_count": df[col].nunique(),
                    "top_values": df[col].value_counts().head(5).to_dict()
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating data summary: {e}")
            raise DataProcessingError(f"Summary generation failed: {e}")
    
    async def validate_data(self, df: pd.DataFrame, validation_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate data against a set of rules"""
        try:
            validation_results = {
                "passed": True,
                "total_rules": len(validation_rules),
                "passed_rules": 0,
                "failed_rules": 0,
                "rule_results": []
            }
            
            for rule in validation_rules:
                rule_type = rule.get("type")
                column = rule.get("column")
                rule_result = {
                    "rule": rule,
                    "passed": False,
                    "message": ""
                }
                
                try:
                    if rule_type == "not_null":
                        null_count = df[column].isnull().sum()
                        rule_result["passed"] = null_count == 0
                        rule_result["message"] = f"Found {null_count} null values" if null_count > 0 else "No null values"
                        
                    elif rule_type == "unique":
                        duplicate_count = df[column].duplicated().sum()
                        rule_result["passed"] = duplicate_count == 0
                        rule_result["message"] = f"Found {duplicate_count} duplicates" if duplicate_count > 0 else "All values unique"
                        
                    elif rule_type == "range":
                        min_val = rule.get("min")
                        max_val = rule.get("max")
                        out_of_range = ((df[column] < min_val) | (df[column] > max_val)).sum()
                        rule_result["passed"] = out_of_range == 0
                        rule_result["message"] = f"Found {out_of_range} values out of range [{min_val}, {max_val}]"
                        
                    elif rule_type == "data_type":
                        expected_type = rule.get("expected_type")
                        actual_type = str(df[column].dtype)
                        rule_result["passed"] = actual_type == expected_type
                        rule_result["message"] = f"Expected {expected_type}, got {actual_type}"
                        
                    if rule_result["passed"]:
                        validation_results["passed_rules"] += 1
                    else:
                        validation_results["failed_rules"] += 1
                        validation_results["passed"] = False
                        
                except Exception as e:
                    rule_result["passed"] = False
                    rule_result["message"] = f"Validation error: {e}"
                    validation_results["failed_rules"] += 1
                    validation_results["passed"] = False
                
                validation_results["rule_results"].append(rule_result)
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Error validating data: {e}")
            raise DataProcessingError(f"Validation failed: {e}")
