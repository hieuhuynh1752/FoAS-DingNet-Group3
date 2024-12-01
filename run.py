from UPISAS.strategies.dingnet_group3_reactive_strategy import ReactiveAdaptationManager
from UPISAS.exemplars.dingnet import DINGNET
import sys
import time

if __name__ == '__main__':

    exemplar = DINGNET(auto_start=True)
    time.sleep(30)
    exemplar.start_run()
    time.sleep(3)

    try:
        strategy = ReactiveAdaptationManager(exemplar)

        strategy.get_monitor_schema()
        strategy.get_adaptation_options_schema()
        strategy.get_execute_schema()

        while True:
            input("Try to adapt?")
            strategy.monitor(verbose=True)
            if strategy.analyze():
                if strategy.plan():
                    strategy.execute()

    except (Exception, KeyboardInterrupt) as e:
        print("Exception log:\n")
        print(e)
        input("something went wrong")
        exemplar.stop_container()
        sys.exit(0)