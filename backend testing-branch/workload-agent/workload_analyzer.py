"""
SafexpressOps Workload Analysis Module
--------------------------------------
Implements TIME AND MOTION STUDY calculations based on VFP-Productivity_TMS template
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TimeStudyObservation:
    """Single time study observation"""

    process_name: str
    observed_time_seconds: float
    num_units: int
    num_workers: int
    date: datetime
    account: str
    observer: str


@dataclass
class WorkloadParameters:
    """Operational parameters for workload analysis"""

    working_hours_per_shift: float = 8.0  # ← Renamed from hours_per_day
    days_per_month: float = 26.0
    performance_rating_factor: float = 1.0
    allowance_percentage: float = 0.15  # ← STANDARD is 15%, not 5%!
    num_shifts: int = 2  # ← Critical for multi-shift operations

    @property
    def total_hours_per_day(self) -> float:
        """Total working hours across all shifts"""
        return self.working_hours_per_shift * self.num_shifts


class WorkloadAnalyzer:
    """
    Core workload analysis engine for SafexpressOps

    Implements formulas from VFP-Productivity_TMS.xlsx:
    1. Normal Time = Observed Time × PRF
    2. Standard Time = Normal Time × (1 + Allowance)
    3. Productivity = 3600 / Standard Time
    4. Required Manpower = ROUNDUP(Volume / (Productivity × Hours), 0)
    5. Utilization = (Workload / Capacity) × 100%
    """

    def __init__(self, params: WorkloadParameters = None):
        self.params = params or WorkloadParameters()

    def calculate_average_observed_time(
        self, observations: List[TimeStudyObservation]
    ) -> float:
        """
        Calculate average observed time per unit from multiple observations

        Args:
            observations: List of time study observations

        Returns:
            Average time in seconds per unit
        """
        total_time = sum(obs.observed_time_seconds for obs in observations)
        total_units = sum(obs.num_units for obs in observations)

        if total_units == 0:
            return 0.0

        return total_time / total_units

    def calculate_normal_time(
        self, observed_time_seconds: float, prf: Optional[float] = None
    ) -> float:
        """
        Calculate normal time by applying performance rating factor

        Formula: Normal Time = Observed Time × PRF

        Args:
            observed_time_seconds: Average observed time per unit
            prf: Performance rating factor (default from params)

        Returns:
            Normal time in seconds
        """
        prf = prf or self.params.performance_rating_factor
        return observed_time_seconds * prf

    def calculate_standard_time(
        self, normal_time_seconds: float, allowance: Optional[float] = None
    ) -> float:
        """
        Calculate standard time by applying allowances

        Formula: Standard Time = Normal Time × (1 + Allowance)

        Args:
            normal_time_seconds: Normal time per unit
            allowance: Allowance percentage (default from params)

        Returns:
            Standard time in seconds
        """
        allowance = allowance or self.params.allowance_percentage
        return normal_time_seconds * (1 + allowance)

    def calculate_productivity_per_hour(self, standard_time_seconds: float) -> float:
        """
        Calculate productivity rate (units per man-hour)

        Formula: Productivity = 3600 / Standard Time

        Args:
            standard_time_seconds: Standard time per unit

        Returns:
            Units per man-hour
        """
        if standard_time_seconds <= 0:
            return 0.0

        return 3600.0 / standard_time_seconds

    def calculate_productivity_per_day(
        self, productivity_per_hour: float, hours_per_day: Optional[float] = None
    ) -> float:
        """
        Calculate daily productivity per worker across ALL shifts

        Formula: Daily Productivity = Productivity per hour × Hours per day × Number of shifts

        NOTE: In multi-shift operations, hours_per_day should reflect TOTAL working hours.
        Example: 2 shifts × 8 hours = 16 hours per day
        """
        hours = hours_per_day or self.params.working_hours_per_shift
        num_shifts = self.params.num_shifts  # ← Use this!

        # Calculate total working hours per day
        total_hours = hours * num_shifts

        return productivity_per_hour * total_hours

    def calculate_required_manpower(
        self,
        daily_volume: float,
        productivity_per_hour: float,
        hours_per_day: Optional[float] = None,
    ) -> int:
        """
        Calculate required number of workers PER SHIFT

        Formula: Required Manpower = ROUNDUP(Volume / (Productivity × Total Hours), 0)

        IMPORTANT: This returns workers needed PER SHIFT, not total workforce.
        Total headcount = Required Workers × Number of Shifts
        """
        hours = hours_per_day or self.params.working_hours_per_shift
        num_shifts = self.params.num_shifts

        # Total production hours available per day
        total_hours = hours * num_shifts

        # Capacity per worker per day (across all shifts)
        daily_capacity_per_worker = productivity_per_hour * total_hours

        if daily_capacity_per_worker <= 0:
            return 0

        required = daily_volume / daily_capacity_per_worker
        return int(np.ceil(required))

    def calculate_utilization(
        self,
        daily_volume: float,
        num_workers: int,
        productivity_per_hour: float,
        hours_per_day: Optional[float] = None,
    ) -> float:
        """
        Calculate resource utilization percentage

        Formula: Utilization = (Required Hours / Available Hours) × 100%

        Args:
            num_workers: Number of workers PER SHIFT
        """
        hours = hours_per_day or self.params.working_hours_per_shift
        num_shifts = self.params.num_shifts

        if productivity_per_hour <= 0 or num_workers <= 0:
            return 0.0

        # Total available capacity (all workers, all shifts)
        total_hours = hours * num_shifts
        available_capacity = num_workers * total_hours  # man-hours

        # Actual workload needed
        actual_workload = daily_volume / productivity_per_hour  # man-hours needed

        return (actual_workload / available_capacity) * 100.0

    def calculate_max_capacity(
        self,
        num_workers: int,
        productivity_per_hour: float,
        hours_per_day: Optional[float] = None,
    ) -> float:
        """
        Calculate maximum daily processing capacity

        Formula: Max Capacity = Workers × Total Hours × Productivity

        Args:
            num_workers: Number of workers PER SHIFT
        """
        hours = hours_per_day or self.params.working_hours_per_shift
        num_shifts = self.params.num_shifts

        total_hours = hours * num_shifts
        return num_workers * total_hours * productivity_per_hour

    def calculate_throughput_time(
        self, volume: float, num_workers: int, productivity_per_hour: float
    ) -> float:
        """
        Calculate time required to process given volume

        Formula: Throughput Time = Volume / (Workers × Productivity)

        Args:
            volume: Number of units to process
            num_workers: Number of workers
            productivity_per_hour: Units per man-hour

        Returns:
            Time in hours
        """
        if num_workers <= 0 or productivity_per_hour <= 0:
            return float("inf")

        return volume / (num_workers * productivity_per_hour)

    def full_analysis(
        self,
        observations: List[TimeStudyObservation],
        daily_volume: float,
        current_workers: int,
    ) -> Dict:
        """
        Perform complete workload analysis

        Args:
            observations: Time study observations
            daily_volume: Expected daily volume
            current_workers: Current number of workers

        Returns:
            Dictionary with all analysis results
        """
        # Step 1: Calculate average observed time
        avg_observed = self.calculate_average_observed_time(observations)

        # Step 2: Calculate normal time
        normal_time = self.calculate_normal_time(avg_observed)

        # Step 3: Calculate standard time
        standard_time = self.calculate_standard_time(normal_time)

        # Step 4: Calculate productivity
        productivity_hour = self.calculate_productivity_per_hour(standard_time)
        productivity_day = self.calculate_productivity_per_day(productivity_hour)

        # Step 5: Calculate manpower requirements
        required_workers = self.calculate_required_manpower(
            daily_volume, productivity_hour
        )

        # Step 6: Calculate utilization
        utilization = self.calculate_utilization(
            daily_volume, current_workers, productivity_hour
        )

        # Step 7: Calculate capacities
        max_capacity = self.calculate_max_capacity(current_workers, productivity_hour)

        throughput = self.calculate_throughput_time(
            daily_volume, current_workers, productivity_hour
        )

        return {
            "observed_time_seconds": avg_observed,
            "normal_time_seconds": normal_time,
            "standard_time_seconds": standard_time,
            "productivity_per_hour": productivity_hour,
            "productivity_per_day": productivity_day,
            "required_workers": required_workers,
            "current_workers": current_workers,
            "utilization_percent": utilization,
            "max_daily_capacity": max_capacity,
            "throughput_hours": throughput,
            "status": self._get_status(utilization),
            "recommendation": self._get_recommendation(
                required_workers, current_workers, utilization
            ),
        }

    def _get_status(self, utilization: float) -> str:
        """Determine operational status based on utilization"""
        if utilization < 50:
            return "UNDERUTILIZED"
        elif utilization < 80:
            return "OPTIMAL"
        elif utilization < 100:
            return "HIGH_UTILIZATION"
        else:
            return "OVERLOADED"

    def _get_recommendation(
        self, required: int, current: int, utilization: float
    ) -> str:
        """Generate recommendation based on analysis"""
        if required > current:
            return f"Add {required - current} worker(s) to meet demand"
        elif utilization < 50:
            return (
                f"Consider reducing workforce by {current - required} or adding tasks"
            )
        elif utilization > 100:
            return "URGENT: Increase manpower or reduce volume to prevent delays"
        else:
            return "Current workforce is appropriate"


class ProcessComparator:
    """Compare multiple processes to identify bottlenecks"""

    def __init__(self):
        self.analyzer = WorkloadAnalyzer()

    def identify_bottleneck(self, processes: Dict[str, Dict]) -> Tuple[str, float]:
        """
        Identify the process with longest throughput time (bottleneck)

        Args:
            processes: Dict mapping process name to analysis results

        Returns:
            Tuple of (process_name, throughput_time)
        """
        bottleneck = None
        max_throughput = 0.0

        for process_name, analysis in processes.items():
            throughput = analysis.get("throughput_hours", 0)
            if throughput > max_throughput:
                max_throughput = throughput
                bottleneck = process_name

        return bottleneck, max_throughput

    def calculate_system_capacity(self, processes: Dict[str, Dict]) -> float:
        """
        Calculate overall system capacity (limited by bottleneck)

        Args:
            processes: Dict mapping process name to analysis results

        Returns:
            System capacity in units per day
        """
        min_capacity = float("inf")

        for analysis in processes.values():
            capacity = analysis.get("max_daily_capacity", float("inf"))
            if capacity < min_capacity:
                min_capacity = capacity

        return min_capacity if min_capacity != float("inf") else 0.0


# Example usage and testing
if __name__ == "__main__":
    print("=" * 70)
    print("SafexpressOps Workload Analysis - Example Usage")
    print("=" * 70)

    # Create sample time study observations
    observations = [
        TimeStudyObservation(
            process_name="INBOUND CHECKING",
            observed_time_seconds=275.73,
            num_units=1,
            num_workers=1,
            date=datetime(2024, 1, 6),
            account="Contis",
            observer="Hans David",
        ),
        TimeStudyObservation(
            process_name="INBOUND CHECKING",
            observed_time_seconds=183.55,
            num_units=1,
            num_workers=1,
            date=datetime(2024, 1, 6),
            account="Contis",
            observer="Hans David",
        ),
        TimeStudyObservation(
            process_name="INBOUND CHECKING",
            observed_time_seconds=220.10,
            num_units=1,
            num_workers=1,
            date=datetime(2024, 1, 6),
            account="Contis",
            observer="Hans David",
        ),
    ]

    # Initialize analyzer
    analyzer = WorkloadAnalyzer()

    # Perform full analysis
    results = analyzer.full_analysis(
        observations=observations,
        daily_volume=67.0,  # pallets per day
        current_workers=2,
    )

    # Display results
    print("\nANALYSIS RESULTS:")
    print("-" * 70)
    print(
        f"Average Observed Time:     {results['observed_time_seconds']:.2f} sec/pallet"
    )
    print(f"Normal Time:               {results['normal_time_seconds']:.2f} sec/pallet")
    print(
        f"Standard Time:             {results['standard_time_seconds']:.2f} sec/pallet"
    )
    print(
        f"Productivity (per hour):   {results['productivity_per_hour']:.2f} pallets/hour"
    )
    print(
        f"Productivity (per day):    {results['productivity_per_day']:.2f} pallets/day"
    )
    print(f"Required Workers:          {results['required_workers']}")
    print(f"Current Workers:           {results['current_workers']}")
    print(f"Utilization:               {results['utilization_percent']:.1f}%")
    print(f"Max Daily Capacity:        {results['max_daily_capacity']:.2f} pallets")
    print(f"Throughput Time:           {results['throughput_hours']:.2f} hours")
    print(f"Status:                    {results['status']}")
    print(f"Recommendation:            {results['recommendation']}")
    print("=" * 70)
