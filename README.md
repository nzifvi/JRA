# Relevant Links
[Project Plan and Progress](https://trello.com/b/QE3CF7Dn/jra)

# Overview

# Neuron Populations
## SpatialMap Neuron Population
$$V(t+1) = \frac{-(V(t) - V_{\text{rest}}) + I_{\text{syn}} - I_{\text{inh}}}{\tau_M}\ \Delta t$$
## MemoryMap Neuron Population
$$V(t+1) \mathrel{+}= \frac{-(V(t) - V_{\text{rest}}) + I_{\text{syn}} + \text{latchGate}\cdot I_{\text{latch}}}{\tau_M}\\Delta t$$
