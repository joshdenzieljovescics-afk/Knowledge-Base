"""
ABC Analysis Agent API - Monthly Inventory Analysis Microservice
================================================================
Specialized agent for ABC analysis (Pareto analysis) of inventory/transaction data.
Works independently - reads Excel files directly, performs analysis, outputs results.

ROLE: Pure analysis - takes Excel files, performs ABC classification by MONTH, returns insights
DOES NOT: Use supervisor agent (works like mapping_agent and sheets_agent)
WORKS WITH: sheets_agent (for uploading results to Google Sheets)

Integration Pattern:
1. Frontend uploads Excel file
2. abc_agent: Reads Excel → performs ABC classification per MONTH → returns JSON results
3. abc_agent: Calls sheets_agent to upload formatted results to Google Sheets
4. Returns sheet URL to frontend
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import pandas as pd
import json
import uvicorn
from datetime import datetime
import os
import tempfile
import requests
from collections import defaultdict
import re
from datetime import datetime
import time
from functools import wraps
import asyncio

MONITORING_URL = os.getenv("MONITORING_SERVICE_URL", "http://localhost:8009")

# FastAPI app
app = FastAPI(title="ABC Analysis Agent API", version="2.0.0")


# ============================================================
# MONITORING UTILITIES
# ============================================================


def calculate_accuracy(result: Any, task_type: str) -> float:
    """Calculate task-specific accuracy score"""
    if not isinstance(result, dict):
        return 100.0

    if not result.get("success"):
        return 0.0

    # Task-specific accuracy calculation
    if task_type == "abc_analysis":
        # Based on successful classification and sheet creation
        if result.get("sheet_url"):
            months = result.get("months_analyzed", [])
            total_trans = result.get("total_transactions", 0)
            if len(months) > 0 and total_trans > 0:
                return 100.0
            return 50.0  # Partial success
        return 0.0

    elif task_type == "analyze_excel_and_upload":
        return 100.0 if result.get("sheet_url") else 0

    else:
        return 100.0


def monitor_task(agent_name: str, task_type: str):
    """
    Decorator to monitor agent tasks (supports both sync and async)
    """

    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            # Async version
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                task_id = f"{agent_name}_{int(time.time() * 1000)}"
                start_time = time.time()

                try:
                    # Execute the async function
                    result = await func(*args, **kwargs)

                    # Calculate metrics
                    latency = time.time() - start_time
                    success = (
                        result.get("success", False)
                        if isinstance(result, dict)
                        else True
                    )

                    # Calculate accuracy
                    accuracy = calculate_accuracy(result, task_type)

                    # Report to monitoring
                    try:
                        requests.post(
                            f"{MONITORING_URL}/metrics/record",
                            json={
                                "agent_name": agent_name,
                                "task_id": task_id,
                                "timestamp": datetime.now().isoformat(),
                                "accuracy_score": accuracy,
                                "latency_seconds": latency,
                                "success": success,
                                "error_message": (
                                    result.get("error")
                                    if isinstance(result, dict)
                                    else None
                                ),
                                "task_type": task_type,
                                "input_size": len(str(kwargs)) if kwargs else 0,
                                "output_size": len(str(result)) if result else 0,
                            },
                            timeout=2,
                        )
                        print(
                            f"   📊 Monitoring: {task_type} | Success: {success} | Accuracy: {accuracy:.1f}%"
                        )
                    except Exception as e:
                        print(f"   ⚠️ Monitoring report failed: {str(e)}")

                    return result

                except Exception as e:
                    latency = time.time() - start_time

                    # Report failure
                    try:
                        requests.post(
                            f"{MONITORING_URL}/metrics/record",
                            json={
                                "agent_name": agent_name,
                                "task_id": task_id,
                                "timestamp": datetime.now().isoformat(),
                                "accuracy_score": 0,
                                "latency_seconds": latency,
                                "success": False,
                                "error_message": str(e),
                                "task_type": task_type,
                            },
                            timeout=2,
                        )
                    except:
                        pass

                    raise

            return async_wrapper
        else:
            # Sync version
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                task_id = f"{agent_name}_{int(time.time() * 1000)}"
                start_time = time.time()

                try:
                    # Execute the function
                    result = func(*args, **kwargs)

                    # Calculate metrics
                    latency = time.time() - start_time
                    success = (
                        result.get("success", False)
                        if isinstance(result, dict)
                        else True
                    )

                    # Calculate accuracy
                    accuracy = calculate_accuracy(result, task_type)

                    # Report to monitoring
                    try:
                        requests.post(
                            f"{MONITORING_URL}/metrics/record",
                            json={
                                "agent_name": agent_name,
                                "task_id": task_id,
                                "timestamp": datetime.now().isoformat(),
                                "accuracy_score": accuracy,
                                "latency_seconds": latency,
                                "success": success,
                                "error_message": (
                                    result.get("error")
                                    if isinstance(result, dict)
                                    else None
                                ),
                                "task_type": task_type,
                                "input_size": len(str(kwargs)) if kwargs else 0,
                                "output_size": len(str(result)) if result else 0,
                            },
                            timeout=2,
                        )
                        print(
                            f"   📊 Monitoring: {task_type} | Success: {success} | Accuracy: {accuracy:.1f}%"
                        )
                    except Exception as e:
                        print(f"   ⚠️ Monitoring report failed: {str(e)}")

                    return result

                except Exception as e:
                    latency = time.time() - start_time

                    # Report failure
                    try:
                        requests.post(
                            f"{MONITORING_URL}/metrics/record",
                            json={
                                "agent_name": agent_name,
                                "task_id": task_id,
                                "timestamp": datetime.now().isoformat(),
                                "accuracy_score": 0,
                                "latency_seconds": latency,
                                "success": False,
                                "error_message": str(e),
                                "task_type": task_type,
                            },
                            timeout=2,
                        )
                    except:
                        pass

                    raise

            return sync_wrapper

    return decorator


# ============================================================
# PYDANTIC MODELS
# ============================================================


class CredentialsDict(BaseModel):
    """Google OAuth credentials"""

    access_token: str
    refresh_token: str
    client_id: Optional[str] = None
    client_secret: Optional[str] = None


class AnalysisRequest(BaseModel):
    """Request for ABC analysis with credentials"""

    file_path: str
    credentials_dict: CredentialsDict
    date_column: str = "Transdate"
    item_column: str = "Itemcode"
    quantity_column: str = "Qtyordered"
    description_column: Optional[str] = "Description"
    uom_column: Optional[str] = "Qtyuom"


class ToolResponse(BaseModel):
    """Generic tool execution response"""

    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ============================================================
# ABC ANALYSIS ENGINE (MONTHLY)
# ============================================================


class MonthlyABCAnalysisEngine:
    """
    Core ABC analysis logic using frequency-based scoring
    Analyzes data by MONTH instead of QUARTER
    Formula: Item Score = Total Quantity × Order Frequency
    """

    def __init__(self, a_threshold: float = 70.0, b_threshold: float = 90.0):
        """
        Args:
            a_threshold: Cumulative % threshold for Class A (default 70%)
            b_threshold: Cumulative % threshold for Class B (default 90%)
        """
        self.a_threshold = a_threshold
        self.b_threshold = b_threshold

    def detect_months(
        self, df: pd.DataFrame, date_column: str = "Transdate"
    ) -> Dict[str, pd.DataFrame]:
        """
        Auto-detect which months are present in the data

        Returns:
            Dict mapping month names (e.g., "Jan 2025") to DataFrames
        """
        print("\n" + "=" * 80)
        print("📅 AUTO-DETECTING MONTHS")
        print("=" * 80)

        if date_column not in df.columns:
            print(f"❌ Date column '{date_column}' not found!")
            return {}

        # Extract year-month combinations
        df["_year_month"] = df[date_column].dt.to_period("M")

        month_data = {}

        # Group by year-month
        for period, group_df in df.groupby("_year_month"):
            # Convert period to datetime for formatting
            month_date = period.to_timestamp()
            month_key = month_date.strftime("%b %Y")  # e.g., "Jan 2025"

            print(f"\n✓ {month_key} detected:")
            print(f"   Transactions: {len(group_df):,}")
            print(
                f"   Date range: {group_df[date_column].min().date()} to {group_df[date_column].max().date()}"
            )

            # Remove the temporary column from the group
            group_df = group_df.drop(columns=["_year_month"])
            month_data[month_key] = group_df.copy()

        # Remove temporary column from original dataframe
        df.drop(columns=["_year_month"], inplace=True)

        if not month_data:
            print("\n⚠️ No months detected (check date column)")

        return month_data

    def perform_abc_analysis(
        self,
        df: pd.DataFrame,
        item_col: str,
        quantity_col: str,
        description_col: str = None,
        uom_col: str = None,
        label: str = "Analysis",
    ) -> tuple:
        """
        Perform ABC analysis on a DataFrame

        Args:
            df: DataFrame with transaction records
            item_col: Column name for item code/ID
            quantity_col: Column name for quantity ordered
            description_col: Optional description column
            uom_col: Optional unit of measure column
            label: Label for this analysis (e.g., "Jan 2025")

        Returns:
            Tuple of (results_df, summary_dict)
        """
        print(f"\n📊 ABC Analysis: {label}")
        print("-" * 80)

        # Prepare grouping columns
        group_cols = [item_col]
        if description_col and description_col in df.columns:
            group_cols.append(description_col)
        if uom_col and uom_col in df.columns:
            group_cols.append(uom_col)

        # Aggregate: sum quantities, count orders
        aggregated = (
            df.groupby(group_cols).agg({quantity_col: ["sum", "count"]}).reset_index()
        )

        # Flatten column names
        aggregated.columns = group_cols + ["Total_Qty", "Order_Count"]

        # Calculate Item Score = Quantity × Frequency
        aggregated["Item_Score"] = aggregated["Total_Qty"] * aggregated["Order_Count"]

        # Sort by score (highest first)
        aggregated = aggregated.sort_values("Item_Score", ascending=False).reset_index(
            drop=True
        )

        # Calculate percentages
        total_score = aggregated["Item_Score"].sum()
        aggregated["Percentage"] = (
            (aggregated["Item_Score"] / total_score) * 100
        ).round(2)

        # Calculate cumulative percentage
        aggregated["Cumulative_Pct"] = aggregated["Percentage"].cumsum().round(2)

        # Assign ABC classification
        aggregated["ABC_Class"] = aggregated["Cumulative_Pct"].apply(
            lambda x: self._classify_item(x)
        )

        # Add ranking
        aggregated.insert(0, "Rank", range(1, len(aggregated) + 1))

        # Generate summary statistics
        summary = self._generate_summary(aggregated)

        print(
            f"   Class A: {summary['class_A']['item_count']} items ({summary['class_A']['pct_of_items']:.1f}%) → {summary['class_A']['contribution_pct']:.1f}%"
        )
        print(
            f"   Class B: {summary['class_B']['item_count']} items ({summary['class_B']['pct_of_items']:.1f}%) → {summary['class_B']['contribution_pct']:.1f}%"
        )
        print(
            f"   Class C: {summary['class_C']['item_count']} items ({summary['class_C']['pct_of_items']:.1f}%) → {summary['class_C']['contribution_pct']:.1f}%"
        )

        return aggregated, summary

    def _classify_item(self, cumulative_pct: float) -> str:
        """Classify item based on cumulative percentage"""
        if cumulative_pct <= self.a_threshold:
            return "A"
        elif cumulative_pct <= self.b_threshold:
            return "B"
        else:
            return "C"

    def _generate_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate summary statistics by ABC class"""
        summary = {}

        for abc_class in ["A", "B", "C"]:
            class_data = df[df["ABC_Class"] == abc_class]

            summary[f"class_{abc_class}"] = {
                "item_count": len(class_data),
                "pct_of_items": (
                    round(len(class_data) / len(df) * 100, 1) if len(df) > 0 else 0
                ),
                "total_quantity": int(class_data["Total_Qty"].sum()),
                "total_orders": int(class_data["Order_Count"].sum()),
                "avg_qty_per_item": (
                    round(class_data["Total_Qty"].mean(), 0)
                    if len(class_data) > 0
                    else 0
                ),
                "avg_orders_per_item": (
                    round(class_data["Order_Count"].mean(), 1)
                    if len(class_data) > 0
                    else 0
                ),
                "contribution_pct": round(class_data["Percentage"].sum(), 1),
            }

        return summary

    def analyze_all_months(
        self,
        month_data: Dict[str, pd.DataFrame],
        item_col: str,
        quantity_col: str,
        description_col: str = None,
        uom_col: str = None,
    ) -> Dict[str, Any]:
        """
        Analyze all detected months

        Returns:
            Dict of results by month
        """
        print("\n" + "=" * 80)
        print("📈 ANALYZING ALL MONTHS")
        print("=" * 80)

        all_results = {}

        for month_key, month_df in month_data.items():
            results, summary = self.perform_abc_analysis(
                month_df,
                item_col,
                quantity_col,
                description_col,
                uom_col,
                label=month_key,
            )

            results["Month"] = month_key

            all_results[month_key] = {
                "results": results,
                "summary": summary,
                "transactions": len(month_df),
            }

        return all_results


