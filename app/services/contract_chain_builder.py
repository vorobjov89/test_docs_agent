from app.models.contract import ContractChain


class ContractChainBuilder:

    def build(
        self,
        documents: list[dict],
    ) -> list[ContractChain]:

        if not documents:
            return []

        chains: dict[str, ContractChain] = {}

        for document in documents:
            contract_id = self._get_contract_id(
                document
            )

            if not contract_id:
                continue

            if contract_id not in chains:
                chains[contract_id] = ContractChain(
                    contract_id=contract_id
                )

            chain = chains[contract_id]

            document_type = document.get(
                "document_type"
            )

            if document_type == "contract":
                self._add_base_contract(
                    chain,
                    document,
                )

            elif document_type in {
                "addendum",
                "termination",
            }:
                chain.addenda.append(document)

        self._finalize_chains(chains)

        return list(chains.values())

    def _get_contract_id(
        self,
        document: dict,
    ) -> str | None:

        document_type = document.get(
            "document_type"
        )

        # Для дополнительного соглашения
        # источник истины — referenced_contract_id.
        if document_type in {
            "addendum",
            "termination",
        }:
            return document.get(
                "referenced_contract_id"
            )

        # Для основного договора
        # contract_id является идентификатором цепочки.
        if document_type == "contract":
            return document.get(
                "contract_id"
            )

        # Для прочих документов используем
        # только явно распознанные идентификаторы.
        return (
            document.get("referenced_contract_id")
            or document.get("contract_id")
        )

    def _add_base_contract(
        self,
        chain: ContractChain,
        document: dict,
    ) -> None:

        if chain.base_contract is None:
            chain.base_contract = document
            return

        # Если в наборе случайно оказалось
        # несколько основных договоров одной цепочки,
        # не затираем первый, а фиксируем проблему.
        chain.warnings.append(
            "Обнаружено несколько основных договоров "
            "для одной contract chain."
        )

    def _finalize_chains(
        self,
        chains: dict[str, ContractChain],
    ) -> None:

        for chain in chains.values():

            if chain.base_contract is None:
                chain.status = "incomplete"

                chain.warnings.append(
                    "Основной договор отсутствует "
                    "в наборе документов."
                )

            else:
                chain.status = "complete"