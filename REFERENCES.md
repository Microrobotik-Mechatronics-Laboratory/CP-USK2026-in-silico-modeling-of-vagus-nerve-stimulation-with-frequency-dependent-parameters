# Academic References

This project builds on the following peer-reviewed computational neuroscience
models and theoretical frameworks. See `README.md` and the module docstrings
for how each is used within the pipeline.

## Ion channel / action potential biophysics

Hodgkin, A. L., & Huxley, A. F. (1952). A quantitative description of membrane
current and its application to conduction and excitation in nerve. *The
Journal of Physiology*, 117(4), 500-544.
— Foundational Hodgkin-Huxley (HH) ion channel model; used as the fallback
mechanism in `src/models/mrg_axon.py` and `src/models/sundt_cfiber.py` when
compiled MRG/Sundt `.mod` mechanisms are unavailable.

## Extracellular stimulation theory

McNeal, D. R. (1976). Analysis of a model for excitation of myelinated nerve.
*IEEE Transactions on Biomedical Engineering*, BME-23(4), 329-337.
— Point-source extracellular stimulation model; basis for
`src/stim/extracellular_field.py::point_source_potential`.

## Myelinated axon model (MRG)

McIntyre, C. C., Richardson, A. G., & Grill, W. M. (2002). Modeling the
excitability of mammalian nerve fibers: influence of afterpotentials on the
recovery cycle. *Journal of Neurophysiology*, 87(2), 995-1006.
— MRG double-cable myelinated axon model (ModelDB Accession: 3810).
Implemented in `src/models/mrg_axon.py` (`MRGAxon` class) using
`mechanisms/AXNODE.mod`.

## Unmyelinated C-fiber model (Sundt)

Sundt, D., Gamper, N., & Jaffe, D. B. (2015). Spike propagation through the
dorsal root ganglia in an unmyelinated sensory neuron: a modeling study.
*Journal of Neurophysiology*, 114(6), 3140-3153.
— C-fiber ion channel model (ModelDB Accession: 187473). Implemented in
`src/models/sundt_cfiber.py` (`CFiber` class) using `mechanisms/nahh.mod`
and `mechanisms/kdr.mod` (NEURON-visible mechanism name `borgkdr`, defined
via `SUFFIX borgkdr` inside `kdr.mod` — the ModelDB source file itself uses
this filename/SUFFIX naming discrepancy).

## Short-term synaptic plasticity

Tsodyks, M. V., & Markram, H. (1997). The neural code between neocortical
pyramidal neurons depends on neurotransmitter release probability.
*Proceedings of the National Academy of Sciences*, 94(2), 719-723.
— Tsodyks-Markram (TM) short-term facilitation/depression model. Implemented
in `src/network/nts_relay.py` (`TM_SYN_EQS`, `TM_ON_PRE`, `make_tm_conn`) and
used for all NTS → downstream-region pathways in
`src/pipeline/level23.py::run_full_network`.

## Interoceptive pathway architecture (NTS → Insula)

Craig, A. D. (2002). How do you feel? Interoception: the sense of the
physiological condition of the body. *Nature Reviews Neuroscience*, 3(8),
655-666.
— Anatomical basis for the NTS → thalamus → insula interoceptive pathway.
This project simplifies the pathway to a direct NTS → Insula connection
(thalamic relay omitted); see `src/network/brain_regions.py::build_insula`
docstring.

## Model repository

Hines, M. L., Morse, T., Migliore, M., Carnevale, N. T., & Shepherd, G. M.
(2004). ModelDB: A database to support computational neuroscience. *Journal
of Computational Neuroscience*, 17(1), 7-11.
— Model repository hosting the MRG (3810) and Sundt (187473) `.mod`
mechanism source files used in `mechanisms/`.
