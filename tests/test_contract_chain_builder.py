from app.services.contract_chain_builder import (
    ContractChainBuilder,
)


def test_build_contract_chains():

    documents = [
        {
            "document_type": "contract",
            "document_id": "D210262441-01",
            "contract_id": "D210262441-01",
        },
        {
            "document_type": "addendum",
            "document_id": "D250134282-01",
            "referenced_contract_id": "D210262441-01",
        },
        {
            "document_type": "addendum",
            "document_id": "D170035583-09",
            "referenced_contract_id": "D150641492-09",
        },
    ]

    builder = ContractChainBuilder()

    chains = builder.build(documents)

    assert len(chains) == 2

    complete_chain = next(
        chain
        for chain in chains
        if chain.contract_id
        == "D210262441-01"
    )

    assert (
        complete_chain.base_contract
        is not None
    )

    assert len(
        complete_chain.addenda
    ) == 1

    assert (
        complete_chain.status
        == "complete"
    )

    incomplete_chain = next(
        chain
        for chain in chains
        if chain.contract_id
        == "D150641492-09"
    )

    assert (
        incomplete_chain.base_contract
        is None
    )

    assert len(
        incomplete_chain.addenda
    ) == 1

    assert (
        incomplete_chain.status
        == "incomplete"
    )