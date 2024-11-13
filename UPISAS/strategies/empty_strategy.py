from UPISAS.strategy import Strategy


class EmptyStrategy(Strategy):

    def analyze(self):
        return True

    def plan(self):
        self.knowledge.plan_data = {
            "items": [
                {
                    'id': 0,
                    'adaptations': [
                        {
                            'name': 'sampling_rate',
                            'value': 2
                        }
                    ]
                }
            ]
        }
        return True
