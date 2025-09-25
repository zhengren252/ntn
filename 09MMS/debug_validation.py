#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from src.models.simulation import SimulationTask, TaskStatus, ScenarioType

try:
    task = SimulationTask(
        task_id="sim_123",
        symbol="AAPL",
        period="1d",
        scenario=ScenarioType.NORMAL,
        strategy_params={
            "entry_threshold": 0.02,
            "exit_threshold": 0.01,
            "position_size": 0.1,
            "spread": 0.05,
            "inventory_limit": 1000,
            "risk_aversion": 0.1,
        },
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=1),
        status=TaskStatus.PENDING
    )
    print("SimulationTask created successfully!")
    print(f"Task: {task}")
except Exception as e:
    print(f"Error creating SimulationTask: {e}")
    import traceback
    traceback.print_exc()