from app.services.aggregator import ContractAggregator


class ContractService:

    def __init__(self):
        self.aggregator = ContractAggregator()

    def build_history(
        self,
        documents: list[dict],
    ):
        return self.aggregator.aggregate(
            documents
        )