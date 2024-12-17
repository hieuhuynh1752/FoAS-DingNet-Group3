from UPISAS.strategy import Strategy
from UPISAS import validate_schema

#This is a port of the ReactiveAdaptationManager originally published alongside SWIM.
class ReactiveAdaptationManager(Strategy):
    SIGNAL_THRESHOLD_LOW = -54  # Example value in dBm for lower signal threshold
    SIGNAL_THRESHOLD_HIGH = -58  # Example value in dBm for higher signal threshold
    POWER_INCREMENT = 1  # Step size for increasing power
    PACKET_LOSS_THRESHOLD = 0

    def __init__(self, exemplar):
        super().__init__(exemplar)
        # Organize knowledge access based on monitored, analysis, and plan sections
        self.monitored = self.knowledge.monitored_data
        self.monitored.setdefault("current_mote", {})  # Dictionary to hold the state of the first mote
        self.analysis = self.knowledge.analysis_data
        self.plan_data = self.knowledge.plan_data
        self.adaptation_options = self.knowledge.adaptation_options
        self.monitor_schema = self.knowledge.monitor_schema
        self.execute_schema = self.knowledge.execute_schema
        self.adaptation_options_schema = self.knowledge.adaptation_options_schema

        # Variables to store previous values for comparison
        self.previous_signal_strength = None
        self.previous_packet_loss = None

    def monitor(self, endpoint_suffix="monitor", with_validation=True, verbose=False):
        """Use the inherited monitor method to collect and store fresh data each time."""
        if verbose:
            print("[Monitor] Starting monitoring phase...")

        # Perform the GET request to fetch fresh data
        fresh_data = self._perform_get_request(endpoint_suffix)
        if verbose:
            print("[Monitor] Got fresh_data: ", fresh_data)

        if with_validation:
            if not self.knowledge.monitor_schema:
                self.get_monitor_schema()  # Fetch the monitor schema if it hasn't been fetched
            validate_schema(fresh_data, self.knowledge.monitor_schema)

        # Update the knowledge base with the fresh data
        data = self.knowledge.monitored_data
        for key in list(fresh_data.keys()):
            if key not in data:
                data[key] = []
            data[key].append(fresh_data[key])

        if verbose:
            print("[Knowledge] Data monitored so far: ", self.knowledge.monitored_data)

        # Extract the latest moteStates data
        mote_states_nested = self.knowledge.monitored_data.get("moteStates", [[]])
        if not mote_states_nested or not isinstance(mote_states_nested, list) or len(mote_states_nested) == 0:
            print("[Monitor] Warning: No valid moteStates data found.")
            return

        # Get the most recent list of motes from the nested structure
        mote_states_list = mote_states_nested[-1]  # Use the last entry in the list
        if not mote_states_list or not isinstance(mote_states_list, list) or len(mote_states_list) == 0:
            print("[Monitor] Warning: No valid list of motes found in moteStates.")
            return

        # Focus on the first mote
        first_mote = mote_states_list[0]
        if not first_mote or not isinstance(first_mote, dict):
            print("[Monitor] Warning: No valid first mote data found.")
            return

        # Update monitored data with the relevant fields of the first mote
        self.monitored["current_mote"] = {
            "highest_received_signal": first_mote.get("highestReceivedSignal", -100),
            "packet_loss": first_mote.get("packetLoss", 0),
            "power_setting": first_mote.get("transmissionPower", 0)
        }

        if verbose:
            print("[Monitor] Monitored data for the first mote: ", self.monitored["current_mote"])

    def analyze(self):
        """Analyze the monitored data for the first mote and store results."""
        print("[Analyze] Starting analysis phase...")
        mote_data = self.monitored["current_mote"]
        current_signal_strength = mote_data.get("highest_received_signal", -100)
        current_packet_loss = mote_data.get("packet_loss", 0)

        # Debug: Print current values
        print(f"[Analyze] Current Signal Strength: {current_signal_strength}, Current Packet Loss Rate: {current_packet_loss}")

        # Set initial values if None
        if self.previous_signal_strength is None:
            self.previous_signal_strength = current_signal_strength
        if self.previous_packet_loss is None:
            self.previous_packet_loss = current_packet_loss

        # Compare current values with previous values
        signal_strength_changed = current_signal_strength != self.previous_signal_strength
        packet_loss_detected = current_packet_loss > self.previous_packet_loss

        # Update the analysis results
        self.analysis.clear()
        self.analysis["increase_power"] = signal_strength_changed and current_signal_strength < self.SIGNAL_THRESHOLD_LOW
        self.analysis["decrease_power"] = signal_strength_changed and current_signal_strength > self.SIGNAL_THRESHOLD_HIGH
        self.analysis["packet_loss_issue"] = packet_loss_detected

        # Debug: Print analysis results
        print("[Analyze] Analysis results: Increase Power - {}, Decrease Power - {}, Packet Loss Issue - {}".format(
            self.analysis["increase_power"], self.analysis["decrease_power"], self.analysis["packet_loss_issue"]))

        # Store current values as previous values for the next cycle
        self.previous_signal_strength = current_signal_strength
        self.previous_packet_loss = current_packet_loss

        # Return True if any adaptation is needed
        return any(self.analysis.values())

    def plan(self):
        """Plan the adaptation actions based on the analysis."""
        print("[Plan] Starting planning phase...")
        adaptations = []

        mote_data = self.monitored["current_mote"]
        current_power_setting = mote_data.get("power_setting", 0)

        # Adjust transmission power
        if self.analysis["increase_power"]:
            adaptations.append({"name": "power", "value": current_power_setting + self.POWER_INCREMENT})
            print(f"[Plan] Planned to increase power by {self.POWER_INCREMENT}")
        elif self.analysis["decrease_power"]:
            adaptations.append({"name": "power", "value": current_power_setting - self.POWER_INCREMENT})
            print(f"[Plan] Planned to decrease power by {self.POWER_INCREMENT}")

        # If packet loss is detected, consider reducing sampling rate or taking other measures
        if self.analysis["packet_loss_issue"]:
            print(f"[Plan] Detected packet loss. Planning appropriate action.")
            # You can add additional adaptations here if necessary

        # Construct the adaptation plan
        self.plan_data = {
            "items": [
                {
                    "id": 0,  # Assuming the first mote's ID is 0; adjust as needed
                    "adaptations": adaptations
                }
            ]
        }

        print("[Plan] Adaptation Plan: ", self.plan_data)

        # Return True if there are any adaptations to execute
        return bool(adaptations)

    def execute(self, adaptation=None, endpoint_suffix="execute", with_validation=True):
        """Use the inherited execute method to apply the adaptation for the first mote."""
        print("[Execute] Starting execution phase...")
        if adaptation != None:
            super().execute(adaptation)
            print(f"[Execute] Direct adaptation applied: {adaptation}")

        if not self.plan_data or not self.plan_data.get("items"):
            print("[Execute] No adaptation plan to execute.")
            return

        print("[Execute] Executing adaptation plan: ", self.plan_data)
        success = super().execute(adaptation=self.plan_data, endpoint_suffix="execute", with_validation=True)

        if success:
            print("[Execute] Adaptation plan executed successfully.")
        else:
            print("[Execute] Adaptation plan execution failed.")