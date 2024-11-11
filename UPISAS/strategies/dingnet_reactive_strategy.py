from UPISAS.strategy import Strategy

#This is a port of the ReactiveAdaptationManager originally published alongside SWIM.
class ReactiveAdaptationManager(Strategy):
    SIGNAL_THRESHOLD_LOW = -48  # Example value in dBm for lower signal threshold
    SIGNAL_THRESHOLD_HIGH = -42  # Example value in dBm for higher signal threshold
    POWER_INCREMENT = 1  # Step size for increasing power
    ENERGY_THRESHOLD_LOW = 10  # Example threshold for low energy level
    LOWER_SAMPLING_RATE = 60  # Example lower sampling rate (in seconds)
    HIGHER_SAMPLING_RATE = 10  # Example higher sampling rate (in seconds)

    def __init__(self, exemplar):
        super().__init__(exemplar)
        # Organize knowledge access based on monitored, analysis, and plan sections
        self.monitored = self.knowledge.monitored_data
        self.monitored.setdefault("mote_states", {})  # Dictionary to hold states of all motes
        self.analysis = self.knowledge.analysis_data
        self.plan = self.knowledge.plan_data
        self.adaptation_options = self.knowledge.adaptation_options
        self.monitor_schema = self.knowledge.monitor_schema
        self.execute_schema = self.knowledge.execute_schema
        self.adaptation_options_schema = self.knowledge.adaptation_options_schema

    def monitor(self, endpoint_suffix="monitor", with_validation=True, verbose=False):
        super().monitor(endpoint_suffix="monitor", with_validation=True, verbose=True)

        # Extract relevant information for analysis
        mote_states_list = self.monitored.get("moteStates", [[]])
        if isinstance(mote_states_list, list) and len(mote_states_list) > 0:
            mote_states = mote_states_list[0]  # Extract the actual list of motes
        else:
            mote_states = []
        if not mote_states:
            print("Warning: No moteStates data found. Check if the /monitor endpoint is returning data correctly.")

        all_mote_states = {}

        if mote_states and isinstance(mote_states, list):
            for mote in mote_states:
                if isinstance(mote, dict):
                    mote_id = mote.get("id", 0)
                    all_mote_states[mote_id] = {
                        "transmission_power": mote.get("transmissionPower", 0),
                        "highest_received_signal": mote.get("highestReceivedSignal", -100),
                        "shortest_distance_to_gateway": mote.get("shortestDistanceToGateway", float("inf")),
                        "energy_level": mote.get("energyLevel", 100),  # Default energy level
                        "sampling_rate": mote.get("samplingRate", self.HIGHER_SAMPLING_RATE)  # Default sampling rate
                    }

        self.monitored["mote_states"] = all_mote_states
        print("Monitored data processed for all motes: ", self.monitored["mote_states"])

    def analyze(self):
        """Analyze the monitored data for all motes and store results."""
        self.analysis.clear()  # Clear previous analysis results
        for mote_id, mote_data in self.monitored["mote_states"].items():
            signal_strength = mote_data["highest_received_signal"]
            distance_to_gateway = mote_data["shortest_distance_to_gateway"]
            energy_level = mote_data["energy_level"]

            # Perform analysis for each mote
            self.analysis[mote_id] = {
                "increase_power": signal_strength < self.SIGNAL_THRESHOLD_LOW,
                "decrease_power": signal_strength > self.SIGNAL_THRESHOLD_HIGH,
                "adjust_for_distance": distance_to_gateway is not None and (
                        distance_to_gateway > 200 or distance_to_gateway < 50),
                "reduce_sampling_rate": energy_level < self.ENERGY_THRESHOLD_LOW  # If energy is low, reduce sampling rate
            }

            print(f"Analysis for mote {mote_id}: Increase Power - {self.analysis[mote_id]['increase_power']}, "
                  f"Decrease Power - {self.analysis[mote_id]['decrease_power']}, "
                  f"Adjust for Distance - {self.analysis[mote_id]['adjust_for_distance']}, "
                  f"Reduce Sampling Rate - {self.analysis[mote_id]['reduce_sampling_rate']}")


    def plan(self):
        """Plan the adaptation actions for all motes based on the analysis."""
        self.plan.clear()  # Clear previous plan
        for mote_id, analysis in self.analysis.items():
            adaptation_plan = {}
            mote_data = self.monitored["mote_states"][mote_id]
            transmission_power = mote_data["transmission_power"]
            current_sampling_rate = mote_data["sampling_rate"]

            # Adjust transmission power
            if analysis["increase_power"]:
                new_power = min(transmission_power + self.POWER_INCREMENT, 15)  # Assuming max power is 15
                adaptation_plan["power_setting"] = new_power
                print(f"Planned to increase power for mote {mote_id} to {new_power}")

            elif analysis["decrease_power"]:
                new_power = max(transmission_power - self.POWER_INCREMENT, 0)  # Ensure power is non-negative
                adaptation_plan["power_setting"] = new_power
                print(f"Planned to decrease power for mote {mote_id} to {new_power}")

            elif analysis["adjust_for_distance"]:
                if mote_data["shortest_distance_to_gateway"] > 200:
                    new_power = min(transmission_power + self.POWER_INCREMENT, 15)
                    adaptation_plan["power_setting"] = new_power
                    print(f"Planned to increase power for distance for mote {mote_id} to {new_power}")
                else:
                    new_power = max(transmission_power - self.POWER_INCREMENT, 0)
                    adaptation_plan["power_setting"] = new_power
                    print(f"Planned to decrease power for distance for mote {mote_id} to {new_power}")

            # Adjust sampling rate if energy level is low
            if analysis["reduce_sampling_rate"]:
                adaptation_plan["sampling_rate"] = self.LOWER_SAMPLING_RATE
                print(f"Planned to reduce sampling rate for mote {mote_id} to {self.LOWER_SAMPLING_RATE}")
            else:
                adaptation_plan["sampling_rate"] = current_sampling_rate  # Keep the current rate

            # Store the plan for this mote
            self.plan[mote_id] = adaptation_plan

        # Validate the plan using adaptation_options_schema
        if not self.adaptation_options_schema.validate(self.plan):
            raise ValueError("Planned adaptation does not conform to the adaptation options schema")

