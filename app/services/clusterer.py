from collections import defaultdict

from app.models.contract import ContractChain, ContractCluster


class ContractClusterer:

    def cluster(
        self,
        chains: list[ContractChain],
    ) -> list[ContractCluster]:

        groups = defaultdict(list)

        for chain in chains:

            if chain.base_contract is None:
                continue

            contract = chain.base_contract

            contract_type = (
                contract.get("contract_type")
                or "unknown"
            )

            subject = (
                contract.get("subject")
                or "unknown"
            )

            key = (
                contract_type,
                subject,
            )

            groups[key].append(
                chain.contract_id
            )

        clusters = []

        for index, (
            key,
            contract_ids,
        ) in enumerate(
            groups.items(),
            start=1,
        ):

            contract_type, subject = key

            clusters.append(
                ContractCluster(
                    cluster_id=f"cluster_{index}",
                    contract_ids=contract_ids,
                    label=contract_type,
                    description=subject,
                )
            )

        return clusters
