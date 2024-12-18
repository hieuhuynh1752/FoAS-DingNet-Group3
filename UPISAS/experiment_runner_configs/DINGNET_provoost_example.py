from EventManager.Models.RunnerEvents import RunnerEvents
from EventManager.EventSubscriptionController import EventSubscriptionController
from ConfigValidator.Config.Models.RunTableModel import RunTableModel
from ConfigValidator.Config.Models.FactorModel import FactorModel
from ConfigValidator.Config.Models.RunnerContext import RunnerContext
from ConfigValidator.Config.Models.OperationType import OperationType
from ExtendedTyping.Typing import SupportsStr
from ProgressManager.Output.OutputProcedure import OutputProcedure as output

from typing import Dict, List, Any, Optional
from pathlib import Path
from os.path import dirname, realpath
import time
import statistics

from UPISAS.strategies.dingnet_provoost_reactive_strategy import ReactiveAdaptationManager
from UPISAS.exemplars.dingnet import DINGNET



class RunnerConfig:
    ROOT_DIR = Path(dirname(realpath(__file__)))

    # ================================ USER SPECIFIC CONFIG ================================
    """The name of the experiment."""
    name:                       str             = "new_runner_experiment"

    """The path in which Experiment Runner will create a folder with the name `self.name`, in order to store the
    results from this experiment. (Path does not need to exist - it will be created if necessary.)
    Output path defaults to the config file's path, inside the folder 'experiments'"""
    results_output_path:        Path            = ROOT_DIR / 'experiments'

    """Experiment operation type. Unless you manually want to initiate each run, use `OperationType.AUTO`."""
    operation_type:             OperationType   = OperationType.AUTO

    """The time Experiment Runner will wait after a run completes.
    This can be essential to accommodate for cooldown periods on some systems."""
    time_between_runs_in_ms:    int             = 1000

    exemplar = None
    strategy = None
    time_between_adaptation = 5
    packetLossList = []
    powerList = []
    energyConsumptionList = []
    # Dynamic configurations can be one-time satisfied here before the program takes the config as-is
    # e.g. Setting some variable based on some criteria
    def __init__(self):
        """Executes immediately after program start, on config load"""

        EventSubscriptionController.subscribe_to_multiple_events([
            (RunnerEvents.BEFORE_EXPERIMENT, self.before_experiment),
            (RunnerEvents.BEFORE_RUN       , self.before_run       ),
            (RunnerEvents.START_RUN        , self.start_run        ),
            (RunnerEvents.START_MEASUREMENT, self.start_measurement),
            (RunnerEvents.INTERACT         , self.interact         ),
            (RunnerEvents.STOP_MEASUREMENT , self.stop_measurement ),
            (RunnerEvents.STOP_RUN         , self.stop_run         ),
            (RunnerEvents.POPULATE_RUN_DATA, self.populate_run_data),
            (RunnerEvents.AFTER_EXPERIMENT , self.after_experiment )
        ])
        self.run_table_model = None  # Initialized later

        output.console_log("Custom config loaded")

    def create_run_table_model(self) -> RunTableModel:
        """Create and return the run_table model here. A run_table is a List (rows) of tuples (columns),
        representing each run performed"""
        factor1 = FactorModel("adaptation_mode", ["provoost"])
        self.run_table_model = RunTableModel(
            factors=[factor1],
            repetitions = 10,
            data_columns=['avg_packet_loss_percentage', 'total_energy_consumption_mJ'],
        )
        return self.run_table_model

    def before_experiment(self) -> None:
        """Perform any activity required before starting the experiment here
        Invoked only once during the lifetime of the program."""

        output.console_log("Config.before_experiment() called!")

    def before_run(self) -> None:
        """Perform any activity required before starting a run.
        No context is available here as the run is not yet active (BEFORE RUN)"""
        self.exemplar = DINGNET(auto_start=True)
        self.strategy = ReactiveAdaptationManager(self.exemplar)
        output.console_log("Config.before_run() called!")

    def start_run(self, context: RunnerContext) -> None:
        """Perform any activity required for starting the run here.
        For example, starting the target system to measure.
        Activities after starting the run should also be performed here."""
        time.sleep(20)
        self.exemplar.start_run()
        time.sleep(5)
        self.strategy.execute(adaptation=
            {
                "items":
                    [
                        {
                            "id": 0,
                            "adaptations": [
                                {
                                    "name": "power",
                                    "value": 7
                                },
                                {
                                    "name": "spreading_factor",
                                    "value": 9
                                }
                            ]
                        }
                    ]
            })
        time.sleep(30)
        output.console_log("Config.start_run() called!")

    def start_measurement(self, context: RunnerContext) -> None:
        """Perform any activity required for starting measurements."""
        output.console_log("Config.start_measurement() called!")

    def interact(self, context: RunnerContext) -> None:
        """Perform any interaction with the running target system here, or block here until the target finishes."""
        for x in range(10):
            self.strategy.get_monitor_schema()
            self.strategy.get_adaptation_options_schema()
            self.strategy.get_execute_schema()

            self.strategy.monitor(verbose=True)
            if self.strategy.analyze():
                if self.strategy.plan():
                    self.strategy.execute()

            first_mote = self.strategy.monitored["current_mote"]
            self.packetLossList.append(first_mote["packet_loss"])
            self.powerList.append(first_mote["power_setting"])
            self.energyConsumptionList.append(pow(10, first_mote["power_setting"]/10)*self.time_between_adaptation)

            time.sleep(self.time_between_adaptation)

        output.console_log("Config.interact() called!")

    def stop_measurement(self, context: RunnerContext) -> None:
        """Perform any activity here required for stopping measurements."""

        output.console_log("Config.stop_measurement called!")

    def stop_run(self, context: RunnerContext) -> None:
        """Perform any activity here required for stopping the run.
        Activities after stopping the run should also be performed here."""
        self.exemplar.stop_container()
        output.console_log("Config.stop_run() called!")

    def populate_run_data(self, context: RunnerContext) -> Optional[Dict[str, SupportsStr]]:
        """Parse and process any measurement data here.
        You can also store the raw measurement data under `context.run_dir`
        Returns a dictionary with keys `self.run_table_model.data_columns` and their values populated"""

        output.console_log("Config.populate_run_data() called!")

        avg_packet_loss = sum(self.packetLossList)/len(self.packetLossList)*100
        total_energy_consumption = sum(self.energyConsumptionList)

        self.powerList = []
        self.packetLossList = []
        self.energyConsumptionList = []

        return {
            "avg_packet_loss_percentage": avg_packet_loss,
            "total_energy_consumption_mJ": total_energy_consumption
        }

    def after_experiment(self) -> None:
        """Perform any activity required after stopping the experiment here
        Invoked only once during the lifetime of the program."""
        output.console_log("Config.after_experiment() called!")

    # ================================ DO NOT ALTER BELOW THIS LINE ================================
    experiment_path:            Path             = None
