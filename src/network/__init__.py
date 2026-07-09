# src/network/__init__.py
# Brian2 ağ katmanı alt paketi
from .bridge import (
    neuron_spikes_to_brian_group,
    merge_fiber_populations,
    bundle_from_single_fiber,
)
from .nts_relay import (
    NTS_EQS,
    TM_SYN_EQS,
    TM_ON_PRE,
    build_nts_relay,
    make_tm_conn,
)
from .brain_regions import (
    LIF_EQS,
    build_lif_population,
    build_pop,
    build_ca3_r,
)

__all__ = [
    "neuron_spikes_to_brian_group",
    "merge_fiber_populations",
    "bundle_from_single_fiber",
    "NTS_EQS",
    "TM_SYN_EQS",
    "TM_ON_PRE",
    "build_nts_relay",
    "make_tm_conn",
    "LIF_EQS",
    "build_lif_population",
    "build_pop",
    "build_ca3_r",
]