# ============================================================
# SHEETS FORMATTING
# ============================================================


def create_sheets_package_for_monthly_abc(
    monthly_results: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create Google Sheets package matching ABC_Analysis_Q3_2024_2.xlsx format

    Creates:
    1. Executive Summary - Overview with key insights
    2. Monthly Comparison - Month-by-month breakdown
    3. Complete ABC Analysis - All items combined
    4. Class A Items - High priority items
    5. Class B Items - Medium priority items
    6. Class C Items - Low priority items
    7. Individual month sheets (for reference)
    """
    try:
        print("\n📦 Creating Sheets Package for Monthly ABC Analysis")

        sheets_dict = {}

        # ============================================================
        # STEP 1: Combine all monthly data into one dataset
        # ============================================================
        all_items_list = []
        for month_key, data in monthly_results.items():
            df = data["results"].copy()
            df["Month"] = month_key
            all_items_list.append(df)

        # Combine all months
        all_items_df = pd.concat(all_items_list, ignore_index=True)

        # Re-calculate rankings across ALL months
        all_items_df = all_items_df.sort_values(
            "Item_Score", ascending=False
        ).reset_index(drop=True)
        all_items_df["Rank"] = range(1, len(all_items_df) + 1)

        # Recalculate cumulative percentages across all data
        total_score = all_items_df["Item_Score"].sum()
        all_items_df["Percentage"] = (
            (all_items_df["Item_Score"] / total_score) * 100
        ).round(2)
        all_items_df["Cumulative_Pct"] = all_items_df["Percentage"].cumsum().round(2)

        # Re-classify based on cumulative percentage
        def classify(cum_pct):
            if cum_pct <= 70.0:
                return "A"
            elif cum_pct <= 90.0:
                return "B"
            else:
                return "C"

        all_items_df["ABC_Class"] = all_items_df["Cumulative_Pct"].apply(classify)

        # Calculate totals
        total_transactions = sum(
            data["transactions"] for data in monthly_results.values()
        )
        total_items = len(all_items_df)
        total_class_a = len(all_items_df[all_items_df["ABC_Class"] == "A"])
        total_class_b = len(all_items_df[all_items_df["ABC_Class"] == "B"])
        total_class_c = len(all_items_df[all_items_df["ABC_Class"] == "C"])

        # ============================================================
        # SHEET 1: EXECUTIVE SUMMARY
        # ============================================================
        exec_summary = [
            ["ABC ANALYSIS - EXECUTIVE SUMMARY"],
            [""],
            ["Total Transactions:", total_transactions],
            ["Total Unique Items:", total_items],
            ["Months Analyzed:", len(monthly_results)],
            [""],
            ["ABC CLASSIFICATION SUMMARY"],
            [
                "Category",
                "Item Count",
                "% of Items",
                "Avg Qty/Item",
                "Avg Orders/Item",
                "Contribution %",
            ],
            [
                "Class A (High Priority)",
                total_class_a,
                f"{(total_class_a/total_items*100):.1f}%" if total_items > 0 else "0%",
                (
                    int(
                        all_items_df[all_items_df["ABC_Class"] == "A"][
                            "Total_Qty"
                        ].mean()
                    )
                    if total_class_a > 0
                    else 0
                ),
                (
                    round(
                        all_items_df[all_items_df["ABC_Class"] == "A"][
                            "Order_Count"
                        ].mean(),
                        1,
                    )
                    if total_class_a > 0
                    else 0
                ),
                "~70%",
            ],
            [
                "Class B (Medium Priority)",
                total_class_b,
                f"{(total_class_b/total_items*100):.1f}%" if total_items > 0 else "0%",
                (
                    int(
                        all_items_df[all_items_df["ABC_Class"] == "B"][
                            "Total_Qty"
                        ].mean()
                    )
                    if total_class_b > 0
                    else 0
                ),
                (
                    round(
                        all_items_df[all_items_df["ABC_Class"] == "B"][
                            "Order_Count"
                        ].mean(),
                        1,
                    )
                    if total_class_b > 0
                    else 0
                ),
                "~20%",
            ],
            [
                "Class C (Low Priority)",
                total_class_c,
                f"{(total_class_c/total_items*100):.1f}%" if total_items > 0 else "0%",
                (
                    int(
                        all_items_df[all_items_df["ABC_Class"] == "C"][
                            "Total_Qty"
                        ].mean()
                    )
                    if total_class_c > 0
                    else 0
                ),
                (
                    round(
                        all_items_df[all_items_df["ABC_Class"] == "C"][
                            "Order_Count"
                        ].mean(),
                        1,
                    )
                    if total_class_c > 0
                    else 0
                ),
                "~10%",
            ],
            [""],
            ["KEY INSIGHTS"],
            [f"• Focus on {total_class_a} Class A items - they drive ~70% of value"],
            [
                f"• {total_class_b} Class B items require moderate attention (~20% of value)"
            ],
            [f"• {total_class_c} Class C items are low priority (~10% of value)"],
        ]

        sheets_dict["Executive Summary"] = exec_summary

        # ============================================================
        # SHEET 2: MONTHLY COMPARISON
        # ============================================================
        comparison_data = [
            ["MONTHLY ABC ANALYSIS COMPARISON"],
            [""],
            ["Month", "Transactions", "Total Items", "Class A", "Class B", "Class C"],
        ]

        for month_key in sorted(monthly_results.keys()):
            data = monthly_results[month_key]
            comparison_data.append(
                [
                    month_key,
                    data["transactions"],
                    len(data["results"]),
                    data["summary"]["class_A"]["item_count"],
                    data["summary"]["class_B"]["item_count"],
                    data["summary"]["class_C"]["item_count"],
                ]
            )

        sheets_dict["Monthly Comparison"] = comparison_data

        # ============================================================
        # SHEET 3: COMPLETE ABC ANALYSIS
        # ============================================================
        def df_to_list(df):
            """Convert DataFrame to 2D list for Google Sheets"""
            headers = list(df.columns)
            data = [headers]

            for _, row in df.iterrows():
                row_list = []
                for val in row:
                    if pd.isna(val):
                        row_list.append("")
                    elif isinstance(val, (int, float, str, bool)):
                        row_list.append(val)
                    else:
                        try:
                            if hasattr(val, "item"):
                                row_list.append(val.item())
                            else:
                                row_list.append(str(val))
                        except:
                            row_list.append(str(val))
                data.append(row_list)

            return data

        sheets_dict["Complete ABC Analysis"] = df_to_list(all_items_df)

        # ============================================================
        # SHEET 4: CLASS A ITEMS
        # ============================================================
        class_a_df = all_items_df[all_items_df["ABC_Class"] == "A"].copy()
        class_a_data = df_to_list(class_a_df)

        # Add title row at the beginning
        headers = class_a_data[0]
        class_a_data.insert(
            0,
            ["CLASS A ITEMS - HIGH PRIORITY (Top 70% Value)"]
            + [""] * (len(headers) - 1),
        )

        sheets_dict["Class A Items"] = class_a_data

        # ============================================================
        # SHEET 5: CLASS B ITEMS
        # ============================================================
        class_b_df = all_items_df[all_items_df["ABC_Class"] == "B"].copy()
        class_b_data = df_to_list(class_b_df)

        # Add title row at the beginning
        headers = class_b_data[0]
        class_b_data.insert(
            0,
            ["CLASS B ITEMS - MEDIUM PRIORITY (Next 20% Value)"]
            + [""] * (len(headers) - 1),
        )

        sheets_dict["Class B Items"] = class_b_data

        # ============================================================
        # SHEET 6: CLASS C ITEMS
        # ============================================================
        class_c_df = all_items_df[all_items_df["ABC_Class"] == "C"].copy()
        class_c_data = df_to_list(class_c_df)

        # Add title row at the beginning
        headers = class_c_data[0]
        class_c_data.insert(
            0,
            ["CLASS C ITEMS - LOW PRIORITY (Bottom 10% Value)"]
            + [""] * (len(headers) - 1),
        )

        sheets_dict["Class C Items"] = class_c_data

        # ============================================================
        # SHEET 7+: Individual Month Sheets (for reference)
        # ============================================================
        for month_key, data in monthly_results.items():
            df = data["results"]
            safe_month_name = month_key.replace(" ", "_")[:30]

            sheets_dict[safe_month_name] = df_to_list(df)

        # Serialize to JSON
        sheets_json = json.dumps(sheets_dict)

        print(f"   ✅ Created {len(sheets_dict)} sheets")
        print(f"   📋 Sheet names: {list(sheets_dict.keys())}")
        print(f"   📏 JSON size: {len(sheets_json)} chars")

        return {
            "success": True,
            "sheets_data": sheets_json,
            "sheet_count": len(sheets_dict),
            "message": f"Created {len(sheets_dict)} sheets for monthly ABC analysis",
        }

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": f"Failed to create sheets package: {str(e)}"}


# ============================================================
# MAIN ANALYSIS FUNCTION
# ============================================================


@monitor_task("abc_agent", "analyze_excel_and_upload")
async def analyze_excel_and_upload(
    file_path: str,
    credentials_dict: CredentialsDict,
    date_column: str = "Transdate",
    item_column: str = "Itemcode",
    quantity_column: str = "Qtyordered",
    description_column: str = "Description",
    uom_column: str = "Qtyuom",
) -> Dict[str, Any]:
    """
    Main function: Load Excel, analyze by month, upload to Sheets

    Returns:
        Dict with sheet_url, analysis_results, and summary
    """
    try:
        print("\n" + "=" * 80)
        print("🎯 STARTING MONTHLY ABC ANALYSIS")
        print("=" * 80)

        # ============================================
        # 0. EXTRACT DATE INFO FROM FILENAME
        # ============================================
        filename = os.path.basename(file_path)
        filename_date_info = extract_date_range_from_filename(filename)

        # 1. Load Excel file
        print(f"\n📂 Loading Excel file: {file_path}")
        df = pd.read_excel(file_path)

        # Remove unnamed columns
        df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

        print(f"   ✓ Loaded {len(df):,} rows")
        print(f"   ✓ Columns: {list(df.columns)}")

        # 2. Convert date column
        if date_column not in df.columns:
            return {"success": False, "error": f"Date column '{date_column}' not found"}

        df[date_column] = pd.to_datetime(df[date_column])

        # 3. Initialize engine and detect months
        engine = MonthlyABCAnalysisEngine()
        month_data = engine.detect_months(df, date_column)

        if not month_data:
            return {"success": False, "error": "No months detected in data"}

        # ============================================
        # 3.5. FILTER MONTHS BASED ON FILENAME (if detected)
        # ============================================
        if filename_date_info.get("success"):
            expected_month_names = set(filename_date_info["month_names"])
            actual_month_names = set(month_data.keys())

            print(f"\n🔍 Filename Analysis:")
            print(f"   Expected from filename: {expected_month_names}")
            print(f"   Found in data: {actual_month_names}")

            # Filter to only include months mentioned in filename
            matching_months = expected_month_names.intersection(actual_month_names)

            if matching_months:
                month_data = {
                    k: v for k, v in month_data.items() if k in matching_months
                }
                print(f"   ✅ Filtered to {len(month_data)} month(s) from filename")
            else:
                print(f"   ⚠️ Filename months don't match data, analyzing all months")

        # 4. Analyze all months
        monthly_results = engine.analyze_all_months(
            month_data, item_column, quantity_column, description_column, uom_column
        )

        # 5. Create sheets package
        sheets_package = create_sheets_package_for_monthly_abc(monthly_results)

        if not sheets_package["success"]:
            return sheets_package

        # 6. Call sheets_agent to upload
        print("\n📤 Uploading to Google Sheets...")

        SHEETS_AGENT_URL = os.environ.get("SHEETS_AGENT_URL", "http://localhost:8003")

        # Generate filename with date range
        months = sorted(month_data.keys())
        first_month = months[0]
        last_month = months[-1]

        # ✅ Use filename date info if available, otherwise use detected dates
        if filename_date_info.get("success"):
            sheet_title = f"ABC Analysis - {filename_date_info['date_range']}"
        else:
            sheet_title = f"ABC Analysis - {first_month} to {last_month}"

        print(f"   📊 Sheet title: {sheet_title}")

        # Parse the sheets_data to get sheet names
        sheets_dict = json.loads(sheets_package["sheets_data"])
        sheet_names = list(sheets_dict.keys())

        print(f"   Sheet names to create: {sheet_names}")

        # STEP 1: Create the sheet with all tab names
        create_payload = {
            "tool": "create_sheet",
            "inputs": {
                "title": sheet_title,
                "sheet_names": sheet_names,
            },
            "credentials_dict": credentials_dict.dict(),
        }

        create_response = requests.post(
            f"{SHEETS_AGENT_URL}/execute_task", json=create_payload, timeout=60
        )

        if create_response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to create sheet: {create_response.text}",
            }

        create_result = create_response.json()

        if not create_result.get("success"):
            return {
                "success": False,
                "error": f"Failed to create sheet: {create_result.get('error', 'Unknown error')}",
            }

        sheet_id = create_result["result"]["sheet_id"]
        sheet_url = create_result["result"]["sheet_url"]

        print(f"   ✅ Created sheet with {len(sheet_names)} tabs: {sheet_url}")

        # STEP 2: Upload multi-sheet data
        upload_payload = {
            "tool": "upload_multi_sheet_data",
            "inputs": {
                "sheet_id": sheet_id,
                "sheets_data": sheets_package["sheets_data"],
            },
            "credentials_dict": credentials_dict.dict(),
        }

        print(f"   📤 Uploading data to {len(sheet_names)} sheets...")

        response = requests.post(
            f"{SHEETS_AGENT_URL}/execute_task",
            json=upload_payload,
            timeout=120,
        )

        if response.status_code != 200:
            return {"success": False, "error": f"Sheets agent error: {response.text}"}

        upload_result = response.json()

        if not upload_result.get("success"):
            return {
                "success": False,
                "error": f"Failed to upload: {upload_result.get('error', 'Unknown error')}",
            }

        print(f"\n✅ SUCCESS!")
        print(f"   Sheet URL: {sheet_url}")
        print(f"   Sheets uploaded: {upload_result.get('sheets_updated', [])}")

        # 7. Return results
        return {
            "success": True,
            "sheet_url": sheet_url,
            "sheet_id": sheet_id,
            "total_transactions": len(df),
            "months_analyzed": list(monthly_results.keys()),
            "monthly_summary": {
                month: {
                    "transactions": data["transactions"],
                    "total_items": len(data["results"]),
                    "class_a": data["summary"]["class_A"]["item_count"],
                    "class_b": data["summary"]["class_B"]["item_count"],
                    "class_c": data["summary"]["class_C"]["item_count"],
                }
                for month, data in monthly_results.items()
            },
        }
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": f"Analysis failed: {str(e)}"}


def extract_date_range_from_filename(filename: str) -> Dict[str, Any]:
    """
    Extract date/month information from filename

    Examples:
    - "VFP_MFI_OctoberMovement(1).xlsx" → Oct 2025
    - "ABC_Analysis_Q3_2024_2.xlsx" → Jul 2024 to Sep 2024
    - "Inventory_Jan_Feb_2025.xlsx" → Jan 2025 to Feb 2025
    - "Movement_2024_Q4.xlsx" → Oct 2024 to Dec 2024
    """
    try:
        print(f"\n📅 Extracting date from filename: {filename}")

        filename_lower = filename.lower()
        current_year = datetime.now().year

        # Pattern 1: Single month name (January, Jan, etc.)
        month_patterns = {
            r"january|jan(?!-|[a-z])": 1,
            r"february|feb(?!-|[a-z])": 2,
            r"march|mar(?!-|[a-z])": 3,
            r"april|apr(?!-|[a-z])": 4,
            r"may": 5,
            r"june|jun(?!-|[a-z])": 6,
            r"july|jul(?!-|[a-z])": 7,
            r"august|aug(?!-|[a-z])": 8,
            r"september|sept|sep(?!-|[a-z])": 9,
            r"october|oct(?!-|[a-z])": 10,
            r"november|nov(?!-|[a-z])": 11,
            r"december|dec(?!-|[a-z])": 12,
        }

        detected_months = []
        for pattern, month_num in month_patterns.items():
            if re.search(pattern, filename_lower):
                detected_months.append(month_num)

        # Pattern 2: Quarter (Q1, Q2, Q3, Q4)
        quarter_match = re.search(r"q([1-4])", filename_lower)
        if quarter_match:
            quarter = int(quarter_match.group(1))
            quarter_months = {
                1: [1, 2, 3],  # Q1: Jan, Feb, Mar
                2: [4, 5, 6],  # Q2: Apr, May, Jun
                3: [7, 8, 9],  # Q3: Jul, Aug, Sep
                4: [10, 11, 12],  # Q4: Oct, Nov, Dec
            }
            detected_months.extend(quarter_months[quarter])
            print(f"   ✓ Detected Quarter {quarter}")

        # Pattern 3: Year in filename
        year_match = re.search(r"(20\d{2})", filename)
        detected_year = int(year_match.group(1)) if year_match else current_year

        if detected_months:
            detected_months = sorted(set(detected_months))
            month_names = [
                datetime(detected_year, m, 1).strftime("%b %Y") for m in detected_months
            ]

            print(f"   ✓ Detected months: {', '.join(month_names)}")

            return {
                "success": True,
                "months": detected_months,
                "year": detected_year,
                "month_names": month_names,
                "date_range": (
                    f"{month_names[0]} to {month_names[-1]}"
                    if len(month_names) > 1
                    else month_names[0]
                ),
            }
        else:
            print(f"   ⚠️ No months detected in filename, will auto-detect from data")
            return {
                "success": False,
                "message": "No date info in filename, will use data dates",
            }

    except Exception as e:
        print(f"   ⚠️ Error parsing filename: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}


# ============================================================
# API ENDPOINTS
# ============================================================


@app.post("/analyze", response_model=ToolResponse)
async def analyze_abc(file: UploadFile = File(...), credentials: str = Form(...)):
    """
    Upload Excel file and perform monthly ABC analysis

    Returns sheet URL and analysis summary
    """
    try:
        # Parse credentials
        credentials_dict = CredentialsDict(**json.loads(credentials))

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        # Analyze and upload
        result = await analyze_excel_and_upload(tmp_path, credentials_dict)

        # Clean up
        os.unlink(tmp_path)

        return ToolResponse(
            success=result["success"],
            result=result if result["success"] else None,
            error=result.get("error"),
        )

    except Exception as e:
        return ToolResponse(success=False, error=f"Failed to process: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "abc_analysis_agent",
        "version": "2.0.0",
        "mode": "monthly_analysis",
    }


@app.get("/")
async def root():
    """Root endpoint with agent info"""
    return {
        "agent": "ABC Analysis Agent",
        "description": "Monthly inventory ABC (Pareto) analysis",
        "role": "Analyzes transaction data by MONTH to classify items by importance",
        "integration": "Direct API (like mapping_agent and sheets_agent)",
        "method": "Frequency-based scoring (Quantity × Order Count)",
        "version": "2.0.0",
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    PORT = int(os.environ.get("ABC_AGENT_PORT", 8007))
    print("\n" + "=" * 60)
    print("🎯 ABC ANALYSIS AGENT STARTING")
    print("=" * 60)
    print(f"📊 Mode: MONTHLY Analysis")
    print(f"🤝 Works With: sheets_agent")
    print(f"🌐 Running on: http://localhost:{PORT}")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=PORT)
