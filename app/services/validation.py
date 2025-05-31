"""
Pipeline validation services
"""

from typing import Dict, List, Any
import re
from pathlib import Path

from app.models import StepType, DataFormat, ScheduleType
from app.utils.logger import get_logger
from config import settings

logger = get_logger(__name__)


async def validate_pipeline_config(pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a complete pipeline configuration"""
    errors = []
    warnings = []
    
    try:
        # Validate basic pipeline structure
        if not pipeline_data.get("name"):
            errors.append("Pipeline name is required")
        elif len(pipeline_data["name"]) < 3:
            errors.append("Pipeline name must be at least 3 characters long")
        
        # Validate steps
        steps = pipeline_data.get("steps", [])
        if not steps:
            errors.append("Pipeline must have at least one step")
        else:
            step_errors = await validate_pipeline_steps(steps)
            errors.extend(step_errors)
        
        # Validate schedule if present
        schedule = pipeline_data.get("schedule")
        if schedule:
            schedule_errors = await validate_schedule_config(schedule)
            errors.extend(schedule_errors)
        
        # Validate step dependencies and data flow
        flow_errors = await validate_data_flow(steps)
        errors.extend(flow_errors)
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
        
    except Exception as e:
        logger.error(f"Error validating pipeline: {e}")
        return {
            "valid": False,
            "errors": [f"Validation error: {str(e)}"],
            "warnings": warnings
        }


async def validate_pipeline_steps(steps: List[Dict[str, Any]]) -> List[str]:
    """Validate pipeline steps"""
    errors = []
    
    # Track step names for uniqueness
    step_names = set()
    
    # Track datasets for dependency validation
    available_datasets = set()
    
    for i, step in enumerate(steps):
        step_prefix = f"Step {i + 1}"
        
        # Validate basic step structure
        if not step.get("name"):
            errors.append(f"{step_prefix}: Step name is required")
        else:
            if step["name"] in step_names:
                errors.append(f"{step_prefix}: Step name '{step['name']}' must be unique")
            step_names.add(step["name"])
        
        if not step.get("type"):
            errors.append(f"{step_prefix}: Step type is required")
        elif step["type"] not in [t.value for t in StepType]:
            errors.append(f"{step_prefix}: Invalid step type '{step['type']}'")
        
        # Validate step-specific configurations
        step_type = step.get("type")
        if step_type == StepType.LOAD.value:
            load_errors = await validate_load_step(step, step_prefix)
            errors.extend(load_errors)
            if not errors:  # Only add to available datasets if valid
                available_datasets.add(step["name"])
        
        elif step_type == StepType.TRANSFORM.value:
            transform_errors = await validate_transform_step(step, step_prefix, available_datasets)
            errors.extend(transform_errors)
            if not errors:
                available_datasets.add(step["name"])
        
        elif step_type == StepType.FILTER.value:
            filter_errors = await validate_filter_step(step, step_prefix, available_datasets)
            errors.extend(filter_errors)
            if not errors:
                available_datasets.add(step["name"])
        
        elif step_type == StepType.AGGREGATE.value:
            agg_errors = await validate_aggregate_step(step, step_prefix, available_datasets)
            errors.extend(agg_errors)
            if not errors:
                available_datasets.add(step["name"])
        
        elif step_type == StepType.JOIN.value:
            join_errors = await validate_join_step(step, step_prefix, available_datasets)
            errors.extend(join_errors)
            if not errors:
                available_datasets.add(step["name"])
        
        elif step_type == StepType.SAVE.value:
            save_errors = await validate_save_step(step, step_prefix, available_datasets)
            errors.extend(save_errors)
    
    return errors


async def validate_load_step(step: Dict[str, Any], step_prefix: str) -> List[str]:
    """Validate a load step"""
    errors = []
    
    source_path = step.get("source_path")
    if not source_path:
        errors.append(f"{step_prefix}: source_path is required for load step")
    else:
        # Check if path is relative to upload directory
        if not Path(source_path).is_absolute():
            full_path = Path(settings.upload_directory) / source_path
        else:
            full_path = Path(source_path)
        
        # For validation, we won't check if file exists since it might be uploaded later
    
    data_format = step.get("format")
    if not data_format:
        errors.append(f"{step_prefix}: format is required for load step")
    elif data_format not in [f.value for f in DataFormat]:
        errors.append(f"{step_prefix}: Invalid format '{data_format}'")
    
    return errors


async def validate_transform_step(step: Dict[str, Any], step_prefix: str, available_datasets: set) -> List[str]:
    """Validate a transform step"""
    errors = []
    
    operations = step.get("operations", [])
    if not operations:
        errors.append(f"{step_prefix}: operations list is required for transform step")
    else:
        for i, operation in enumerate(operations):
            op_prefix = f"{step_prefix}, Operation {i + 1}"
            
            if not operation.get("type"):
                errors.append(f"{op_prefix}: operation type is required")
            else:
                op_errors = await validate_transform_operation(operation, op_prefix)
                errors.extend(op_errors)
    
    return errors


async def validate_transform_operation(operation: Dict[str, Any], op_prefix: str) -> List[str]:
    """Validate a single transform operation"""
    errors = []
    
    op_type = operation.get("type")
    
    if op_type == "rename_columns":
        if not operation.get("mapping"):
            errors.append(f"{op_prefix}: mapping is required for rename_columns operation")
    
    elif op_type == "add_column":
        if not operation.get("name"):
            errors.append(f"{op_prefix}: column name is required for add_column operation")
        if not operation.get("expression"):
            errors.append(f"{op_prefix}: expression is required for add_column operation")
    
    elif op_type == "drop_columns":
        if not operation.get("columns"):
            errors.append(f"{op_prefix}: columns list is required for drop_columns operation")
    
    elif op_type == "convert_types":
        if not operation.get("mapping"):
            errors.append(f"{op_prefix}: type mapping is required for convert_types operation")
    
    elif op_type == "fill_na":
        # Either method or value should be specified
        if not operation.get("method") and operation.get("value") is None:
            errors.append(f"{op_prefix}: either method or value is required for fill_na operation")
    
    elif op_type == "sort":
        if not operation.get("columns"):
            errors.append(f"{op_prefix}: columns list is required for sort operation")
    
    elif op_type not in ["reset_index"]:
        errors.append(f"{op_prefix}: unknown operation type '{op_type}'")
    
    return errors


async def validate_filter_step(step: Dict[str, Any], step_prefix: str, available_datasets: set) -> List[str]:
    """Validate a filter step"""
    errors = []
    
    conditions = step.get("conditions", [])
    if not conditions:
        errors.append(f"{step_prefix}: conditions list is required for filter step")
    else:
        for i, condition in enumerate(conditions):
            cond_prefix = f"{step_prefix}, Condition {i + 1}"
            cond_errors = await validate_filter_condition(condition, cond_prefix)
            errors.extend(cond_errors)
    
    return errors


async def validate_filter_condition(condition: Dict[str, Any], cond_prefix: str) -> List[str]:
    """Validate a single filter condition"""
    errors = []
    
    cond_type = condition.get("type")
    if not cond_type:
        errors.append(f"{cond_prefix}: condition type is required")
        return errors
    
    if cond_type not in [
        "equals", "not_equals", "greater_than", "less_than", 
        "greater_equal", "less_equal", "in", "not_in", 
        "contains", "not_null", "is_null", "expression"
    ]:
        errors.append(f"{cond_prefix}: unknown condition type '{cond_type}'")
        return errors
    
    # Most conditions require a column
    if cond_type != "expression" and not condition.get("column"):
        errors.append(f"{cond_prefix}: column is required for {cond_type} condition")
    
    # Conditions that require a value
    if cond_type in ["equals", "not_equals", "greater_than", "less_than", "greater_equal", "less_equal", "contains"]:
        if condition.get("value") is None:
            errors.append(f"{cond_prefix}: value is required for {cond_type} condition")
    
    # Conditions that require a list of values
    if cond_type in ["in", "not_in"]:
        if not condition.get("values"):
            errors.append(f"{cond_prefix}: values list is required for {cond_type} condition")
    
    # Expression condition requires expression
    if cond_type == "expression" and not condition.get("expression"):
        errors.append(f"{cond_prefix}: expression is required for expression condition")
    
    return errors


async def validate_aggregate_step(step: Dict[str, Any], step_prefix: str, available_datasets: set) -> List[str]:
    """Validate an aggregate step"""
    errors = []
    
    group_by = step.get("group_by", [])
    aggregations = step.get("aggregations", {})
    
    if not aggregations:
        errors.append(f"{step_prefix}: aggregations mapping is required for aggregate step")
    else:
        valid_agg_functions = ["count", "sum", "mean", "min", "max", "std"]
        for column, agg_func in aggregations.items():
            if agg_func not in valid_agg_functions:
                errors.append(f"{step_prefix}: invalid aggregation function '{agg_func}' for column '{column}'")
    
    return errors


async def validate_join_step(step: Dict[str, Any], step_prefix: str, available_datasets: set) -> List[str]:
    """Validate a join step"""
    errors = []
    
    right_dataset = step.get("right_dataset")
    if not right_dataset:
        errors.append(f"{step_prefix}: right_dataset is required for join step")
    elif right_dataset not in available_datasets:
        errors.append(f"{step_prefix}: right_dataset '{right_dataset}' is not available. Available datasets: {available_datasets}")
    
    if not step.get("left_on"):
        errors.append(f"{step_prefix}: left_on is required for join step")
    
    if not step.get("right_on"):
        errors.append(f"{step_prefix}: right_on is required for join step")
    
    join_type = step.get("join_type", "inner")
    if join_type not in ["inner", "left", "right", "outer"]:
        errors.append(f"{step_prefix}: invalid join_type '{join_type}'")
    
    return errors


async def validate_save_step(step: Dict[str, Any], step_prefix: str, available_datasets: set) -> List[str]:
    """Validate a save step"""
    errors = []
    
    output_path = step.get("output_path")
    if not output_path:
        errors.append(f"{step_prefix}: output_path is required for save step")
    
    data_format = step.get("format")
    if not data_format:
        errors.append(f"{step_prefix}: format is required for save step")
    elif data_format not in [f.value for f in DataFormat]:
        errors.append(f"{step_prefix}: Invalid format '{data_format}'")
    
    return errors


async def validate_schedule_config(schedule: Dict[str, Any]) -> List[str]:
    """Validate schedule configuration"""
    errors = []
    
    schedule_type = schedule.get("type")
    if not schedule_type:
        errors.append("Schedule type is required")
        return errors
    
    if schedule_type not in [t.value for t in ScheduleType]:
        errors.append(f"Invalid schedule type '{schedule_type}'")
        return errors
    
    # Validate cron expression if type is CRON
    if schedule_type == ScheduleType.CRON.value:
        cron_expr = schedule.get("cron_expression")
        if not cron_expr:
            errors.append("Cron expression is required for cron schedule type")
        else:
            cron_errors = await validate_cron_expression(cron_expr)
            errors.extend(cron_errors)
    
    # Validate interval for recurring schedules
    if schedule_type in [ScheduleType.HOURLY.value, ScheduleType.DAILY.value, ScheduleType.WEEKLY.value, ScheduleType.MONTHLY.value]:
        interval = schedule.get("interval")
        if interval is not None and (not isinstance(interval, int) or interval <= 0):
            errors.append("Interval must be a positive integer")
    
    return errors


async def validate_cron_expression(cron_expr: str) -> List[str]:
    """Validate cron expression (basic validation)"""
    errors = []
    
    try:
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            errors.append("Cron expression must have exactly 5 parts: minute hour day month weekday")
            return errors
        
        minute, hour, day, month, weekday = parts
        
        # Basic validation for each part
        if not await validate_cron_field(minute, 0, 59, "minute"):
            errors.append("Invalid minute field in cron expression")
        
        if not await validate_cron_field(hour, 0, 23, "hour"):
            errors.append("Invalid hour field in cron expression")
        
        if not await validate_cron_field(day, 1, 31, "day"):
            errors.append("Invalid day field in cron expression")
        
        if not await validate_cron_field(month, 1, 12, "month"):
            errors.append("Invalid month field in cron expression")
        
        if not await validate_cron_field(weekday, 0, 7, "weekday"):  # 0 and 7 are both Sunday
            errors.append("Invalid weekday field in cron expression")
        
    except Exception as e:
        errors.append(f"Error parsing cron expression: {str(e)}")
    
    return errors


async def validate_cron_field(field: str, min_val: int, max_val: int, field_name: str) -> bool:
    """Validate a single cron field"""
    try:
        if field == "*":
            return True
        
        # Handle ranges (e.g., "1-5")
        if "-" in field:
            start, end = field.split("-", 1)
            start_val = int(start)
            end_val = int(end)
            return min_val <= start_val <= max_val and min_val <= end_val <= max_val and start_val <= end_val
        
        # Handle lists (e.g., "1,3,5")
        if "," in field:
            values = field.split(",")
            for value in values:
                if not value.isdigit() or not (min_val <= int(value) <= max_val):
                    return False
            return True
        
        # Handle step values (e.g., "*/5")
        if "/" in field:
            base, step = field.split("/", 1)
            if base != "*" and not (base.isdigit() and min_val <= int(base) <= max_val):
                return False
            return step.isdigit() and int(step) > 0
        
        # Single numeric value
        if field.isdigit():
            value = int(field)
            return min_val <= value <= max_val
        
        return False
        
    except (ValueError, AttributeError):
        return False


async def validate_data_flow(steps: List[Dict[str, Any]]) -> List[str]:
    """Validate the data flow through pipeline steps"""
    errors = []
    
    # Check that we have at least one load step
    load_steps = [s for s in steps if s.get("type") == StepType.LOAD.value]
    if not load_steps:
        errors.append("Pipeline must have at least one load step")
    
    # Check that we have at least one save step
    save_steps = [s for s in steps if s.get("type") == StepType.SAVE.value]
    if not save_steps:
        errors.append("Pipeline should have at least one save step")
    
    # Validate step ordering - load steps should come before processing steps
    step_types = [s.get("type") for s in steps]
    
    first_non_load_index = None
    for i, step_type in enumerate(step_types):
        if step_type != StepType.LOAD.value:
            first_non_load_index = i
            break
    
    if first_non_load_index is not None:
        # Check if there are any load steps after processing steps
        for i in range(first_non_load_index, len(step_types)):
            if step_types[i] == StepType.LOAD.value:
                errors.append("Load steps should generally come before processing steps")
                break
    
    return errors
